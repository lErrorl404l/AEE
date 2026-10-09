//! A minimal HTTP/1.1 loopback listener for the dev console.
//!
//! The listener binds `127.0.0.1` only. A bind to any other address is refused
//! before a socket exists, so the console can never listen on a public
//! interface. The server uses only `std`: one `TcpListener` on a `std::thread`
//! and one short-lived thread per connection. There is no async runtime.
//!
//! Routes:
//!
//! - `GET /health` returns `pong` (an unauthenticated liveness probe).
//! - `POST /command` takes a `{op, id, args, token}` JSON body and requires the
//!   token. A wrong or missing token is `401`.

use std::io::{BufRead, BufReader, Read, Write};
use std::net::{IpAddr, Ipv4Addr, SocketAddr, TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use serde::Deserialize;

/// The default loopback port for the dev console.
pub const DEFAULT_PORT: u16 = 7788;

/// How often the accept loop checks the shutdown flag.
const POLL_INTERVAL: Duration = Duration::from_millis(30);

/// The largest request body the listener reads.
const MAX_BODY_BYTES: usize = 1024 * 1024;

/// Errors raised while starting or serving the listener.
#[derive(Debug)]
pub enum HttpError {
    /// The requested bind address is not a loopback address.
    NonLoopback(SocketAddr),
    /// The socket could not be created.
    Io(std::io::Error),
}

impl std::fmt::Display for HttpError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NonLoopback(addr) => write!(f, "refusing a non-loopback bind: {addr}"),
            Self::Io(error) => write!(f, "listener io error: {error}"),
        }
    }
}

impl std::error::Error for HttpError {}

impl From<std::io::Error> for HttpError {
    fn from(error: std::io::Error) -> Self {
        Self::Io(error)
    }
}

/// The dev console configuration, read from the environment.
#[derive(Debug, Clone)]
pub struct DevConfig {
    /// The loopback port (`AEE_DEV_PORT`, default [`DEFAULT_PORT`]).
    pub port: u16,
    /// The shared token (`AEE_DEV_TOKEN`). An empty token refuses every call.
    pub token: String,
}

impl DevConfig {
    /// Reads `AEE_DEV_PORT` and `AEE_DEV_TOKEN` from the environment.
    #[must_use]
    pub fn from_env() -> Self {
        let port = std::env::var("AEE_DEV_PORT")
            .ok()
            .and_then(|value| value.parse().ok())
            .unwrap_or(DEFAULT_PORT);
        let token = std::env::var("AEE_DEV_TOKEN").unwrap_or_default();
        Self { port, token }
    }

    /// The loopback bind address. The IP is fixed to `127.0.0.1`, never
    /// `0.0.0.0`.
    #[must_use]
    pub const fn bind_addr(&self) -> SocketAddr {
        SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), self.port)
    }
}

/// Refuses a bind address that is not a loopback address.
///
/// # Errors
/// Returns [`HttpError::NonLoopback`] when `addr` is not loopback.
pub fn ensure_loopback(addr: SocketAddr) -> Result<SocketAddr, HttpError> {
    if addr.ip().is_loopback() {
        Ok(addr)
    } else {
        Err(HttpError::NonLoopback(addr))
    }
}

/// A parsed `POST /command` body.
#[derive(Debug, Default, Deserialize)]
pub struct CommandRequest {
    /// The verb to run.
    #[serde(default)]
    pub op: String,
    /// The client's correlation id, echoed back by the caller.
    #[serde(default)]
    pub id: serde_json::Value,
    /// The verb arguments.
    #[serde(default)]
    pub args: Vec<serde_json::Value>,
    /// The shared token.
    #[serde(default)]
    pub token: String,
}

/// A response the handler returns to the caller.
#[derive(Debug, Clone)]
pub struct HttpResponse {
    /// The HTTP status code.
    pub status: u16,
    /// The response body.
    pub body: String,
}

impl HttpResponse {
    /// A `200` response.
    #[must_use]
    pub fn ok(body: impl Into<String>) -> Self {
        Self {
            status: 200,
            body: body.into(),
        }
    }

