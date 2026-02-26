#!/usr/bin/env python3
# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: cli.py
# Description: Stegcore command-line interface.
#
#   Two usage modes:
#     Power users  — single-line commands with flags
#     Basic users  — `stegcore wizard` for guided step-by-step flow
#
#   Commands: embed, extract, score, info, ciphers, wizard
#   Requires: typer, rich  (pip install typer rich)

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from typing import Optional

# Windows cmd/PowerShell defaults to cp1252. Force UTF-8 before Rich initialises.
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    for _stream in (sys.stdout, sys.stderr):
        if _stream and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

import typer
from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Bootstrap — make sure core/ is importable when running cli.py directly
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from core import crypto, steg, utils  # noqa: E402

# ---------------------------------------------------------------------------
# App + console
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="stegcore",
    help=(
        "Crypto-steganography toolkit.\n\n"
        "[dim]New to the terminal?  Run:[/dim]  [bright_blue bold]stegcore wizard[/bright_blue bold]\n"
        "[dim]Power users:[/dim]  stegcore embed / extract / score / info / ciphers --help"
    ),
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()

# Colour constants
ACCENT = "bright_blue"
GOOD   = "bright_green"
WARN   = "yellow"
ERR    = "bright_red"
MUTED  = "dim"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _banner() -> None:
    console.print(
        Panel(
            Text.assemble(
                ("stegcore", "bold white"),
                ("  v2.0.1", MUTED),
                ("  |  ", MUTED),
                ("AGPL-3.0", MUTED),
            ),
            border_style=ACCENT,
            padding=(0, 2),
        )
    )


def _err(msg: str) -> None:
    console.print(f"\n[{ERR}]✗  Error:[/{ERR}]  {msg}\n")
    raise typer.Exit(1)


def _warn(msg: str) -> None:
    console.print(f"[{WARN}]⚠  {msg}[/{WARN}]")


def _ok(msg: str) -> None:
    console.print(f"[{GOOD}]✓[/{GOOD}]  {msg}")


def _hint(msg: str) -> None:
    console.print(f"  [{MUTED}]{msg}[/{MUTED}]")


def _section(title: str) -> None:
    console.print(Rule(f"[{ACCENT} bold]{title}[/{ACCENT} bold]", style=MUTED))


def _read_secret(prompt_text: str) -> str:
    """
    Read a secret string without echo.

    When stdin IS a real terminal (interactive use), Prompt.ask(password=True)
    is used — this calls getpass.getpass() which opens /dev/tty directly,
    suppresses echo, and gives the user a proper hidden-input experience.

    When stdin is NOT a tty (subprocess pipe, shell redirect, test harness),
    getpass would open /dev/tty and block indefinitely waiting for keyboard
    input that never arrives — causing the process to hang until killed.
    In that case we read plainly from sys.stdin, which is where the caller
    actually piped the data. No echo suppression is attempted because there
    is no terminal to echo to anyway.
    """
    if sys.stdin.isatty():
        return Prompt.ask(f"[{ACCENT}]{prompt_text}[/{ACCENT}]", password=True)
    else:
        # Non-interactive: stdin is a pipe or redirect.
        # Print prompt to stderr so it doesn't pollute stdout captures.
        sys.stderr.write(f"{prompt_text}: ")
        sys.stderr.flush()
        return sys.stdin.readline().rstrip("\n")


def _fmt_bytes(n: int) -> str:
    if n >= 1_048_576:
        return f"{n / 1_048_576:.2f} MB"
    if n >= 1_024:
        return f"{n / 1_024:.1f} KB"
    return f"{n} B"


def _score_colour(label: str) -> str:
    return {"Excellent": GOOD, "Good": ACCENT, "Fair": WARN, "Poor": ERR}.get(label, MUTED)


def _strength_hint(pw: str) -> None:
    if len(pw) < 8:
        _warn("Weak passphrase — consider using 14+ random characters.")
    elif len(pw) < 14:
        console.print(f"  [{WARN}]~  Moderate strength passphrase.[/{WARN}]")
    else:
        _ok("Strong passphrase.")


# ---------------------------------------------------------------------------
# Passphrase prompt — shared by power commands and wizard
# ---------------------------------------------------------------------------

