//! The asynchronous callback request-response bridge.
//!
//! The HTTP handler allocates an id, stores a oneshot reply channel, calls
//! `ctx.callback_data("aee_dev", "exec", ...)` with an SQF-literal request and
//! waits with a timeout. The
//! SQF side replies with `"aee_dev" callExtension ["reply", [id, payload]]`;
//! the extension stores the reply and unblocks the HTTP thread. The engine
//! thread is never blocked: `arma-rs` raises the callback on its own worker
//! thread and `Context::callback_data` only enqueues.
//!
//! Size: the engine caps the `callExtension` RETURN value at 10240 bytes. The
//! reply here ignores that cap because it travels as the `callExtension`
//! INPUT (the `["reply", ...]` call), whose limit the study does not document.
//! A reply larger than [`CHUNK_BOUND`] is therefore chunked by the caller and
//! reassembled on the final chunk, not claimed as unlimited flow.

use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::mpsc::{self, Receiver, RecvTimeoutError, Sender};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use crate::http::{CommandHandler, CommandRequest, HttpResponse};

/// The reply size above which the caller chunks (`4 KiB`).
pub const CHUNK_BOUND: usize = 4096;

/// The default wait for a reply (`2 s`).
pub const DEFAULT_TIMEOUT: Duration = Duration::from_millis(2000);

/// A bridge failure.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BridgeError {
    /// No pending request carries this id, or it already resolved.
    UnknownId(u64),
    /// No reply arrived before the timeout.
    Timeout,
    /// The waiting request went away before a reply arrived.
    Abandoned,
    /// The extension callback channel is closed.
    CallbackClosed,
}

impl std::fmt::Display for BridgeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnknownId(id) => write!(f, "no pending request with id {id}"),
            Self::Timeout => write!(f, "no reply before the timeout"),
            Self::Abandoned => write!(f, "the waiter was abandoned"),
            Self::CallbackClosed => write!(f, "the extension callback channel is closed"),
        }
    }
}

impl std::error::Error for BridgeError {}

/// A channel that raises the SQF `ExtensionCallback` event. The listener
/// captures one implementation once, at start, and reuses it for every
/// request; it is never rebuilt per request.
pub trait CallbackChannel: Send + Sync {
    /// Sends an `exec` callback carrying `request` as the callback data.
    ///
    /// # Errors
    /// Returns [`BridgeError::CallbackClosed`] when the engine callback
    /// channel is closed.
    fn exec(&self, request: &str) -> Result<(), BridgeError>;
}

#[derive(Debug)]
struct Pending {
    tx: Sender<String>,
    chunks: Vec<(u32, String)>,
}
/// A pending request/reply registry keyed by an extension-allocated id.
#[derive(Debug, Default)]
pub struct Bridge {
    next_id: AtomicU64,
    pending: Mutex<HashMap<u64, Pending>>,
}

