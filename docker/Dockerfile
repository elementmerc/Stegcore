# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM rust:1.82-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache dependencies separately from source
COPY Cargo.toml Cargo.lock ./
COPY crates/core/Cargo.toml crates/core/Cargo.toml
COPY crates/cli/Cargo.toml  crates/cli/Cargo.toml

# Engine stub (libstegcore is private — public builds use stub)
RUN mkdir -p libstegcore/src \
    && printf '[package]\nname = "stegcore-engine"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\nname = "stegcore_engine"\n' > libstegcore/Cargo.toml \
    && touch libstegcore/src/lib.rs

# Stub source files so cargo can fetch deps without full source
RUN mkdir -p crates/core/src crates/cli/src \
    && echo 'pub fn placeholder() {}' > crates/core/src/lib.rs \
    && echo 'fn main() {}' > crates/cli/src/main.rs

# Fetch and cache all dependencies
RUN cargo fetch

# Copy real source
COPY crates/ crates/

# Build CLI binary only (no Tauri, no frontend)
RUN cargo build --release -p stegcore-cli --no-default-features

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1000 stegcore
USER stegcore
WORKDIR /home/stegcore

COPY --from=builder /app/target/release/stegcore /usr/local/bin/stegcore

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=1 \
    CMD stegcore --version || exit 1

ENTRYPOINT ["stegcore"]