def _ask_passphrase(
    label: str = "Passphrase",
    confirm: bool = False,
    hint: str = "",
    retries: int = 3,
) -> str:
    """
    Prompt for a passphrase with optional confirmation.
    Retries up to `retries` times on mismatch or empty input.
    Raises typer.Exit(1) after exhausting retries.
    """
    if hint:
        _hint(hint)

    for attempt in range(1, retries + 1):
        pw = _read_secret(label)

        if not pw or not pw.strip():
            if attempt < retries:
                _warn(f"Passphrase cannot be empty. ({retries - attempt} attempt(s) left)")
                continue
            _err("Passphrase cannot be empty.")

        if len(pw) < 4:
            if attempt < retries:
                _warn(f"Passphrase must be at least 4 characters. ({retries - attempt} left)")
                continue
            _err("Passphrase too short — minimum 4 characters.")

        if confirm:
            pw2 = _read_secret(f"Confirm {label.lower()}")
            if pw != pw2:
                if attempt < retries:
                    _warn(f"Passphrases do not match. ({retries - attempt} attempt(s) left)")
                    continue
                _err("Passphrases do not match after multiple attempts.")

        _strength_hint(pw)
        return pw

    _err("Too many failed passphrase attempts.")


# ---------------------------------------------------------------------------
# File prompt — used in wizard
# ---------------------------------------------------------------------------

def _ask_file(
    label: str,
    hint: str = "",
    must_exist: bool = True,
    extensions: list[str] | None = None,
    retries: int = 3,
) -> Path:
    """
    Prompt for a file path with validation.
    Extensions should be lowercase including dot, e.g. ['.png', '.bmp'].
    """
    if hint:
        _hint(hint)

    for attempt in range(1, retries + 1):
        raw = Prompt.ask(f"[{ACCENT}]{label}[/{ACCENT}]").strip()

        if not raw:
            if attempt < retries:
                _warn(f"Path cannot be empty. ({retries - attempt} left)")
                continue
            _err("No file path provided.")

        p = Path(raw).expanduser()

        if must_exist and not p.exists():
            if attempt < retries:
                _warn(f"File not found: {p}  ({retries - attempt} left)")
                continue
            _err(f"File not found: {p}")

        if extensions and p.suffix.lower() not in extensions:
            ext_str = ", ".join(extensions)
            if attempt < retries:
                _warn(f"Expected one of: {ext_str}  ({retries - attempt} left)")
                continue
            _err(f"Unsupported file type '{p.suffix}'. Expected: {ext_str}")

        return p

    _err("Too many invalid file paths.")


# ---------------------------------------------------------------------------
# Spinner helper for long operations
# ---------------------------------------------------------------------------

def _run_with_spinner(label: str, fn, *args, **kwargs):
    """
    Run fn(*args, **kwargs) while showing an indeterminate spinner.
    Returns the result. Raises on exception.
    """
    with Progress(
        SpinnerColumn(style=ACCENT),
        TextColumn(f"[{MUTED}]{label}[/{MUTED}]"),
        TimeElapsedColumn(),
        transient=False,
        console=console,
    ) as prog:
        task = prog.add_task(label, total=None)
        result = fn(*args, **kwargs)
        prog.update(task, completed=1, total=1)
    return result


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------

@app.command()
def score(
    image: Path = typer.Argument(..., help="Cover image to analyse (PNG, BMP, JPEG)."),
) -> None:
    """
    Analyse a cover image and report its steganographic quality score.

    [dim]Higher entropy and texture density = harder to detect.[/dim]
    """
    _banner()

    if not image.exists():
        _err(f"File not found: {image}")
    if not image.is_file():
        _err(f"Not a file: {image}")

    valid_exts = {".png", ".bmp", ".jpg", ".jpeg"}
    if image.suffix.lower() not in valid_exts:
        _err(f"Unsupported format '{image.suffix}'. Supported: {', '.join(sorted(valid_exts))}")

    try:
        result = _run_with_spinner("Analysing cover image…", steg.score_cover_image, image)
    except Exception as exc:
        _err(f"Could not analyse image: {exc}")

    label     = result["label"]
    score_val = result["score"]
    col       = _score_colour(label)

    score_text = Text.assemble(
        (f"{score_val}", col + " bold"),
        (" / 100  ", MUTED),
        (f"{label}", col + " bold"),
    )
    console.print(Panel(score_text, title="Cover Score", border_style=col, padding=(0, 2)))

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("key",   style=MUTED,  no_wrap=True)
    t.add_column("value", style="white")
    t.add_row("Dimensions",          f"{result['width']} × {result['height']} px")
    t.add_row("Entropy",             f"{result['entropy']:.2f} / 8.00 bits")
    t.add_row("Texture density",     f"{result['texture_density'] * 100:.1f}%")
    t.add_row("Adaptive capacity",   _fmt_bytes(result["adaptive_capacity"]))
    t.add_row("Sequential capacity", _fmt_bytes(result["sequential_capacity"]))
    console.print(t)

    if label == "Poor":
        console.print(f"[{ERR}]  ✗  Poor cover choice — try a larger or more complex image.[/{ERR}]\n")
    elif label == "Fair":
        console.print(f"[{WARN}]  ⚠  Usable, but a higher-entropy cover is recommended.[/{WARN}]\n")
    else:
        console.print(f"[{GOOD}]  ✓  Good cover image.[/{GOOD}]\n")


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------

