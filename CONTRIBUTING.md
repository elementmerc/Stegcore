# Contributing to Stegcore

## Dev environment

**Prerequisites:** Rust 1.70+, Node.js 20+ (24 recommended), npm.

```bash
git clone https://github.com/elementmerc/Stegcore.git
cd Stegcore

# Install frontend dependencies
cd frontend && npm install && cd ..

# Run in development mode (GUI + hot reload)
cargo tauri dev

# Or build release binaries
cargo build --release
```

**Linux dependencies:**
```bash
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev \
  libayatana-appindicator3-dev librsvg2-dev libglib2.0-dev
```

**Node.js version (this machine):**
```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 24
```

---

## Project structure

```
Cargo.toml              — workspace root
crates/core/            — public library (errors, wrappers, keyfile, utils)
crates/cli/             — CLI binary (clap v4)
src-tauri/              — Tauri v2 app shell + IPC commands
frontend/               — React + TypeScript + Vite + Tailwind
libstegcore/            — private engine (not in this repo)
```

---

## Code style

**Rust:**
- `cargo fmt --all` before every commit
- `cargo clippy --workspace -- -D warnings` must pass

**TypeScript:**
- `npx tsc --noEmit` from `frontend/` must pass
- Inline styles using `--ui-*` / `--sc-*` CSS variables
- CSS hover classes (not inline JS style mutations)
- `React.memo()` for heavy sub-components

---

## Architecture rules

- **No modals.** Toasts only for notifications.
- **Two repos:** `stegcore` (public, AGPL) + `libstegcore` (private).
  Do not suggest merging them.
- **All Tauri commands** must be `async` with `spawn_blocking` for
  CPU-heavy work to prevent UI freezes.

---

## Testing

```bash
# Run all tests
cargo test --workspace

# With engine (if libstegcore is available)
cargo test --workspace --features engine

# TypeScript type check
cd frontend && npx tsc --noEmit

# Format check
cargo fmt --all --check
```

---

## Pull requests

- One logical change per PR
- Include a description of what changed and why
- Ensure all checks pass (`clippy`, `fmt`, `tsc`)
