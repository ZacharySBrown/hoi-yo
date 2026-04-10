"""Validators for Clausewitz-format output files.

Checks bracket matching, encoding correctness, and runs the full suite
against a given file path.
"""

from __future__ import annotations

from pathlib import Path


def validate_brackets(content: str) -> list[str]:
    """Check that every ``{`` has a matching ``}``.

    Returns a list of error strings (empty == valid).
    """
    errors: list[str] = []
    depth = 0
    for lineno, line in enumerate(content.splitlines(), start=1):
        # Skip comments
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for ch in line:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    errors.append(f"Line {lineno}: unexpected closing brace")
                    depth = 0  # reset to keep scanning
    if depth > 0:
        errors.append(f"Unclosed braces: {depth} opening brace(s) without matching close")
    return errors


def validate_encoding(path: Path, expect_bom: bool = False) -> list[str]:
    """Verify the file is valid UTF-8 and check BOM expectation.

    Parameters
    ----------
    path:
        Path to the file to check.
    expect_bom:
        If *True*, the file **must** start with a UTF-8 BOM.
        If *False* (default for HOI4 strategy files), the file must **not**
        have a BOM.
    """
    errors: list[str] = []
    raw = path.read_bytes()

    # UTF-8 decodability
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"Not valid UTF-8: {exc}")
        return errors  # no point checking BOM if decode failed

    bom = b"\xef\xbb\xbf"
    has_bom = raw.startswith(bom)

    if expect_bom and not has_bom:
        errors.append("Expected UTF-8 BOM but file does not start with one")
    elif not expect_bom and has_bom:
        errors.append("File starts with UTF-8 BOM but BOM is not expected")

    return errors


def validate_file(path: Path) -> list[str]:
    """Run all validators against *path*. Returns combined error list."""
    errors: list[str] = []

    if not path.exists():
        return [f"File does not exist: {path}"]

    # Encoding (HOI4 strategy files: no BOM)
    errors.extend(validate_encoding(path, expect_bom=False))

    # Bracket matching
    content = path.read_text(encoding="utf-8")
    errors.extend(validate_brackets(content))

    return errors