@app.command()
def embed(
    cover:      Path = typer.Argument(..., help="Cover file (PNG, BMP, JPEG, WAV)."),
    payload:    Path = typer.Argument(..., help="Text file to hide."),
    output:     Path = typer.Argument(..., help="Output stego file path."),
    key_out:    Optional[Path] = typer.Option(None, "--key", "-k",
                    help="Key file save path (default: <output>.key.json)."),
    cipher:     str  = typer.Option("Ascon-128", "--cipher", "-c",
                    help="Encryption cipher [Ascon-128 | ChaCha20-Poly1305 | AES-256-GCM]."),
    mode:       str  = typer.Option("adaptive", "--mode", "-m",
                    help="Steg mode for PNG/BMP [adaptive | sequential]."),
    deniable:   bool = typer.Option(False, "--deniable", "-d",
                    help="Deniable dual-payload (adaptive PNG/BMP only)."),
    passphrase: Optional[str] = typer.Option(None, "--passphrase", "-p",
                    help="Passphrase (omit to be prompted securely)."),
    force:      bool = typer.Option(False, "--force", "-f",
                    help="Overwrite output without prompting."),
    no_score:   bool = typer.Option(False, "--no-score",
                    help="Skip cover image scoring."),
) -> None:
    """
    Embed an encrypted payload inside a cover file.

    [dim]Examples:
      stegcore embed photo.png secret.txt stego.png
      stegcore embed photo.png secret.txt stego.png --cipher AES-256-GCM
      stegcore embed photo.png secret.txt stego.png --deniable
      stegcore embed photo.png secret.txt stego.png --force --no-score --passphrase "..."[/dim]
    """
    _banner()
    _do_embed(
        cover=cover, payload=payload, output=output,
        key_out=key_out, cipher=cipher, mode=mode, deniable=deniable,
        passphrase=passphrase, force=force, no_score=no_score,
    )


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

@app.command()
def extract(
    stego:      Path = typer.Argument(..., help="Stego file to extract from."),
    key_file:   Path = typer.Argument(..., help="Key file (.json) from embedding."),
    output:     Path = typer.Argument(..., help="Where to save the recovered text."),
    passphrase: Optional[str] = typer.Option(None, "--passphrase", "-p",
                    help="Passphrase (omit to be prompted securely)."),
    force:      bool = typer.Option(False, "--force", "-f",
                    help="Overwrite output without prompting."),
) -> None:
    """
    Extract and decrypt a hidden payload from a stego file.

    [dim]Examples:
      stegcore extract stego.png stego.key.json recovered.txt
      stegcore extract stego.png decoy.key.json recovered.txt[/dim]
    """
    _banner()
    _do_extract(
        stego=stego, key_file=key_file, output=output,
        passphrase=passphrase, force=force,
    )


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

@app.command()
def info(
    key_file: Path = typer.Argument(..., help="Key file to inspect."),
) -> None:
    """
    Display the metadata stored in a key file.

    [dim]Does not require the stego file or passphrase.[/dim]
    """
    _banner()

    if not key_file.exists():
        _err(f"Key file not found: {key_file}")
    if key_file.suffix.lower() != ".json":
        _warn(f"Expected a .json key file, got '{key_file.suffix}'. Attempting anyway…")

    try:
        d = crypto.read_key_file(key_file)
    except ValueError as exc:
        _err(str(exc))
    except Exception as exc:
        _err(f"Unexpected error reading key file: {exc}")

    t = Table(box=box.ROUNDED, show_header=False, padding=(0, 2), border_style=ACCENT)
    t.add_column("field", style=MUTED,   no_wrap=True)
    t.add_column("value", style="white")
    t.add_row("File",          str(key_file))
    t.add_row("Cipher",        d["cipher"])
    t.add_row("Steg mode",     d["steg_mode"])
    t.add_row("Deniable",      "yes" if d["deniable"] else "no")
    t.add_row("Payload type",  d.get("info_type", "unknown"))
    if d["deniable"]:
        half = d.get("partition_half")
        t.add_row("Partition half", "0 — real key" if half == 0 else "1 — decoy key")
    console.print(t)
    console.print()


# ---------------------------------------------------------------------------
# ciphers
# ---------------------------------------------------------------------------

@app.command()
def ciphers() -> None:
    """List all supported encryption ciphers."""
    _banner()
    t = Table(box=box.SIMPLE, padding=(0, 2))
    t.add_column("Cipher",   style=ACCENT + " bold")
    t.add_column("Type",     style=MUTED)
    t.add_column("Key size", style=MUTED)
    t.add_column("Notes",    style=MUTED)
    for row in [
        ("Ascon-128",         "AEAD", "128-bit", "Lightweight, NIST standard — default"),
        ("ChaCha20-Poly1305", "AEAD", "256-bit", "Fast in software, no AES hardware needed"),
        ("AES-256-GCM",       "AEAD", "256-bit", "Hardware-accelerated on most modern CPUs"),
    ]:
        t.add_row(*row)
    console.print(t)
    _hint("All ciphers use Argon2id key derivation.")
    console.print()