    /// A response with a chosen status.
    #[must_use]
    pub fn text(status: u16, body: impl Into<String>) -> Self {
        Self {
            status,
            body: body.into(),
        }
    }
}

/// A handler for `POST /command`.
pub trait CommandHandler: Send + Sync {
    /// Runs `request` and produces a response.
    fn handle(&self, request: CommandRequest) -> HttpResponse;
}

struct ServerState {
    token: String,
    handler: Arc<dyn CommandHandler>,
    shutdown: Arc<AtomicBool>,
}

/// A running loopback listener. Dropping it stops the accept loop.
#[derive(Debug)]
pub struct Server {
    addr: SocketAddr,
    shutdown: Arc<AtomicBool>,
}

impl Server {
    /// Starts the listener on the loopback address from `config`.
    ///
    /// # Errors
    /// Returns [`HttpError`] when the bind is refused or fails.
    pub fn start(config: &DevConfig, handler: Arc<dyn CommandHandler>) -> Result<Self, HttpError> {
        Self::start_on(config.bind_addr(), config.token.clone(), handler)
    }

    /// Starts the listener on an explicit address, refusing any non-loopback
    /// address.
    ///
    /// # Errors
    /// Returns [`HttpError::NonLoopback`] for a non-loopback address and
    /// [`HttpError::Io`] when the socket cannot be created.
    pub fn start_on(
        bind: SocketAddr,
        token: String,
        handler: Arc<dyn CommandHandler>,
    ) -> Result<Self, HttpError> {
        let bind = ensure_loopback(bind)?;
        let listener = TcpListener::bind(bind)?;
        let addr = listener.local_addr()?;
        listener.set_nonblocking(true)?;
        let shutdown = Arc::new(AtomicBool::new(false));
        let state = Arc::new(ServerState {
            token,
            handler,
            shutdown: Arc::clone(&shutdown),
        });
        thread::spawn(move || accept_loop(&listener, &state));
        Ok(Self { addr, shutdown })
    }

    /// The bound address, including the OS-assigned port when the requested
    /// port was `0`.
    #[must_use]
    pub const fn addr(&self) -> SocketAddr {
        self.addr
    }
}

impl Drop for Server {
    fn drop(&mut self) {
        self.shutdown.store(true, Ordering::SeqCst);
    }
}

/// Whether this build may open the loopback dev listener.
///
/// The listener is a dev-server surface. A client build must not open a dev
/// port, so it compiles the listener out under the `client` feature.
#[must_use]
pub const fn listener_supported() -> bool {
    !cfg!(feature = "client")
}

/// The outcome of a start attempt.
#[derive(Debug, Clone, Copy)]
pub enum StartOutcome {
    /// The listener started on this address.
    Started(SocketAddr),
    /// The listener was already running; nothing changed.
    AlreadyRunning,
    /// The listener is disabled in this build (a client build).
    DisabledInClientBuild,
}

/// Owns the single persistent listener. The command that starts it builds the
/// callback-bearing handler once through `make_handler`; this server calls
/// that factory exactly once, at start, never per request.
#[derive(Debug, Default)]
pub struct DevServer {
    inner: Mutex<Option<Server>>,
}

impl DevServer {
    /// Creates a stopped server.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Starts the listener unless one already runs.
    ///
    /// `make_handler` runs once, on the first successful start, and captures
    /// the callback. A later start leaves the running listener untouched.
    ///
    /// # Errors
    /// Returns [`HttpError`] when the bind is refused or fails.
    pub fn start<F>(&self, config: &DevConfig, make_handler: F) -> Result<StartOutcome, HttpError>
    where
        F: FnOnce() -> Arc<dyn CommandHandler>,
    {
        if !listener_supported() {
            return Ok(StartOutcome::DisabledInClientBuild);
        }
        let mut guard = self.lock();
        if guard.is_some() {
            return Ok(StartOutcome::AlreadyRunning);
        }
        let server = Server::start(config, make_handler())?;
        let addr = server.addr();
        *guard = Some(server);
        Ok(StartOutcome::Started(addr))
    }

