use std::ffi::CString;
use std::path::Path;
use crate::errors::{StegError, from_ffi_code};
use crate::ffi::engine;
use crate::keyfile::KeyFile;

// ── helpers ──────────────────────────────────────────────────────────────────

fn path_to_cstr(p: &Path) -> Result<CString, StegError> {
    CString::new(p.to_string_lossy().as_bytes())
        .map_err(|_| StegError::FileNotFound(p.display().to_string()))
}

fn bytes_to_cstr(b: &[u8]) -> Result<CString, StegError> {
    CString::new(b).map_err(|_| StegError::CorruptedFile)
}

fn str_to_cstr(s: &str) -> Result<CString, StegError> {
    CString::new(s).map_err(|_| StegError::CorruptedFile)
}

/// Parse a heap buffer returned by the engine into a `KeyFile`.
/// The buffer is freed via `lsc_free_buffer` before returning.
unsafe fn parse_keyfile(ptr: *mut u8, len: usize) -> Result<KeyFile, StegError> {
    let slice = std::slice::from_raw_parts(ptr, len);
    let result = serde_json::from_slice::<KeyFile>(slice).map_err(StegError::Json);
    engine::lsc_free_buffer(ptr);
    result
}

// ── Public API ───────────────────────────────────────────────────────────────

/// Score a cover file for embedding suitability. Returns 0.0–1.0.
pub fn assess(path: &Path) -> Result<f64, StegError> {
    let c_path = path_to_cstr(path)?;
    let score = unsafe { engine::lsc_assess(c_path.as_ptr()) };
    if score < 0.0 {
        return Err(from_ffi_code(score as i32));
    }
    Ok(score)
}

/// Embed payload into an image cover using adaptive mode.
pub fn embed_adaptive(
    cover: &Path,
    payload: &[u8],
    passphrase: &[u8],
    cipher: &str,
    out: &Path,
    export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    call_embed(cover, payload, passphrase, cipher, "adaptive", out, export_key)
}

/// Embed payload into an image cover using sequential LSB mode.
pub fn embed_sequential(
    cover: &Path,
    payload: &[u8],
    passphrase: &[u8],
    cipher: &str,
    out: &Path,
    export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    call_embed(cover, payload, passphrase, cipher, "sequential", out, export_key)
}

/// Embed payload into a WAV audio file (always sequential).
pub fn embed_wav(
    cover: &Path,
    payload: &[u8],
    passphrase: &[u8],
    cipher: &str,
    out: &Path,
    export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    call_embed(cover, payload, passphrase, cipher, "sequential", out, export_key)
}

/// Embed two independent payloads (deniable mode). Always exports both key files.
pub fn embed_deniable(
    cover: &Path,
    real_payload: &[u8],
    decoy_payload: &[u8],
    real_pass: &[u8],
    decoy_pass: &[u8],
    cipher: &str,
    out: &Path,
) -> Result<(KeyFile, KeyFile), StegError> {
    let c_cover   = path_to_cstr(cover)?;
    let c_pass    = bytes_to_cstr(real_pass)?;
    let c_cipher  = str_to_cstr(cipher)?;
    let c_mode    = str_to_cstr("sequential")?;
    let c_dpass   = bytes_to_cstr(decoy_pass)?;
    let c_out     = path_to_cstr(out)?;

    let mut out_ptr: *mut u8 = std::ptr::null_mut();
    let mut out_len: usize = 0;

    let rc = unsafe {
        engine::lsc_embed(
            c_cover.as_ptr(),
            real_payload.as_ptr(),
            real_payload.len(),
            c_pass.as_ptr(),
            c_cipher.as_ptr(),
            c_mode.as_ptr(),
            1, // deniable
            decoy_payload.as_ptr(),
            decoy_payload.len(),
            c_dpass.as_ptr(),
            1, // export key
            c_out.as_ptr(),
            &mut out_ptr,
            &mut out_len,
        )
    };

    if rc != 0 {
        return Err(from_ffi_code(rc));
    }

    // out buffer contains JSON array [real_kf, decoy_kf]
    let pair: (KeyFile, KeyFile) = unsafe {
        let slice = std::slice::from_raw_parts(out_ptr, out_len);
        let mut arr: Vec<KeyFile> = serde_json::from_slice(slice).map_err(|e| {
            engine::lsc_free_buffer(out_ptr);
            StegError::Json(e)
        })?;
        engine::lsc_free_buffer(out_ptr);
        if arr.len() < 2 {
            return Err(StegError::CorruptedFile);
        }
        let decoy = arr.remove(1);
        let real  = arr.remove(0);
        (real, decoy)
    };

    Ok(pair)
}