# ---------------------------------------------------------------------------
# wizard — guided interactive mode for new / basic users
# ---------------------------------------------------------------------------

@app.command()
def wizard() -> None:
    """
    Guided step-by-step mode for new users.

    [dim]Walks you through embedding or extracting without needing to remember any flags.[/dim]
    """
    _banner()
    console.print(
        Panel(
            "[white]Welcome to the Stegcore wizard.\n"
            "This will guide you through hiding or recovering a secret message\n"
            "inside an ordinary image or audio file, step by step.[/white]\n\n"
            f"[{MUTED}]If you already know the CLI, you can skip this and use:\n"
            f"  stegcore embed / extract / score --help[/{MUTED}]",
            border_style=ACCENT,
            padding=(1, 2),
        )
    )
    console.print()

    # ── Choose operation ──────────────────────────────────────────────────
    _section("What would you like to do?")
    console.print(f"  [white]1[/white]  [{GOOD}]Embed[/{GOOD}]   — hide an encrypted message inside a file")
    console.print(f"  [white]2[/white]  [{ACCENT}]Extract[/{ACCENT}] — recover a hidden message from a file")
    console.print(f"  [white]3[/white]  [{MUTED}]Score[/{MUTED}]   — check how good a file is as a cover")
    console.print(f"  [white]4[/white]  [{MUTED}]Exit[/{MUTED}]")
    console.print()

    choice_raw = Prompt.ask(
        f"[{ACCENT}]Enter 1, 2, 3, or 4[/{ACCENT}]",
        choices=["1", "2", "3", "4"],
        show_choices=False,
    )
    choice = int(choice_raw)

    if choice == 4:
        console.print(f"\n[{MUTED}]Goodbye.[/{MUTED}]\n")
        raise typer.Exit(0)

    if choice == 3:
        console.print()
        _section("Score a cover file")
        img = _ask_file(
            "Path to the image file",
            hint="Enter the full or relative path to a PNG, BMP, or JPEG file.",
            extensions=[".png", ".bmp", ".jpg", ".jpeg"],
        )
        score(image=img)
        return

    if choice == 1:
        _wizard_embed()
    else:
        _wizard_extract()


