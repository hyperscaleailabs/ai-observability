"""
Tests for cli.py.

cli.py is a runnable script whose module body calls instrument.run_experiment
immediately. Tests patch run_experiment on the already-imported instrument
module *before* reloading cli, so no real LLM calls are made.
"""
import sys
import importlib
from unittest.mock import patch, MagicMock

import instrument

FAKE_RESULT = (
    {
        "trace_id": "cli-test-trace",
        "runs": [],
        "summary": {
            "total_runs": 2,
            "success_count": 2,
            "valid_count": 2,
            "invalid_count": 0,
            "success_percentage": 100.0,
            "avg_latency": 0.9,
            "observed_issue_types": [],
        },
    },
    MagicMock(),  # pandas DataFrame placeholder
)


def _import_cli():
    """Force a fresh import of cli.py within the current patch context."""
    sys.modules.pop("cli", None)
    return importlib.import_module("cli")


class TestCLI:
    def test_cli_calls_run_experiment(self):
        with patch.object(instrument, "run_experiment", return_value=FAKE_RESULT) as mock_exp, \
             patch("builtins.print"):
            _import_cli()
        mock_exp.assert_called_once()

    def test_cli_passes_prompts_dict(self):
        with patch.object(instrument, "run_experiment", return_value=FAKE_RESULT) as mock_exp, \
             patch("builtins.print"):
            _import_cli()
        call_kwargs = mock_exp.call_args[1]
        assert "prompts" in call_kwargs
        prompts_arg = call_kwargs["prompts"]
        assert isinstance(prompts_arg, dict)
        assert "prompts" in prompts_arg

    def test_cli_experiment_has_at_least_one_prompt(self):
        with patch.object(instrument, "run_experiment", return_value=FAKE_RESULT) as mock_exp, \
             patch("builtins.print"):
            _import_cli()
        prompts = mock_exp.call_args[1]["prompts"]["prompts"]
        assert isinstance(prompts, list)
        assert len(prompts) >= 1

    def test_cli_prompt_entry_has_required_keys(self):
        with patch.object(instrument, "run_experiment", return_value=FAKE_RESULT) as mock_exp, \
             patch("builtins.print"):
            _import_cli()
        entry = mock_exp.call_args[1]["prompts"]["prompts"][0]
        assert "prompt" in entry
        assert "runs" in entry

    def test_cli_prints_result(self):
        with patch.object(instrument, "run_experiment", return_value=FAKE_RESULT), \
             patch("builtins.print") as mock_print:
            _import_cli()
        mock_print.assert_called_once()
