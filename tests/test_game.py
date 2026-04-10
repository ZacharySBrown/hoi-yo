"""Tests for game controller, save watcher, settings, and CLI."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.cli import cli
from src.game.controller import GameController
from src.game.save_watcher import SaveWatcher
from src.game.settings import configure_hoi4_settings


# ── SaveWatcher ──────────────────────────────────────────────────────

class TestSaveWatcher:
    """SaveWatcher instantiation and configuration."""

    def test_instantiate_with_temp_dir(self, tmp_path: Path) -> None:
        watcher = SaveWatcher(tmp_path)
        assert watcher.save_dir == tmp_path

    def test_save_dir_is_stored(self, tmp_path: Path) -> None:
        save_dir = tmp_path / "saves"
        save_dir.mkdir()
        watcher = SaveWatcher(save_dir)
        assert watcher.save_dir == save_dir
        assert watcher.save_dir.exists()

    def test_stop_is_safe_when_not_running(self, tmp_path: Path) -> None:
        """Calling stop() without calling watch() should not raise."""
        watcher = SaveWatcher(tmp_path)
        watcher.stop()  # should be a no-op


# ── GameController ───────────────────────────────────────────────────

class TestGameController:
    """GameController graceful degradation."""

    def test_handles_missing_executable(self, tmp_path: Path) -> None:
        """launch() should return False when the executable doesn't exist."""
        fake_exe = tmp_path / "nonexistent" / "hoi4"
        controller = GameController(fake_exe)
        result = controller.launch()
        assert result is False

    def test_is_running_when_not_launched(self, tmp_path: Path) -> None:
        """is_running() should return False when no process was started."""
        controller = GameController(tmp_path / "hoi4")
        assert controller.is_running() is False

    def test_xvfb_flag_stored(self, tmp_path: Path) -> None:
        controller = GameController(tmp_path / "hoi4", use_xvfb=True)
        assert controller.use_xvfb is True

    def test_stop_is_safe_when_not_launched(self, tmp_path: Path) -> None:
        """stop() should not raise when no process is running."""
        controller = GameController(tmp_path / "hoi4")
        controller.stop()  # no-op


# ── Settings ─────────────────────────────────────────────────────────

class TestSettings:
    """HOI4 settings.txt configuration."""

    def test_missing_settings_file(self, tmp_path: Path) -> None:
        """Returns False if settings.txt doesn't exist."""
        result = configure_hoi4_settings(tmp_path, plaintext_saves=True)
        assert result is False

    def test_modifies_existing_settings(self, tmp_path: Path) -> None:
        settings_file = tmp_path / "settings.txt"
        settings_file.write_text(textwrap.dedent("""\
            graphics_quality="high"
            save_as_binary="yes"
            autosave="YEARLY"
            fullscreen="yes"
        """))

        result = configure_hoi4_settings(
            tmp_path,
            plaintext_saves=True,
            autosave_interval="MONTHLY",
        )
        assert result is True

        content = settings_file.read_text()
        assert '"no"' in content  # save_as_binary set to no
        assert '"MONTHLY"' in content
        # Preserve other settings
        assert "graphics_quality" in content
        assert "fullscreen" in content

    def test_appends_missing_keys(self, tmp_path: Path) -> None:
        """If the keys don't exist, they should be appended."""
        settings_file = tmp_path / "settings.txt"
        settings_file.write_text("graphics_quality=\"high\"\n")

        result = configure_hoi4_settings(tmp_path, plaintext_saves=True)
        assert result is True

        content = settings_file.read_text()
        assert "save_as_binary" in content
        assert "autosave" in content

    def test_invalid_interval_defaults_to_monthly(self, tmp_path: Path) -> None:
        settings_file = tmp_path / "settings.txt"
        settings_file.write_text('autosave="YEARLY"\n')

        result = configure_hoi4_settings(
            tmp_path,
            plaintext_saves=True,
            autosave_interval="INVALID_VALUE",
        )
        assert result is True

        content = settings_file.read_text()
        assert '"MONTHLY"' in content


# ── CLI ──────────────────────────────────────────────────────────────

class TestCLI:
    """CLI help text and basic invocation."""

    @pytest.fixture()
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_help_text_renders(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "hoi-yo" in result.output
        assert "Hearts of Iron IV" in result.output

    def test_run_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--local" in result.output
        assert "--headless" in result.output
        assert "--speed" in result.output
        assert "--persona" in result.output
        assert "--popcorn" in result.output
        assert "--deep-dive" in result.output

    def test_dashboard_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["dashboard", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output

    def test_swap_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["swap", "--help"])
        assert result.exit_code == 0
        assert "TAG" in result.output
        assert "SOUL_PATH" in result.output

    def test_whisper_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["whisper", "--help"])
        assert result.exit_code == 0
        assert "TAG" in result.output
        assert "MESSAGE" in result.output

    def test_status_no_active_game(self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """status should report 'No active game' when no state file exists."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "No active game found" in result.output

    def test_deploy_placeholder(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["deploy"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output

    def test_run_with_config(self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """run should load config and print the startup banner."""
        monkeypatch.chdir(tmp_path)

        config_content = textwrap.dedent("""\
            [game]
            hoi4_executable = "/fake/hoi4"
            save_dir = "/fake/saves"
            mod_dir = "/fake/mod"
            config_dir = "/fake/config"

            [personas]
            GER = "personas/germany"

            [api]

            [dashboard]
        """)
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)

        result = runner.invoke(cli, ["--config", str(config_file), "run", "--local", "--speed", "4"])
        assert result.exit_code == 0
        assert "Hearts of Iron IV" in result.output or "hoi" in result.output.lower()
        assert "GER" in result.output
        assert "Speed:     4" in result.output

    def test_run_missing_config(self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """run should fail gracefully with a missing config."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["--config", "nonexistent.toml", "run"])
        assert "config file not found" in result.output or result.exit_code != 0

    def test_all_commands_listed_in_help(self, runner: CliRunner) -> None:
        """All subcommands should appear in --help output."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for cmd in ["run", "dashboard", "swap", "whisper", "replay", "status", "deploy"]:
            assert cmd in result.output, f"Command '{cmd}' missing from help output"