def _wizard_embed() -> None:
    """Guided embed flow."""
    console.print()
    _section("Embed — hide a message")
    _hint("You will need: a text file (your message), a cover image or audio file, and a passphrase.")
    console.print()

    # ── Cover file ────────────────────────────────────────────────────────
    console.print(f"[{ACCENT} bold]Step 1 of 5 — Cover file[/{ACCENT} bold]")
    _hint("This is the file your message will be hidden inside.")
    _hint("Supported: PNG, BMP, JPEG, WAV")
    cover = _ask_file(
        "Path to cover file",
        extensions=[".png", ".bmp", ".jpg", ".jpeg", ".wav"],
    )
    console.print()

    # Show score inline
    fmt = cover.suffix.lower()
    if fmt in {".png", ".bmp", ".jpg", ".jpeg"}:
        _hint("Checking cover quality…")
        try:
            s = _run_with_spinner("Scoring cover image…", steg.score_cover_image, cover)
            col = _score_colour(s["label"])
            console.print(
                f"  Cover score: [{col} bold]{s['score']}/100 — {s['label']}[/{col} bold]"
                f"  [{MUTED}](adaptive capacity: {_fmt_bytes(s['adaptive_capacity'])})[/{MUTED}]"
            )
            if s["score"] < 35:
                _warn("This is a poor cover. Detection is more likely.")
                if not Confirm.ask("Continue with this cover anyway?", default=False):
                    _hint("Pick a better cover and run the wizard again.")
                    raise typer.Exit(0)
            elif s["adaptive_capacity"] < 1024:
                _warn(f"Very low capacity ({_fmt_bytes(s['adaptive_capacity'])}). "
                      "Your message may not fit.")
        except typer.Exit:
            raise
        except Exception as exc:
            _warn(f"Could not score cover: {exc}")
    console.print()

    # ── Payload ───────────────────────────────────────────────────────────
    console.print(f"[{ACCENT} bold]Step 2 of 5 — Message file[/{ACCENT} bold]")
    _hint("This is the text file containing the message you want to hide.")
    _hint("It must be a plain .txt file.")
    payload = _ask_file(
        "Path to your message file (.txt)",
        extensions=[".txt"],
    )
    sz = payload.stat().st_size
    _ok(f"Message: {payload.name}  ({_fmt_bytes(sz)})")
    console.print()

    # ── Output path ───────────────────────────────────────────────────────
    console.print(f"[{ACCENT} bold]Step 3 of 5 — Output file[/{ACCENT} bold]")
    _hint("Where to save the stego file (the cover with the hidden message).")
    out_ext = ".wav" if fmt == ".wav" else ".png"
    if fmt in {".jpg", ".jpeg"}:
        _hint("JPEG covers are embedded into a PNG — JPEG recompression would destroy the hidden data.")
    _hint(f"Output will be saved as {out_ext.upper()}. Example: stego.png")

    for attempt in range(1, 4):
        raw_out = Prompt.ask(f"[{ACCENT}]Save stego file as[/{ACCENT}]").strip()
        if not raw_out:
            _warn(f"Path cannot be empty. ({3 - attempt} left)")
            continue
        output = Path(raw_out).expanduser()
        if output.exists():
            if not Confirm.ask(f"  '{output.name}' already exists. Overwrite?", default=False):
                continue
        break
    else:
        _err("No valid output path provided.")

    key_path = output.with_suffix("").with_suffix(".key.json")
    _hint(f"Key file will be saved as: {key_path.name}")
    console.print()

    # ── Cipher ────────────────────────────────────────────────────────────
    console.print(f"[{ACCENT} bold]Step 4 of 5 — Encryption cipher[/{ACCENT} bold]")
    _hint("All three options are secure. If you're unsure, press Enter to use the default.")
    console.print(f"  [white]1[/white]  Ascon-128          [{MUTED}](default — lightweight, NIST standard)[/{MUTED}]")
    console.print(f"  [white]2[/white]  ChaCha20-Poly1305  [{MUTED}](fast on any hardware)[/{MUTED}]")
    console.print(f"  [white]3[/white]  AES-256-GCM        [{MUTED}](hardware-accelerated)[/{MUTED}]")
    console.print()

    cipher_choice = Prompt.ask(
        f"[{ACCENT}]Choose 1, 2, or 3[/{ACCENT}]",
        choices=["1", "2", "3"],
        default="1",
        show_choices=False,
    )
    cipher = ["Ascon-128", "ChaCha20-Poly1305", "AES-256-GCM"][int(cipher_choice) - 1]
    _ok(f"Cipher: {cipher}")
    console.print()

    # ── Deniable ──────────────────────────────────────────────────────────
    deniable = False
    if fmt in {".png", ".bmp"}:
        console.print(f"[{ACCENT} bold]Optional — Deniable mode[/{ACCENT} bold]")
        _hint("Deniable mode lets you hide TWO messages in one file.")
        _hint("You provide a real message and a fake 'decoy' message.")
        _hint("If someone forces you to reveal your passphrase, you give them the decoy one.")
        deniable = Confirm.ask("  Enable deniable dual-payload mode?", default=False)
        console.print()

    # ── Passphrase ────────────────────────────────────────────────────────
    console.print(f"[{ACCENT} bold]Step 5 of 5 — Passphrase[/{ACCENT} bold]")
    _hint("This is used to encrypt your message. You will need it to recover the message later.")
    _hint("Use something long and random — at least 14 characters recommended.")
    passphrase = _ask_passphrase("Your passphrase", confirm=True)
    console.print()

    # ── Confirm ───────────────────────────────────────────────────────────
    _section("Summary — please confirm")
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("k", style=MUTED)
    t.add_column("v", style="white")
    t.add_row("Cover file",  str(cover))
    t.add_row("Message",     f"{payload.name}  ({_fmt_bytes(sz)})")
    t.add_row("Output",      str(output))
    t.add_row("Key file",    str(key_path))
    t.add_row("Cipher",      cipher)
    t.add_row("Deniable",    "yes" if deniable else "no")
    console.print(t)
    console.print()

    if not Confirm.ask(f"[{ACCENT}]Proceed with embedding?[/{ACCENT}]", default=True):
        console.print(f"\n[{MUTED}]Cancelled.[/{MUTED}]\n")
        raise typer.Exit(0)

    console.print()
    _do_embed(
        cover=cover, payload=payload, output=output,
        key_out=key_path, cipher=cipher, mode="adaptive",
        deniable=deniable, passphrase=passphrase,
        force=True, no_score=True,
    )