impl Bridge {
    /// Creates an empty bridge.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Allocates an id and registers a oneshot reply channel.
    #[must_use]
    pub fn open(&self) -> (u64, Receiver<String>) {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed) + 1;
        let (tx, rx) = mpsc::channel();
        self.lock().insert(
            id,
            Pending {
                tx,
                chunks: Vec::new(),
            },
        );
        (id, rx)
    }

    /// Stores a complete reply and unblocks the waiter.
    ///
    /// # Errors
    /// Returns [`BridgeError::UnknownId`] when no pending request matches.
    pub fn reply(&self, id: u64, payload: String) -> Result<(), BridgeError> {
        let pending = self.lock().remove(&id).ok_or(BridgeError::UnknownId(id))?;
        let _ = pending.tx.send(payload);
        Ok(())
    }

    /// Stores one chunk of a chunked reply. The chunk marked `last` joins all
    /// chunks in index order and unblocks the waiter.
    ///
    /// # Errors
    /// Returns [`BridgeError::UnknownId`] when no pending request matches.
    pub fn reply_chunk(
        &self,
        id: u64,
        index: u32,
        chunk: String,
        last: bool,
    ) -> Result<(), BridgeError> {
        let mut guard = self.lock();
        match guard.get_mut(&id) {
            Some(pending) => pending.chunks.push((index, chunk)),
            None => return Err(BridgeError::UnknownId(id)),
        }
        if !last {
            return Ok(());
        }
        let pending = guard.remove(&id).ok_or(BridgeError::UnknownId(id))?;
        let mut chunks = pending.chunks;
        chunks.sort_by_key(|(index, _)| *index);
        let joined: String = chunks.into_iter().map(|(_, chunk)| chunk).collect();
        let _ = pending.tx.send(joined);
        Ok(())
    }

    /// Drops a pending id so a late reply finds nothing.
    pub fn abandon(&self, id: u64) {
        self.lock().remove(&id);
    }

    /// The number of pending requests.
    #[must_use]
    pub fn pending_len(&self) -> usize {
        self.lock().len()
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, HashMap<u64, Pending>> {
        self.pending
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
}

/// Waits for a reply with a timeout.
///
/// # Errors
/// Returns [`BridgeError::Timeout`] when no reply arrives in time and
/// [`BridgeError::Abandoned`] when the sender is dropped.
pub fn wait(rx: &Receiver<String>, timeout: Duration) -> Result<String, BridgeError> {
    match rx.recv_timeout(timeout) {
        Ok(payload) => Ok(payload),
        Err(RecvTimeoutError::Timeout) => Err(BridgeError::Timeout),
        Err(RecvTimeoutError::Disconnected) => Err(BridgeError::Abandoned),
    }
}

/// Splits `payload` into chunks of at most `bound` bytes, never splitting a
/// UTF-8 character. Returns an empty vector for an empty payload or a zero
/// bound.
#[must_use]
pub fn chunk_payload(payload: &str, bound: usize) -> Vec<String> {
    if bound == 0 || payload.is_empty() {
        return Vec::new();
    }
    let mut chunks = Vec::new();
    let mut start = 0;
    let mut len = 0;
    for (index, character) in payload.char_indices() {
        let size = character.len_utf8();
        if len + size > bound {
            chunks.push(payload[start..index].to_string());
            start = index;
            len = 0;
        }
        len += size;
    }
    chunks.push(payload[start..].to_string());
    chunks
}

/// Builds the SQF-literal request the SQF dispatcher reads with
/// `parseSimpleArray`: `[id, "op", [args...]]`. JSON would not parse, so the
/// request never uses it.
fn exec_request(id: u64, op: &str, args: &[serde_json::Value]) -> String {
    let args = serde_json::Value::Array(args.to_vec());
    format!(
        "[{id},\"{}\",{}]",
        op.replace('"', "\"\""),
        to_sqf_literal(&args)
    )
}

/// Renders a JSON value as an SQF literal. A JSON object has no SQF literal, so
/// it renders as `nil`.
fn to_sqf_literal(value: &serde_json::Value) -> String {
    match value {
        serde_json::Value::Null => "nil".to_string(),
        serde_json::Value::Bool(flag) => flag.to_string(),
        serde_json::Value::Number(number) => number.to_string(),
        serde_json::Value::String(text) => format!("\"{}\"", text.replace('"', "\"\"")),
        serde_json::Value::Array(items) => {
            let inner: Vec<String> = items.iter().map(to_sqf_literal).collect();
            format!("[{}]", inner.join(","))
        }
        serde_json::Value::Object(_) => "nil".to_string(),
    }
}

/// Extracts the id from an SQF-literal exec request `[id, ...]`.
#[cfg(test)]
fn leading_id(request: &str) -> Option<u64> {
    let rest = request.strip_prefix('[')?;
    let end = rest.find(',')?;
    rest[..end].trim().parse().ok()
}

/// The `POST /command` handler: open a bridge id, raise the `exec` callback,
/// and wait for the reply. A timeout is a `504`.
pub struct BridgeHandler {
    bridge: Arc<Bridge>,
    callback: Arc<dyn CallbackChannel>,
    timeout: Duration,
}

impl BridgeHandler {
    /// Wires a bridge and a captured callback into a handler.
    #[must_use]
    pub fn new(bridge: Arc<Bridge>, callback: Arc<dyn CallbackChannel>, timeout: Duration) -> Self {
        Self {
            bridge,
            callback,
            timeout,
        }
    }
}

impl CommandHandler for BridgeHandler {
    fn handle(&self, request: CommandRequest) -> HttpResponse {
        let (id, rx) = self.bridge.open();
        let exec = exec_request(id, &request.op, &request.args);
        if self.callback.exec(&exec).is_err() {
            self.bridge.abandon(id);
            return HttpResponse::text(502, "the extension callback channel is closed");
        }
        match wait(&rx, self.timeout) {
            Ok(payload) => HttpResponse::ok(payload),
            Err(_) => {
                self.bridge.abandon(id);
                HttpResponse::text(504, "timeout")
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::http::CommandRequest;

    /// A callback that immediately resolves the id with a fixed payload.
    struct Immediate {
        bridge: Arc<Bridge>,
        payload: String,
    }

    impl CallbackChannel for Immediate {
        fn exec(&self, request: &str) -> Result<(), BridgeError> {
            let id = leading_id(request).ok_or(BridgeError::CallbackClosed)?;
            self.bridge.reply(id, self.payload.clone())
        }
    }

    /// A callback that never replies.
    struct Silent;

    impl CallbackChannel for Silent {
        fn exec(&self, _request: &str) -> Result<(), BridgeError> {
            Ok(())
        }
    }

    /// A callback that replies with a payload larger than the chunk bound.
    struct Chunked {
        bridge: Arc<Bridge>,
    }

    impl CallbackChannel for Chunked {
        fn exec(&self, request: &str) -> Result<(), BridgeError> {
            let id = leading_id(request).ok_or(BridgeError::CallbackClosed)?;
            let payload = "y".repeat(CHUNK_BOUND + 10);
            let chunks = chunk_payload(&payload, CHUNK_BOUND);
            let count = chunks.len();
            for (index, chunk) in chunks.into_iter().enumerate() {
                let last = index + 1 == count;
                self.bridge.reply_chunk(id, index as u32, chunk, last)?;
            }
            Ok(())
        }
    }

    #[test]
    fn exec_request_is_an_sqf_literal_array() {
        let request = exec_request(7, "get", &[serde_json::json!("aee_x")]);
        assert_eq!(request, "[7,\"get\",[\"aee_x\"]]");
        assert_eq!(leading_id(&request), Some(7));
    }

    #[test]
    fn reply_resolves_a_stored_id() {
        let bridge = Bridge::new();
        let (id, rx) = bridge.open();
        bridge.reply(id, "hello".to_string()).expect("reply");
        assert_eq!(wait(&rx, DEFAULT_TIMEOUT).expect("wait"), "hello");
        assert_eq!(bridge.pending_len(), 0);
    }

    #[test]
    fn reply_to_an_unknown_id_is_rejected() {
        let bridge = Bridge::new();
        assert_eq!(
            bridge.reply(7, "x".to_string()),
            Err(BridgeError::UnknownId(7))
        );
    }

    #[test]
    fn timeout_drops_the_id_and_a_late_reply_is_unknown() {
        let bridge = Bridge::new();
        let (id, rx) = bridge.open();
        assert_eq!(
            wait(&rx, Duration::from_millis(10)),
            Err(BridgeError::Timeout)
        );
        bridge.abandon(id);
        assert_eq!(bridge.pending_len(), 0);
        assert_eq!(
            bridge.reply(id, "late".to_string()),
            Err(BridgeError::UnknownId(id))
        );
    }

    #[test]
    fn chunked_reply_reassembles_in_index_order() {
        let bridge = Bridge::new();
        let (id, rx) = bridge.open();
        bridge
            .reply_chunk(id, 1, "world".to_string(), false)
            .expect("chunk 1");
        bridge
            .reply_chunk(id, 0, "hello ".to_string(), false)
            .expect("chunk 0");
        bridge
            .reply_chunk(id, 2, "!".to_string(), true)
            .expect("last");
        assert_eq!(wait(&rx, DEFAULT_TIMEOUT).expect("wait"), "hello world!");
    }

    #[test]
    fn chunk_payload_splits_a_reply_larger_than_the_bound() {
        let payload = "x".repeat(CHUNK_BOUND * 2 + 5);
        let chunks = chunk_payload(&payload, CHUNK_BOUND);
        assert_eq!(chunks.len(), 3);
        assert!(chunks.iter().all(|chunk| chunk.len() <= CHUNK_BOUND));
        assert_eq!(chunks.concat(), payload);
    }

    #[test]
    fn chunk_payload_respects_utf8_boundaries() {
        let payload = "é".repeat(10); // two bytes per char
        let chunks = chunk_payload(&payload, 3);
        assert!(chunks.iter().all(|chunk| chunk.len() <= 3));
        assert_eq!(chunks.concat(), payload);
    }

    #[test]
    fn handler_resolves_a_reply() {
        let bridge = Arc::new(Bridge::new());
        let handler = BridgeHandler::new(
            Arc::clone(&bridge),
            Arc::new(Immediate {
                bridge: Arc::clone(&bridge),
                payload: "engine-answer".to_string(),
            }),
            Duration::from_millis(500),
        );
        let response = handler.handle(CommandRequest::default());
        assert_eq!(response.status, 200);
        assert_eq!(response.body, "engine-answer");
    }

    #[test]
    fn handler_times_out_with_504_and_drops_the_id() {
        let bridge = Arc::new(Bridge::new());
        let handler = BridgeHandler::new(
            Arc::clone(&bridge),
            Arc::new(Silent),
            Duration::from_millis(20),
        );
        let response = handler.handle(CommandRequest::default());
        assert_eq!(response.status, 504);
        assert_eq!(bridge.pending_len(), 0);
    }

    #[test]
    fn handler_reassembles_a_chunked_reply() {
        let bridge = Arc::new(Bridge::new());
        let handler = BridgeHandler::new(
            Arc::clone(&bridge),
            Arc::new(Chunked {
                bridge: Arc::clone(&bridge),
            }),
            Duration::from_millis(500),
        );
        let response = handler.handle(CommandRequest::default());
        assert_eq!(response.status, 200);
        assert_eq!(response.body.len(), CHUNK_BOUND + 10);
    }
}
