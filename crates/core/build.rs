fn main() {
    // The `engine` cfg is now driven by the `engine` Cargo feature
    // (which enables the `stegcore-engine` dependency). No more static
    // library detection — the engine is a normal Rust crate dependency.
    println!("cargo::rustc-check-cfg=cfg(engine)");

    if std::env::var("CARGO_FEATURE_ENGINE").is_ok() {
        println!("cargo:rustc-cfg=engine");
    }

    println!("cargo:rerun-if-changed=build.rs");
}