def _wizard_extract() -> None:
    """Guided extract flow."""
    console.print()
    _section("Extract — recover a hidden message")
    _hint("You will need: the stego file, the key file (.json), and the passphrase used when embedding.")
    console.print()

    console.print(f"[{ACCENT} bold]Step 1 of 3 — Stego file[/{ACCENT} bold]")
    _hint("This is the file containing the hidden message.")
    stego = _ask_file(
        "Path to the stego file",
        extensions=[".png", ".bmp", ".wav"],
    )
    console.print()

    console.print(f"[{ACCENT} bold]Step 2 of 3 — Key file[/{ACCENT} bold]")
    _hint("This is the .json key file that was saved when the message was embedded.")
    _hint("Keep this file safe — without it, the message cannot be recovered.")
    key_file = _ask_file(
        "Path to the key file (.json)",
        extensions=[".json"],
    )
    console.print()

    # Show info about the key file so user can confirm it looks right
    try:
        d = crypto.read_key_file(key_file)
        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        t.add_column("k", style=MUTED)
        t.add_column("v", style="white")
        t.add_row("Cipher",   d["cipher"])
        t.add_row("Mode",     d["steg_mode"])
        t.add_row("Deniable", "yes" if d["deniable"] else "no")
        if d["deniable"]:
            half = d.get("partition_half")
            t.add_row("Key type", "real" if half == 0 else "decoy")
        console.print(t)
    except Exception as exc:
        _warn(f"Could not read key file metadata: {exc}")

    console.print()

    console.print(f"[{ACCENT} bold]Step 3 of 3 — Output file[/{ACCENT} bold]")
    _hint("Where to save the recovered text.")

    for attempt in range(1, 4):
        raw_out = Prompt.ask(f"[{ACCENT}]Save recovered text as[/{ACCENT}]").strip()
        if not raw_out:
            _warn(f"Path cannot be empty. ({3 - attempt} left)")
            continue
        output = Path(raw_out).expanduser()
        if output.exists():
            if not Confirm.ask(f"  '{output.name}' already exists. Overwrite?", default=False):
                continue
        break
    else:
        _err("No valid output path provided.")

    console.print()

    console.print(f"[{ACCENT} bold]Passphrase[/{ACCENT} bold]")
    _hint("Enter the passphrase you used when embedding the message.")
    passphrase = _ask_passphrase("Passphrase", confirm=False)
    console.print()

    _do_extract(
        stego=stego, key_file=key_file, output=output,
        passphrase=passphrase, force=True,
    )


# ---------------------------------------------------------------------------
# Core embed logic — shared by `embed` command and wizard
# ---------------------------------------------------------------------------

