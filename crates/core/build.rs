fn main() {
    // Declare `cfg(engine)` as a known cfg key so rustc doesn't warn about it.
    println!("cargo::rustc-check-cfg=cfg(engine)");

    // Engine detection: look for prebuilt static lib in lib/<target>/
    // If found, link it and set cfg(engine) so ffi.rs uses real bindings.
    // If absent, a stub returning StegError::EngineAbsent is compiled instead.
    let target = std::env::var("TARGET").unwrap_or_default();
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_default();
    let lib_dir = std::path::PathBuf::from(&manifest_dir)
        .join("lib")
        .join(&target);

    let lib_name = if target.contains("windows") {
        "stegcore_engine.lib"
    } else {
        "libstegcore_engine.a"
    };

    if lib_dir.join(lib_name).exists() {
        println!("cargo:rustc-link-search=native={}", lib_dir.display());
        println!("cargo:rustc-link-lib=static=stegcore_engine");
        println!("cargo:rustc-cfg=engine");
        println!("cargo:warning=stegcore-core: using prebuilt engine from {}", lib_dir.display());
    } else {
        println!(
            "cargo:warning=stegcore-core: engine library not found at {}. \
             Compiling stub — all embed/extract/analyze calls will return EngineAbsent. \
             Download a prebuilt release or build libstegcore to enable full functionality.",
            lib_dir.join(lib_name).display()
        );
    }

    println!("cargo:rerun-if-changed=lib/{}/", target);
    println!("cargo:rerun-if-changed=build.rs");
}
