// Copyright (C) 2026 Daniel Iwugo — elementmerc
// SPDX-License-Identifier: AGPL-3.0-or-later OR LicenseRef-Stegcore-Commercial
//
// This file is part of Stegcore. Stegcore is free software: you can
// redistribute it and/or modify it under the terms of the GNU Affero
// General Public License as published by the Free Software Foundation,
// either version 3 of the License, or (at your option) any later version.
//
// Commercial licensing: daniel@themalwarefiles.com

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
