# aee_dev - the AEE development extension

A dev-only Arma 3 native extension, loaded from the standalone dev harness under
`tools/dev-harness/`. It hosts the loopback dev console (tasks 11 and 12 of the
development-experience plan). It is not part of any release artefact.

## What it exposes

The crate is a `cdylib` built on [`arma-rs`](https://docs.rs/arma-rs) 1.13.0.
The Arma 3 extension ABI is the C interface the engine calls:

- `RVExtension` - a single string argument.
- `RVExtensionArgs` - a function name plus a string array.
- `RVExtensionRegisterCallback` - the engine hands the extension a function
  pointer; the extension calls it to raise the SQF `ExtensionCallback` mission
  event handler.
- `RVExtensionVersion` - the version string.

`arma-rs` generates all four from the `#[arma]` entry point in `src/lib.rs` and
runs the callback dispatch loop on a worker thread, so a callback never blocks
the engine thread.

SQF addresses the extension by name through `callExtension`:

```sqf
"aee_dev" callExtension ["ping", []]
```

The return value of `callExtension` is capped at 10240 bytes by the engine.
The asynchronous bridge ignores that cap: the reply travels as the
`callExtension` *input* (the `["reply", ...]` call), and a reply larger than
4096 bytes is chunked. See `src/bridge.rs`.

## Build

Linux (the Docker harness):

```sh
./build.sh linux
# -> dist/aee_dev_x64.so
```

Windows 64-bit, cross-compiled with `cargo-xwin`:

```sh
./build.sh windows
# -> dist/aee_dev_x64.dll
```

`cargo-xwin` needs the Microsoft CRT/SDK. It downloads them on first use; on a
host without network access the Windows build is a manual step and the exact
toolchain is recorded in the evidence log. A 32-bit Windows build additionally
needs the `Win32.def` workaround for the 32-bit link; this crate targets 64-bit
only.

## Server build and client build

The default build is the server build: it binds the loopback listener on
`127.0.0.1:7788` and needs no BattlEye whitelist. A dedicated server runs it
directly.

A client build must not open a dev port. Enable the `client` feature and the
listener refuses to bind:

```sh
cargo build --release --features client
```

`cargo test` proves the observable outcome in `tests/test_client_no_listener.rs`:
the server build binds, the client build does not.

A client extension is optional and needs BattlEye off. `hasInterface` is false
on a headless client, so the client-local helpers are skipped there. The
BattlEye-on server path is a manual ceiling: it is not exercised by any gate.

## Linux compatibility

The Linux `.so` links the glibc of the machine that builds it. The dedicated
server image is Debian 12 (glibc 2.36); a `libaee_dev.so` built on a host with a
newer glibc fails to load with `Call extension 'aee_dev' could not be loaded`.
Build the extension inside a glibc-compatible environment (or with a matching
sysroot) before the Docker harness can load it.

## Tests

```sh
cargo test
```

Unit tests cover the command surface, the HTTP listener and the bridge. The
integration test builds the listener probe with and without the `client`
feature and asserts whether the listener binds. They run on the host and do not
need Arma.

## Licence

GPL-2.0-or-later. See `LICENSE` and the repository root `LICENSE`.

The `arma-rs` dependency declares MIT in its crate `Cargo.toml` but carries the
GNU General Public License v2 as its repository `LICENSE`. No `arma-rs` source
is vendored here; the discrepancy is recorded in `LICENSE` and the evidence
log.
