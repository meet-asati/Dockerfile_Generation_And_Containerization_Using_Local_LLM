# Sample Rust project

This small HTTP service is intentionally structured for a multi-stage Dockerfile:

- The build stage can compile `src/main.rs` with `cargo build --release`.
- The runtime stage only needs the resulting `target/release/sample-rust-multistage` binary.
- The service binds to `0.0.0.0`, reads its port from `PORT`, and provides a `/health` endpoint.

## Run locally

```powershell
cargo run
```

Then open `http://localhost:8080/health`.

To create the production artifact used by a runtime image:

```powershell
cargo build --release
```