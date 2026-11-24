"""One-line roast: the gadget you use every day.

Copies line.txt (the entry, one line, 1-200 characters) to
/output/entry.txt byte for byte. MAKEFUN_OUTPUT_DIR, when set, stands
in for /output so the entry can be tested locally.

Usage:
    python3 main.py            # write /output/entry.txt
    python3 main.py --check    # validate line.txt only, write nothing

Fails loudly if anything is off: the entry is not valid UTF-8, it is
not 1-200 characters, it is only white space, it has leading or
trailing white space, it contains a line break, or the written copy
differs from line.txt in size or bytes. Every failure reports the
actual value against the expected value, so a bad entry cannot pass
silently.

Standard library only. No network, no randomness, no timestamps.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LINE_FILE = HERE / "line.txt"
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
OUTPUT_FILE = OUTPUT_DIR / "entry.txt"

MIN_CHARS = 1
MAX_CHARS = 200


def load_entry() -> tuple[bytes, str]:
    """Read line.txt and return (raw bytes, decoded text).

    Raises RuntimeError with the actual value when the entry is not
    valid UTF-8, is outside 1-200 characters, is only white space,
    has leading or trailing white space, or contains a line break.
    """
    try:
        source = LINE_FILE.read_bytes()
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"line.txt not found at {LINE_FILE}, "
            "expected the entry file next to main.py"
        ) from exc
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"line.txt is not valid UTF-8: {exc}") from exc

    if not MIN_CHARS <= len(text) <= MAX_CHARS:
        raise RuntimeError(
            f"entry is {len(text)} characters, "
            f"allowed {MIN_CHARS}-{MAX_CHARS}"
        )
    if not text.strip():
        raise RuntimeError("entry must not be only white space")
    if text != text.strip():
        raise RuntimeError(
            "entry must not have leading or trailing white space: "
            f"got {len(text)} characters, stripped to {len(text.strip())}"
        )
    if "\n" in text or "\r" in text:
        raise RuntimeError("entry must be a single line, no line breaks")
    bad = [c for c in text if ord(c) < 0x20 or ord(c) == 0x7F]
    if bad:
        raise RuntimeError(
            "entry must not contain control characters: "
            f"found {len(bad)} (first U+{ord(bad[0]):04X})"
        )
    return source, text


def verify_copy(source: bytes, written: bytes) -> None:
    """Check the written copy against the source, byte for byte.

    Raises RuntimeError naming the first differing byte (with the
    actual and expected byte values) or the size mismatch.
    """
    if len(written) != len(source):
        raise RuntimeError(
            f"copy size differs: wrote {len(written)} bytes, "
            f"source is {len(source)} bytes"
        )
    if written != source:
        offset = next(
            i for i, (a, b) in enumerate(zip(written, source)) if a != b
        )
        raise RuntimeError(
            f"copy bytes differ from line.txt: first difference at "
            f"byte {offset} (wrote 0x{written[offset]:02x}, "
            f"source is 0x{source[offset]:02x})"
        )


def write_entry(source: bytes, text: str) -> str:
    """Write source to the output file, verify the copy, return sha256.

    The digest is computed over the bytes actually read back from
    disk, not over the in-memory source, so it proves what landed.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_bytes(source)

    written = OUTPUT_FILE.read_bytes()
    verify_copy(source, written)

    digest = hashlib.sha256(written).hexdigest()
    print(
        f"wrote {OUTPUT_FILE} ({len(source)} bytes, "
        f"{len(text)} characters, sha256 {digest})"
    )
    return digest


def check_entry() -> str:
    """Validate line.txt without writing anything; return its sha256.

    Used by `python3 main.py --check`: the entry is loaded and
    validated exactly as for a write, then its digest is reported
    and no output file is created or touched.
    """
    source, text = load_entry()
    digest = hashlib.sha256(source).hexdigest()
    print(
        f"entry ok: {len(source)} bytes, {len(text)} characters, "
        f"sha256 {digest} (no output written)"
    )
    return digest


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the command line: only --check is accepted."""
    parser = argparse.ArgumentParser(
        description="Copy line.txt to /output/entry.txt (or validate it)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate line.txt only, write no output file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point: validate, then write the entry (unless --check)."""
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.check:
        check_entry()
        return
    source, text = load_entry()
    write_entry(source, text)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
