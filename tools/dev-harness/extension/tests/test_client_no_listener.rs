//! The client build must not open the loopback dev listener.
//!
//! The test runs the `listener_probe` example twice: once for the default
//! (server) build and once with the `client` feature. It asserts the observable
//! outcome, whether the listener binds, not a grep for a feature flag.
//!
//! The nested builds use their own target directory, so they never contend for
//! the lock the outer `cargo test` holds on the default target directory.

use std::path::{Path, PathBuf};
use std::process::Command;

fn run_probe(features: Option<&str>, target_dir: &Path) -> String {
    let cargo = std::env::var("CARGO").unwrap_or_else(|_| "cargo".to_string());
    let mut command = Command::new(cargo);
    command
        .args([
            "run",
            "--quiet",
            "--example",
            "listener_probe",
            "--target-dir",
        ])
        .arg(target_dir);
    if let Some(features) = features {
        command.args(["--features", features]);
    }
    command.current_dir(env!("CARGO_MANIFEST_DIR"));
    let output = command.output().expect("run the listener probe");
    assert!(
        output.status.success(),
        "the probe build failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8_lossy(&output.stdout).trim().to_string()
}

fn probe_dir(root: &Path, name: &str) -> PathBuf {
    root.join("target").join("probe").join(name)
}

#[test]
fn server_build_binds_the_listener_and_client_build_does_not() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));

    let server = run_probe(None, &probe_dir(&root, "server"));
    assert!(
        server.starts_with("bound "),
        "the server build must bind the listener, got: {server}"
    );

    let client = run_probe(Some("client"), &probe_dir(&root, "client"));
    assert_eq!(
        client, "disabled",
        "the client build must not bind the listener, got: {client}"
    );
}