/// Extract hidden payload using only passphrase (metadata embedded in file).
pub fn extract(stego: &Path, passphrase: &[u8]) -> Result<Vec<u8>, StegError> {
    let c_stego = path_to_cstr(stego)?;
    let c_pass  = bytes_to_cstr(passphrase)?;

    let mut out_ptr: *mut u8 = std::ptr::null_mut();
    let mut out_len: usize = 0;

    let rc = unsafe {
        engine::lsc_extract(
            c_stego.as_ptr(),
            c_pass.as_ptr(),
            std::ptr::null(), // no key file
            &mut out_ptr,
            &mut out_len,
        )
    };

    if rc != 0 {
        return Err(from_ffi_code(rc));
    }

    let data = unsafe {
        let slice = std::slice::from_raw_parts(out_ptr, out_len);
        let v = slice.to_vec();
        engine::lsc_free_buffer(out_ptr);
        v
    };

    Ok(data)
}

/// Extract hidden payload using an external key file.
pub fn extract_with_keyfile(
    stego: &Path,
    keyfile: &KeyFile,
    passphrase: &[u8],
) -> Result<Vec<u8>, StegError> {
    // Write key file to a temp path so the engine can read it.
    let tmp = tempfile::NamedTempFile::new().map_err(StegError::Io)?;
    crate::keyfile::write_key_file(tmp.path(), keyfile)?;

    let c_stego = path_to_cstr(stego)?;
    let c_pass  = bytes_to_cstr(passphrase)?;
    let c_kf    = path_to_cstr(tmp.path())?;

    let mut out_ptr: *mut u8 = std::ptr::null_mut();
    let mut out_len: usize = 0;

    let rc = unsafe {
        engine::lsc_extract(
            c_stego.as_ptr(),
            c_pass.as_ptr(),
            c_kf.as_ptr(),
            &mut out_ptr,
            &mut out_len,
        )
    };

    if rc != 0 {
        return Err(from_ffi_code(rc));
    }

    let data = unsafe {
        let slice = std::slice::from_raw_parts(out_ptr, out_len);
        let v = slice.to_vec();
        engine::lsc_free_buffer(out_ptr);
        v
    };

    Ok(data)
}

/// Read the embedded metadata header from a stego file without decrypting the payload.
/// Requires the passphrase. Returns the metadata as a parsed JSON value.
pub fn read_meta(path: &Path, passphrase: &[u8]) -> Result<serde_json::Value, StegError> {
    let c_path = path_to_cstr(path)?;
    let c_pass = bytes_to_cstr(passphrase)?;

    let mut json_ptr: *mut std::os::raw::c_char = std::ptr::null_mut();
    let mut json_len: usize = 0;

    let rc = unsafe {
        engine::lsc_read_meta(c_path.as_ptr(), c_pass.as_ptr(), &mut json_ptr, &mut json_len)
    };

    if rc != 0 {
        return Err(from_ffi_code(rc));
    }

    let value = unsafe {
        let slice = std::slice::from_raw_parts(json_ptr as *const u8, json_len);
        let result = serde_json::from_slice::<serde_json::Value>(slice).map_err(StegError::Json);
        engine::lsc_free_buffer(json_ptr as *mut u8);
        result?
    };

    Ok(value)
}

// ── Private helper ────────────────────────────────────────────────────────────

fn call_embed(
    cover: &Path,
    payload: &[u8],
    passphrase: &[u8],
    cipher: &str,
    mode: &str,
    out: &Path,
    export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    let c_cover  = path_to_cstr(cover)?;
    let c_pass   = bytes_to_cstr(passphrase)?;
    let c_cipher = str_to_cstr(cipher)?;
    let c_mode   = str_to_cstr(mode)?;
    let c_out    = path_to_cstr(out)?;

    let mut out_ptr: *mut u8 = std::ptr::null_mut();
    let mut out_len: usize = 0;

    let rc = unsafe {
        engine::lsc_embed(
            c_cover.as_ptr(),
            payload.as_ptr(),
            payload.len(),
            c_pass.as_ptr(),
            c_cipher.as_ptr(),
            c_mode.as_ptr(),
            0, // not deniable
            std::ptr::null(),
            0,
            std::ptr::null(),
            export_key as i32,
            c_out.as_ptr(),
            &mut out_ptr,
            &mut out_len,
        )
    };

    if rc != 0 {
        return Err(from_ffi_code(rc));
    }

    if out_ptr.is_null() {
        return Ok(None);
    }

    let kf = unsafe { parse_keyfile(out_ptr, out_len)? };
    Ok(Some(kf))
}