def _do_embed(
    cover: Path,
    payload: Path,
    output: Path,
    key_out: Optional[Path],
    cipher: str,
    mode: str,
    deniable: bool,
    passphrase: Optional[str],
    force: bool,
    no_score: bool,
) -> None:

    # ── Validate all inputs upfront ───────────────────────────────────────
    if not cover.exists():
        _err(f"Cover file not found: {cover}")
    if not cover.is_file():
        _err(f"Not a file: {cover}")
    if not payload.exists():
        _err(f"Payload file not found: {payload}")
    if not payload.is_file():
        _err(f"Not a file: {payload}")
    if payload.stat().st_size == 0:
        _err(f"Payload file is empty: {payload}")

    fmt = cover.suffix.lower()
    valid_cover_exts = {".png", ".bmp", ".jpg", ".jpeg", ".wav"}
    if fmt not in valid_cover_exts:
        _err(f"Unsupported cover format '{fmt}'. Supported: {', '.join(sorted(valid_cover_exts))}")

    if cipher not in crypto.SUPPORTED_CIPHERS:
        _err(f"Unknown cipher '{cipher}'. Choose from: {', '.join(crypto.SUPPORTED_CIPHERS)}")

    effective_mode = mode if fmt in {".png", ".bmp", ".jpg", ".jpeg"} else "sequential"
    if mode != effective_mode:
        _warn(f"{fmt} does not support mode '{mode}' — using sequential.")

    if deniable and effective_mode != "adaptive":
        _err("Deniable mode requires adaptive PNG, BMP, or JPEG cover.")

    # JPEG covers produce a PNG stego file — JPEG recompression destroys LSBs.
    # Auto-correct the output extension and warn the user.
    if fmt in {".jpg", ".jpeg"} and output.suffix.lower() in {".jpg", ".jpeg"}:
        corrected = output.with_suffix(".png")
        _warn(
            f"JPEG covers are embedded into PNG (JPEG recompression destroys LSBs). "
            f"Saving as '{corrected.name}' instead of '{output.name}'."
        )
        output = corrected

    if output.exists() and not force:
        if not Confirm.ask(f"[{WARN}]'{output.name}' already exists. Overwrite?[/{WARN}]"):
            raise typer.Exit(0)

    key_path = key_out or output.with_suffix("").with_suffix(".key.json")

    # ── Cover score ───────────────────────────────────────────────────────
    if not no_score and fmt in {".png", ".bmp", ".jpg", ".jpeg"}:
        try:
            s = _run_with_spinner("Scoring cover image…", steg.score_cover_image, cover)
            col = _score_colour(s["label"])
            console.print(
                f"  Cover  [{col}]{s['score']}/100 — {s['label']}[/{col}]"
                f"  [{MUTED}]adaptive capacity: {_fmt_bytes(s['adaptive_capacity'])}[/{MUTED}]"
            )
            if s["score"] < 35:
                _warn("Poor cover — embedding may be detectable.")
                if not Confirm.ask("Continue anyway?", default=False):
                    raise typer.Exit(0)
            elif s["adaptive_capacity"] < 1024:
                _warn(f"Very low capacity ({_fmt_bytes(s['adaptive_capacity'])}).")
        except typer.Exit:
            raise
        except Exception as exc:
            _warn(f"Could not score cover image: {exc}")

    # ── Passphrase ────────────────────────────────────────────────────────
    if passphrase is None:
        passphrase = _ask_passphrase("Passphrase", confirm=True)
    elif passphrase:
        _warn("Passphrase passed as argument — visible in shell history.")

    info_type = payload.suffix or ".txt"

    # ── Encrypt ───────────────────────────────────────────────────────────
    try:
        plaintext = payload.read_text(errors="ignore").encode("utf-8")
        if len(plaintext) == 0:
            _err("Payload file is empty after reading.")
        result = _run_with_spinner(
            f"Encrypting with {cipher}…",
            crypto.encrypt, plaintext, passphrase, cipher,
        )
    except typer.Exit:
        raise
    except (ValueError, RuntimeError) as exc:
        _err(f"Encryption failed: {exc}")
    except Exception as exc:
        _err(f"Unexpected error during encryption: {exc}")

    steg_key = result["key"] if effective_mode == "adaptive" else None

    # ── Deniable decoy ────────────────────────────────────────────────────
    decoy_result = decoy_key = partition_seed = None
    if deniable:
        _section("Deniable Mode — Decoy Setup")
        _hint("Provide a plausible-looking decoy message and a separate passphrase.")
        _hint("Someone forcing you to reveal your passphrase gets the decoy one.")
        console.print()

        decoy_path = _ask_file(
            "Path to your decoy message file (.txt)",
            hint="This should be a realistic but innocuous text file.",
            extensions=[".txt"],
        )

        decoy_pw = _ask_passphrase(
            "Decoy passphrase",
            confirm=False,
            hint="Must be different from your real passphrase.",
        )
        if decoy_pw == passphrase:
            _err("Decoy passphrase must differ from the real passphrase.")

        try:
            decoy_text   = decoy_path.read_text(errors="ignore").encode("utf-8")
            decoy_result = _run_with_spinner(
                f"Encrypting decoy with {cipher}…",
                crypto.encrypt, decoy_text, decoy_pw, cipher,
            )
            decoy_key      = decoy_result["key"]
            partition_seed = os.urandom(16)
        except typer.Exit:
            raise
        except (ValueError, RuntimeError, OSError) as exc:
            _err(f"Decoy encryption failed: {exc}")

    # ── Embed ─────────────────────────────────────────────────────────────
    try:
        if deniable:
            _run_with_spinner(
                "Embedding dual payload…",
                steg.embed_deniable,
                cover_path=cover,
                real_payload=result["ciphertext"],
                decoy_payload=decoy_result["ciphertext"],
                output_path=output,
                real_key=steg_key,
                decoy_key=decoy_key,
                partition_seed=partition_seed,
            )
        else:
            def _embed_op():
                with utils.temp_file(".bin") as tmp:
                    tmp.write_bytes(result["ciphertext"])
                    steg.embed(cover, tmp, output, key=steg_key, mode=effective_mode)

            _run_with_spinner("Embedding payload…", _embed_op)
    except typer.Exit:
        raise
    except (ValueError, RuntimeError) as exc:
        _err(f"Embedding failed: {exc}")
    except Exception as exc:
        _err(f"Unexpected error during embedding: {exc}")

    # ── Save key file(s) ──────────────────────────────────────────────────
    try:
        crypto.write_key_file(
            key_path,
            nonce=result["nonce"], salt=result["salt"],
            cipher=cipher, info_type=info_type,
            steg_mode=effective_mode, deniable=deniable,
            partition_seed=partition_seed if deniable else None,
            partition_half=0 if deniable else None,
        )
    except Exception as exc:
        _err(f"Could not save key file: {exc}")

    if deniable:
        decoy_key_path = key_path.with_stem(key_path.stem + ".decoy")
        try:
            crypto.write_key_file(
                decoy_key_path,
                nonce=decoy_result["nonce"], salt=decoy_result["salt"],
                cipher=cipher, info_type=info_type,
                steg_mode=effective_mode, deniable=True,
                partition_seed=partition_seed, partition_half=1,
            )
        except Exception as exc:
            _err(f"Could not save decoy key file: {exc}")

    passphrase = ""  # clear from memory

    # ── Summary ───────────────────────────────────────────────────────────
    console.print()
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("k", style=MUTED, no_wrap=True)
    t.add_column("v", style="white")
    t.add_row("Stego file",  str(output))
    t.add_row("Key file",    str(key_path))
    if deniable:
        t.add_row("Decoy key",  str(decoy_key_path))
    t.add_row("Cipher",      cipher)
    t.add_row("Mode",        effective_mode)
    t.add_row("Payload",     _fmt_bytes(len(plaintext)))

    console.print(Panel(
        t,
        title=f"[{GOOD} bold]✓  Embedding complete[/{GOOD} bold]",
        border_style=GOOD,
    ))

    if deniable:
        console.print(f"\n  [{MUTED}]Keep the real key file and decoy key file separate.\n"
                      f"  Real key:  {key_path}\n"
                      f"  Decoy key: {decoy_key_path}[/{MUTED}]")
    console.print()


