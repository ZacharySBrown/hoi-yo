"""Generic parser for Paradox Clausewitz save/mod format.

The Clausewitz format uses nested key=value pairs with curly braces:

    date="1939.9.1"
    countries={
        GER={
            stability=0.65
            manpower=8500000
        }
    }

Values can be quoted strings, bare identifiers, integers, floats,
dates (YYYY.M.D), or yes/no booleans. Comments start with #.
"""

from __future__ import annotations

import re
from typing import Any


# Pre-compiled patterns for performance
_COMMENT_RE = re.compile(r"#.*$")
_DATE_RE = re.compile(r"^\d{1,4}\.\d{1,2}\.\d{1,2}$")
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


def parse_clausewitz(text: str) -> dict[str, Any]:
    """Parse a Clausewitz-format string into a nested dictionary.

    Args:
        text: Raw Clausewitz-format text content.

    Returns:
        Nested dict representing the parsed structure. Repeated keys at the
        same level are collected into lists automatically.
    """
    tokens = _tokenize(text)
    result, _ = _parse_block(tokens, 0)
    return result


def _tokenize(text: str) -> list[str]:
    """Break raw text into a flat list of tokens.

    Tokens are: '{', '}', '=', quoted strings (with quotes stripped),
    and bare words/values. Comments and whitespace are discarded.
    """
    tokens: list[str] = []
    i = 0
    length = len(text)

    while i < length:
        ch = text[i]

        # Skip whitespace
        if ch in (" ", "\t", "\n", "\r"):
            i += 1
            continue

        # Skip comments
        if ch == "#":
            while i < length and text[i] != "\n":
                i += 1
            continue

        # Structural tokens
        if ch in ("{", "}", "="):
            tokens.append(ch)
            i += 1
            continue

        # Quoted string
        if ch == '"':
            i += 1
            start = i
            while i < length and text[i] != '"':
                if text[i] == "\\" and i + 1 < length:
                    i += 2  # skip escaped char
                else:
                    i += 1
            token = text[start:i]
            tokens.append(token)
            if i < length:
                i += 1  # skip closing quote
            continue

        # Bare word / number / date
        start = i
        while i < length and text[i] not in (" ", "\t", "\n", "\r", "=", "{", "}", "#", '"'):
            i += 1
        token = text[start:i]
        if token:
            tokens.append(token)

    return tokens


def _coerce_value(raw: str) -> Any:
    """Convert a raw string token into the appropriate Python type."""
    if raw == "yes":
        return True
    if raw == "no":
        return False

    # Date check first -- dates look like "1939.9.1" and must not become floats
    if _DATE_RE.match(raw):
        return raw

    if _INT_RE.match(raw):
        return int(raw)

    if _FLOAT_RE.match(raw):
        return float(raw)

    return raw


def _insert(target: dict, key: str, value: Any) -> None:
    """Insert a value into a dict, converting to list on duplicate keys."""
    if key not in target:
        target[key] = value
    else:
        existing = target[key]
        if isinstance(existing, list):
            existing.append(value)
        else:
            target[key] = [existing, value]


def _parse_block(tokens: list[str], pos: int) -> tuple[dict[str, Any], int]:
    """Parse tokens from *pos* until EOF or a closing '}'.

    Returns:
        (parsed_dict, next_position)
    """
    result: dict[str, Any] = {}
    length = len(tokens)

    while pos < length:
        token = tokens[pos]

        if token == "}":
            return result, pos + 1

        # Look ahead to decide what this token is
        # Case 1: key = { ... }   (nested block)
        # Case 2: key = value
        # Case 3: bare value inside a list-like block
        if pos + 1 < length and tokens[pos + 1] == "=":
            key = token
            pos += 2  # skip key and '='

            if pos >= length:
                break

            next_token = tokens[pos]

            if next_token == "{":
                # Could be a sub-block OR a value-list like { 1 2 3 }
                pos += 1  # skip '{'
                block_or_list, pos = _parse_block_or_list(tokens, pos)
                _insert(result, key, block_or_list)
            else:
                _insert(result, key, _coerce_value(next_token))
                pos += 1
        elif token == "{":
            # Orphan opening brace -- parse as anonymous block
            pos += 1
            _block, pos = _parse_block(tokens, pos)
        else:
            # Bare value (inside a list-like context) -- skip it at top level
            pos += 1

    return result, pos


def _parse_block_or_list(tokens: list[str], pos: int) -> tuple[Any, int]:
    """After seeing '{', decide whether the contents form a dict or a flat list.

    Heuristic: if the second non-brace token is '=', it's a dict block.
    Otherwise treat it as a flat value list like { 1 2 3 }.
    """
    # Peek ahead to decide
    if pos < len(tokens) and tokens[pos] == "}":
        # Empty block
        return {}, pos + 1

    is_dict = _looks_like_dict(tokens, pos)

    if is_dict:
        return _parse_block(tokens, pos)
    else:
        return _parse_flat_list(tokens, pos)


def _looks_like_dict(tokens: list[str], pos: int) -> bool:
    """Peek at tokens to guess if this is a key=value block or a flat list."""
    length = len(tokens)
    i = pos

    # Skip through up to a few tokens looking for '='
    depth = 0
    scanned = 0
    while i < length and scanned < 6:
        tok = tokens[i]
        if tok == "{":
            depth += 1
        elif tok == "}":
            if depth == 0:
                return False  # Reached end of block with no '='
            depth -= 1
        elif tok == "=" and depth == 0:
            return True
        i += 1
        scanned += 1

    return False


def _parse_flat_list(tokens: list[str], pos: int) -> tuple[list[Any], int]:
    """Parse a flat list of values until the matching '}'."""
    values: list[Any] = []
    length = len(tokens)

    while pos < length:
        token = tokens[pos]
        if token == "}":
            return values, pos + 1
        if token == "{":
            # Nested structure inside a list -- parse as block
            pos += 1
            block, pos = _parse_block(tokens, pos)
            values.append(block)
        else:
            values.append(_coerce_value(token))
            pos += 1

    return values, pos
