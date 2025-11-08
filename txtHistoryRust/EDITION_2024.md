# Rust Edition 2024 Configuration

This project uses Rust Edition 2024, which is required by the `imessage-database` v2.4.0 dependency.

## Toolchain Setup

The project uses the nightly Rust toolchain to support Edition 2024. This is configured via `rust-toolchain.toml`:

```toml
[toolchain]
channel = "nightly"
components = ["rustfmt", "clippy"]
```

## Usage

When you run `cargo` commands in this directory, Rust will automatically use the nightly toolchain specified in `rust-toolchain.toml`.

## Note

Edition 2024 is still in development and requires nightly Rust. When Edition 2024 becomes stable, you can switch to the stable toolchain.