# ---------------------------------------------------------------------------
# Core extract logic — shared by `extract` command and wizard
# ---------------------------------------------------------------------------

def _do_extract(
    stego: Path,
    key_file: Path,
    output: Path,
    passphrase: Optional[str],
    force: bool,
) -> None:

    # ── Validate inputs ───────────────────────────────────────────────────
    if not stego.exists():
        _err(f"Stego file not found: {stego}")
    if not stego.is_file():
        _err(f"Not a file: {stego}")
    if not key_file.exists():
        _err(f"Key file not found: {key_file}")
    if not key_file.is_file():
        _err(f"Not a file: {key_file}")
    if stego.stat().st_size == 0:
        _err(f"Stego file is empty: {stego}")

    if output.exists() and not force:
        if not Confirm.ask(f"[{WARN}]'{output.name}' already exists. Overwrite?[/{WARN}]"):
            raise typer.Exit(0)

    # ── Read key file ─────────────────────────────────────────────────────
    try:
        key_data = crypto.read_key_file(key_file)
    except ValueError as exc:
        _err(f"Invalid key file: {exc}")
    except Exception as exc:
        _err(f"Unexpected error reading key file: {exc}")

    # ── Passphrase ────────────────────────────────────────────────────────
    if passphrase is None:
        passphrase = _ask_passphrase("Passphrase", confirm=False)
    elif passphrase:
        _warn("Passphrase passed as argument — visible in shell history.")

    steg_mode = key_data.get("steg_mode", "sequential")
    deniable  = key_data.get("deniable", False)

    try:
        steg_key = (
            crypto.derive_key(passphrase, key_data["salt"], key_data["cipher"])
            if steg_mode == "adaptive" else None
        )
    except Exception as exc:
        _err(f"Key derivation failed: {exc}")

    # ── Extract ───────────────────────────────────────────────────────────
    plaintext = None
    try:
        if deniable:
            def _extract_op():
                raw = steg.extract_deniable(
                    stego,
                    key=steg_key,
                    partition_seed=key_data["partition_seed"],
                    partition_half=key_data["partition_half"],
                )
                return crypto.decrypt({**key_data, "ciphertext": raw}, passphrase)
            plaintext = _run_with_spinner("Extracting and decrypting…", _extract_op)
        else:
            def _extract_op():
                with utils.temp_file(".bin") as tmp:
                    steg.extract(stego, tmp, key=steg_key, mode=steg_mode)
                    ciphertext = tmp.read_bytes()
                    return crypto.decrypt({**key_data, "ciphertext": ciphertext}, passphrase)
            plaintext = _run_with_spinner("Extracting and decrypting…", _extract_op)

    except ValueError as exc:
        _err(f"Extraction or decryption failed: {exc}\n\n"
             f"  This usually means the passphrase is wrong, or the wrong key file was used.")
    except Exception as exc:
        _err(f"Unexpected error during extraction: {exc}")

    # ── Save output ───────────────────────────────────────────────────────
    try:
        recovered = plaintext.decode("utf-8")
        output.write_text(recovered, encoding="utf-8")
    except UnicodeDecodeError:
        _err("Recovered data could not be decoded as UTF-8 text. "
             "The payload may be binary, or the passphrase may be wrong.")
    except OSError as exc:
        _err(f"Could not write output file: {exc}")

    passphrase = ""  # clear from memory

    # ── Summary ───────────────────────────────────────────────────────────
    console.print()
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("k", style=MUTED, no_wrap=True)
    t.add_column("v", style="white")
    t.add_row("Source",    str(stego))
    t.add_row("Recovered", str(output))
    t.add_row("Cipher",    key_data["cipher"])
    t.add_row("Mode",      steg_mode)
    t.add_row("Size",      _fmt_bytes(len(plaintext)))
    if deniable:
        t.add_row("Deniable", "yes")

    console.print(Panel(
        t,
        title=f"[{GOOD} bold]✓  Extraction complete[/{GOOD} bold]",
        border_style=GOOD,
    ))
    console.print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()