    /// Stops the listener. Returns true when one was running.
    pub fn stop(&self) -> bool {
        self.lock().take().is_some()
    }

    /// The bound address, when running.
    #[must_use]
    pub fn addr(&self) -> Option<SocketAddr> {
        self.lock().as_ref().map(Server::addr)
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, Option<Server>> {
        self.inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
}

fn accept_loop(listener: &TcpListener, state: &Arc<ServerState>) {
    loop {
        if state.shutdown.load(Ordering::SeqCst) {
            return;
        }
        match listener.accept() {
            Ok((stream, _peer)) => {
                let state = Arc::clone(state);
                thread::spawn(move || {
                    let _ = handle_conn(&stream, &state);
                });
            }
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                thread::sleep(POLL_INTERVAL);
            }
            Err(_) => return,
        }
    }
}

fn handle_conn(stream: &TcpStream, state: &ServerState) -> std::io::Result<()> {
    stream.set_read_timeout(Some(Duration::from_secs(5)))?;
    let mut writer = stream.try_clone()?;
    let mut reader = BufReader::new(stream);
    let mut request_line = String::new();
    if reader.read_line(&mut request_line)? == 0 {
        return Ok(());
    }

    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or_default();
    let path = parts.next().unwrap_or_default();

    let mut content_length = 0usize;
    loop {
        let mut line = String::new();
        if reader.read_line(&mut line)? == 0 {
            break;
        }
        let trimmed = line.trim_end();
        if trimmed.is_empty() {
            break;
        }
        if let Some((name, value)) = trimmed.split_once(':') {
            if name.eq_ignore_ascii_case("content-length") {
                content_length = value.trim().parse().unwrap_or(0);
            }
        }
    }

    let mut body = vec![0u8; content_length.min(MAX_BODY_BYTES)];
    if !body.is_empty() {
        reader.read_exact(&mut body)?;
    }

    let response = route(state, method, path, &body);
    write_response(&mut writer, &response)
}

fn route(state: &ServerState, method: &str, path: &str, body: &[u8]) -> HttpResponse {
    match (method, path) {
        ("GET", "/health") => HttpResponse::ok("pong"),
        ("POST", "/command") => command(state, body),
        _ => HttpResponse::text(404, "not found"),
    }
}

fn command(state: &ServerState, body: &[u8]) -> HttpResponse {
    let request: CommandRequest = match serde_json::from_slice(body) {
        Ok(request) => request,
        Err(_) => return HttpResponse::text(400, "bad request"),
    };
    if !token_ok(&state.token, &request.token) {
        return HttpResponse::text(401, "unauthorized");
    }
    state.handler.handle(request)
}

/// A length-checked, branch-free comparison that never matches an empty
/// expected token.
fn token_ok(expected: &str, provided: &str) -> bool {
    if expected.is_empty() || expected.len() != provided.len() {
        return false;
    }
    let diff = expected
        .bytes()
        .zip(provided.bytes())
        .fold(0u8, |acc, (a, b)| acc | (a ^ b));
    diff == 0
}

fn write_response(stream: &mut TcpStream, response: &HttpResponse) -> std::io::Result<()> {
    let reason = match response.status {
        200 => "OK",
        400 => "Bad Request",
        401 => "Unauthorized",
        404 => "Not Found",
        504 => "Gateway Timeout",
        _ => "OK",
    };
    let head = format!(
        "HTTP/1.1 {} {}\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        response.status, reason, response.body.len()
    );
    stream.write_all(head.as_bytes())?;
    stream.write_all(response.body.as_bytes())?;
    stream.flush()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;

    struct Echo;

    impl CommandHandler for Echo {
        fn handle(&self, request: CommandRequest) -> HttpResponse {
            HttpResponse::ok(format!("op={}", request.op))
        }
    }

    fn config(token: &str) -> DevConfig {
        DevConfig {
            port: 0,
            token: token.to_string(),
        }
    }

    fn raw_request(addr: SocketAddr, request: &str) -> String {
        let mut stream = TcpStream::connect(addr).expect("connect");
        stream.write_all(request.as_bytes()).expect("write");
        stream
            .shutdown(std::net::Shutdown::Write)
            .expect("shutdown");
        let mut out = String::new();
        stream.read_to_string(&mut out).expect("read");
        out
    }

    fn post(addr: SocketAddr, body: &str) -> String {
        let request = format!(
            "POST /command HTTP/1.1\r\nHost: localhost\r\nContent-Length: {}\r\n\r\n{}",
            body.len(),
            body
        );
        raw_request(addr, &request)
    }

    #[test]
    fn handler_is_captured_once_at_start_not_per_request() {
        let factory_calls = Arc::new(AtomicUsize::new(0));
        let calls = Arc::clone(&factory_calls);
        let dev = DevServer::new();
        let addr = match dev
            .start(&config("s3cret"), move || {
                calls.fetch_add(1, Ordering::SeqCst);
                Arc::new(Echo)
            })
            .expect("start")
        {
            StartOutcome::Started(addr) => addr,
            StartOutcome::AlreadyRunning => panic!("expected a start"),
            StartOutcome::DisabledInClientBuild => {
                panic!("the default test build must enable the listener")
            }
        };
        post(addr, r#"{"op":"ping","token":"s3cret"}"#);
        post(addr, r#"{"op":"ping","token":"s3cret"}"#);
        assert_eq!(factory_calls.load(Ordering::SeqCst), 1);
        let again = dev.start(&config("s3cret"), || -> Arc<dyn CommandHandler> {
            panic!("the handler factory must not run again")
        });
        assert!(matches!(again, Ok(StartOutcome::AlreadyRunning)));
        assert_eq!(factory_calls.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn health_returns_pong() {
        let server = Server::start(&config("s3cret"), Arc::new(Echo)).expect("start");
        let response = raw_request(
            server.addr(),
            "GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n",
        );
        assert!(response.starts_with("HTTP/1.1 200"), "{response}");
        assert!(response.ends_with("pong"), "{response}");
    }

    #[test]
    fn valid_token_is_accepted() {
        let server = Server::start(&config("s3cret"), Arc::new(Echo)).expect("start");
        let response = post(
            server.addr(),
            r#"{"op":"ping","id":1,"args":[],"token":"s3cret"}"#,
        );
        assert!(response.starts_with("HTTP/1.1 200"), "{response}");
        assert!(response.ends_with("op=ping"), "{response}");
    }

    #[test]
    fn wrong_token_is_unauthorized() {
        let server = Server::start(&config("s3cret"), Arc::new(Echo)).expect("start");
        let response = post(
            server.addr(),
            r#"{"op":"ping","id":1,"args":[],"token":"wrong"}"#,
        );
        assert!(response.starts_with("HTTP/1.1 401"), "{response}");
    }

    #[test]
    fn missing_token_is_unauthorized() {
        let server = Server::start(&config("s3cret"), Arc::new(Echo)).expect("start");
        let response = post(server.addr(), r#"{"op":"ping","args":[]}"#);
        assert!(response.starts_with("HTTP/1.1 401"), "{response}");
    }

    #[test]
    fn empty_configured_token_refuses_every_call() {
        let server = Server::start(&config(""), Arc::new(Echo)).expect("start");
        let response = post(server.addr(), r#"{"op":"ping","token":""}"#);
        assert!(response.starts_with("HTTP/1.1 401"), "{response}");
    }

    #[test]
    fn non_loopback_bind_is_refused() {
        let addr = SocketAddr::new(IpAddr::V4(Ipv4Addr::UNSPECIFIED), 0);
        let error = Server::start_on(addr, "token".into(), Arc::new(Echo)).err();
        assert!(
            matches!(error, Some(HttpError::NonLoopback(_))),
            "expected NonLoopback, got {error:?}"
        );
    }

    #[test]
    fn unknown_route_is_not_found() {
        let server = Server::start(&config("s3cret"), Arc::new(Echo)).expect("start");
        let response = raw_request(
            server.addr(),
            "GET /nope HTTP/1.1\r\nHost: localhost\r\n\r\n",
        );
        assert!(response.starts_with("HTTP/1.1 404"), "{response}");
    }
}
