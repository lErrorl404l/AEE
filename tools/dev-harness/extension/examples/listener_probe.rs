//! Reports whether the dev listener binds in this build.
//!
//! `test_client_no_listener` runs this twice: once for the default (server)
//! build and once with `--features client`. The printed line is the observable
//! outcome the test asserts on.

use std::sync::Arc;

use aee_dev::http::{
    CommandHandler, CommandRequest, DevConfig, DevServer, HttpResponse, StartOutcome,
};

struct Noop;

impl CommandHandler for Noop {
    fn handle(&self, _request: CommandRequest) -> HttpResponse {
        HttpResponse::ok("")
    }
}

fn main() {
    let config = DevConfig {
        port: 0,
        token: "probe".to_string(),
    };
    match DevServer::new().start(&config, || Arc::new(Noop)) {
        Ok(StartOutcome::Started(addr)) => println!("bound {addr}"),
        Ok(StartOutcome::AlreadyRunning) => println!("already-running"),
        Ok(StartOutcome::DisabledInClientBuild) => println!("disabled"),
        Err(error) => println!("error {error}"),
    }
}
