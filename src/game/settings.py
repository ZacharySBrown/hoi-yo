"""Configure HOI4 settings.txt for automated play.

Modifies the game's settings file in-place, touching only the keys we
care about so that the player's other preferences are preserved.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Valid autosave intervals recognised by HOI4
VALID_INTERVALS = {"MONTHLY", "QUARTERLY", "HALF_YEARLY", "YEARLY", "NEVER"}

SETTINGS_FILENAME = "settings.txt"


def configure_hoi4_settings(
    config_dir: Path,
    plaintext_saves: bool = True,
    autosave_interval: str = "MONTHLY",
) -> bool:
    """Update HOI4 *settings.txt* for automated play.

    Parameters
    ----------
    config_dir:
        The HOI4 user-data directory (contains ``settings.txt``).
    plaintext_saves:
        If ``True``, set ``save_as_binary=no`` so saves are human-readable.
    autosave_interval:
        One of ``MONTHLY``, ``QUARTERLY``, ``HALF_YEARLY``, ``YEARLY``,
        ``NEVER``.

    Returns ``True`` if the file was written, ``False`` if nothing could be
    done (e.g. directory/file missing).
    """
    if autosave_interval.upper() not in VALID_INTERVALS:
        logger.warning(
            "Invalid autosave_interval '%s' -- defaulting to MONTHLY",
            autosave_interval,
        )
        autosave_interval = "MONTHLY"
    else:
        autosave_interval = autosave_interval.upper()

    settings_path = config_dir / SETTINGS_FILENAME
    if not settings_path.exists():
        logger.warning(
            "settings.txt not found at %s -- cannot configure HOI4 settings. "
            "Launch the game once to generate the file.",
            settings_path,
        )
        return False

    logger.info("Configuring HOI4 settings at %s", settings_path)
    content = settings_path.read_text(encoding="utf-8")

    # ── save_as_binary ───────────────────────────────────────────
    binary_value = "no" if plaintext_saves else "yes"
    content, n = re.subn(
        r'(save_as_binary\s*=\s*)"?\w+"?',
        rf'\g<1>"{binary_value}"',
        content,
    )
    if n == 0:
        # Key not present -- append it
        content += f'\nsave_as_binary="{binary_value}"\n'
    logger.info("save_as_binary set to %s", binary_value)

    # ── autosave interval ────────────────────────────────────────
    content, n = re.subn(
        r'(autosave\s*=\s*)"?\w+"?',
        rf'\g<1>"{autosave_interval}"',
        content,
    )
    if n == 0:
        content += f'\nautosave="{autosave_interval}"\n'
    logger.info("autosave interval set to %s", autosave_interval)

    settings_path.write_text(content, encoding="utf-8")
    logger.info("HOI4 settings updated successfully")
    return True
