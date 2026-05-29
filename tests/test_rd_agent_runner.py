"""Tests for the RD-Agent Docker runner (docker_runner.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stock_rtx4060.factors.rd_agent.docker_runner import (
    _docker_is_running,
    _parse_budget_spent,
    _parse_cycles_complete,
    run_docker_factor_mining,
)


class TestDockerIsRunning:
    def test_returns_true_when_docker_info_succeeds(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert _docker_is_running() is True
            mock_run.assert_called_once_with(["docker", "info"], capture_output=True, timeout=10)

    def test_returns_false_when_docker_info_fails(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert _docker_is_running() is False

    def test_returns_false_on_subprocess_exception(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert _docker_is_running() is False


class TestParseBudgetSpent:
    def test_parses_dollar_format(self) -> None:
        assert _parse_budget_spent("budget_spent=$3.42") == pytest.approx(3.42)

    def test_parses_colon_format(self) -> None:
        assert _parse_budget_spent("budget_spent: 2.50") == pytest.approx(2.5)

    def test_parses_spaced_format(self) -> None:
        assert _parse_budget_spent("Budget Spent = $9.99") == pytest.approx(9.99)

    def test_fallback_dollar_amount(self) -> None:
        # Fallback pattern triggers when "budget_spent" is absent but dollar amount + "spent" are present
        result = _parse_budget_spent("llm cost $1.23 spent on API calls")
        assert result == pytest.approx(1.23)

    def test_returns_zero_on_no_match(self) -> None:
        assert _parse_budget_spent("no budget info here") == pytest.approx(0.0)


class TestParseCyclesComplete:
    def test_parses_equals_format(self) -> None:
        assert _parse_cycles_complete("cycles_complete=3") == 3

    def test_parses_colon_format(self) -> None:
        assert _parse_cycles_complete("cycles_complete: 2") == 2

    def test_returns_zero_on_no_match(self) -> None:
        assert _parse_cycles_complete("no cycles info") == 0


class TestRunDockerFactorMining:
    def test_docker_runner_graceful_skip_no_docker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Docker absent → returns []. No exception raised."""
        monkeypatch.setenv("RDAGENT_ENABLED", "true")
        # Simulate docker info failing
        with patch("stock_rtx4060.factors.rd_agent.docker_runner._docker_is_running", return_value=False):
            result = run_docker_factor_mining()
        assert result == []

    def test_docker_runner_disabled_by_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RDAGENT_ENABLED=false → returns [] immediately."""
        monkeypatch.setenv("RDAGENT_ENABLED", "false")
        with patch("stock_rtx4060.factors.rd_agent.docker_runner._docker_is_running") as mock_docker:
            result = run_docker_factor_mining()
        assert result == []
        mock_docker.assert_not_called()

    def test_docker_runner_timeout(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Timeout triggers kill + returns []. No exception propagated."""
        monkeypatch.setenv("RDAGENT_ENABLED", "true")

        # Fake stdout iterator
        fake_out = MagicMock()
        fake_out.__iter__ = lambda self: iter(["line1\n", "line2\n"])

        fake_proc = MagicMock()
        fake_proc.stdout = fake_out
        fake_proc.kill = MagicMock()
        fake_proc.wait = MagicMock(return_value=0)

        # Use the function to allow test-time patching of the env var check
        with patch("stock_rtx4060.factors.rd_agent.docker_runner._is_rdagent_enabled", return_value=True):
            with patch("stock_rtx4060.factors.rd_agent.docker_runner._docker_is_running", return_value=True):
                with patch("subprocess.Popen", return_value=fake_proc):
                    # Simulate timeout exceeded: deadline = start_time + timeout_min*60
                    # start=1000.0, timeout_min=1 (60s), deadline=1060.0
                    # After reading 2 lines, deadline exceeded → kill triggered
                    # time.monotonic() called: (1) initial check, (2) after each line read
                    # Sequence: 1000.0 (OK) → 1000.0 (OK) → 1060.1 (EXCEEDED → kill + break)
                    with patch("time.monotonic", side_effect=[1000.0, 1000.0, 1060.1]):
                        result = run_docker_factor_mining(timeout_min=1)

        fake_proc.kill.assert_called_once()
        assert result == []

    def test_docker_runner_budget_exceeded_log(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """budget_spent > budget_limit → warning logged."""
        monkeypatch.setenv("RDAGENT_ENABLED", "true")

        # Create a fake output dir with a factor file
        session_id = "rd_20260529_test123"
        discovered = tmp_path / "discovered" / session_id
        discovered.mkdir(parents=True, exist_ok=True)

        fake_factor = discovered / "rd_momentum.py"
        fake_factor.write_text("class RdMomentum: pass\n")

        fake_out = MagicMock()
        fake_out.__iter__ = lambda self: iter(["budget_spent=$15.00\ncycles_complete=1\n"])

        fake_proc = MagicMock()
        fake_proc.stdout = fake_out
        fake_proc.kill = MagicMock()
        fake_proc.wait = MagicMock(return_value=0)

        with patch("stock_rtx4060.factors.rd_agent.docker_runner._is_rdagent_enabled", return_value=True):
            with patch("stock_rtx4060.factors.rd_agent.docker_runner._docker_is_running", return_value=True):
                with patch("subprocess.Popen", return_value=fake_proc):
                    with patch("stock_rtx4060.factors.rd_agent.docker_runner._DISCOVERED_DIR", tmp_path / "discovered"):
                        with patch("time.strftime", return_value="20260529"):
                            with patch("uuid.uuid4", return_value=MagicMock(hex="abc123")):
                                with patch("stock_rtx4060.factors.rd_agent.docker_runner._LOGGER.warning") as warn:
                                    run_docker_factor_mining(budget_usd=10.0, cycles=1)

        assert any("budget exceeded" in str(call.args[0]).lower() for call in warn.call_args_list)


class TestGracefulDegradation:
    def test_never_raises_on_docker_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When Docker is unavailable, the function logs a warning and returns [] silently."""
        monkeypatch.setenv("RDAGENT_ENABLED", "true")
        with patch("stock_rtx4060.factors.rd_agent.docker_runner._docker_is_running", return_value=False):
            # Should not raise — empty list returned
            result = run_docker_factor_mining()
            assert result == []
