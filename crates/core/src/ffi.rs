/// C FFI declarations for the libstegcore engine.
///
/// When the engine is present (`cfg(engine)`), these extern "C" declarations
/// resolve to the prebuilt static library. When absent, the stub module
/// below is compiled instead — every function returns -99 (EngineAbsent).

#[cfg(engine)]
pub mod engine {
    use std::os::raw::{c_char, c_int};

    extern "C" {
        /// Embed a payload into a cover file.
        /// Returns 0 on success; negative error code on failure.
        pub fn lsc_embed(
            cover: *const c_char,
            payload: *const u8,
            payload_len: usize,
            passphrase: *const c_char,
            cipher: *const c_char,
            mode: *const c_char,
            deniable: c_int,
            decoy_payload: *const u8,
            decoy_len: usize,
            decoy_pass: *const c_char,
            export_key: c_int,
            out_path: *const c_char,
            out: *mut *mut u8,
            out_len: *mut usize,
        ) -> c_int;

        /// Extract a payload from a stego file.
        /// Returns 0 on success; negative error code on failure.
        pub fn lsc_extract(
            stego: *const c_char,
            passphrase: *const c_char,
            key_file: *const c_char, // may be NULL
            out: *mut *mut u8,
            out_len: *mut usize,
        ) -> c_int;

        /// Analyze a file for steganographic content.
        /// Returns 0 on success; fills json_out with a library-allocated JSON string.
        pub fn lsc_analyze(
            path: *const c_char,
            json_out: *mut *mut c_char,
            json_len: *mut usize,
        ) -> c_int;

        /// Score a cover file for embedding suitability. Returns 0.0–1.0 on success,
        /// or a negative value cast to f64 on error.
        pub fn lsc_assess(path: *const c_char) -> f64;

        /// Free a buffer previously allocated by the engine.
        pub fn lsc_free_buffer(ptr: *mut u8);
    }
}

#[cfg(not(engine))]
pub mod engine {
    use std::os::raw::{c_char, c_int};

    pub unsafe fn lsc_embed(
        _cover: *const c_char,
        _payload: *const u8,
        _payload_len: usize,
        _passphrase: *const c_char,
        _cipher: *const c_char,
        _mode: *const c_char,
        _deniable: c_int,
        _decoy_payload: *const u8,
        _decoy_len: usize,
        _decoy_pass: *const c_char,
        _export_key: c_int,
        _out_path: *const c_char,
        _out: *mut *mut u8,
        _out_len: *mut usize,
    ) -> c_int {
        -99
    }

    pub unsafe fn lsc_extract(
        _stego: *const c_char,
        _passphrase: *const c_char,
        _key_file: *const c_char,
        _out: *mut *mut u8,
        _out_len: *mut usize,
    ) -> c_int {
        -99
    }

    pub unsafe fn lsc_analyze(
        _path: *const c_char,
        _json_out: *mut *mut c_char,
        _json_len: *mut usize,
    ) -> c_int {
        -99
    }

    pub unsafe fn lsc_assess(_path: *const c_char) -> f64 {
        -99.0
    }

    pub unsafe fn lsc_free_buffer(_ptr: *mut u8) {}
}
