"""
Unit tests for instrument.py — normalization, validation, run_prompt, run_experiment.

All LLM calls are mocked; no network access is required.
"""
import json
import sys
from unittest.mock import MagicMock, patch

import pytest

import instrument


# ── info() ────────────────────────────────────────────────────────────────────

class TestInfo:
    def test_returns_dict(self):
        assert isinstance(instrument.info(), dict)

    def test_has_required_keys(self):
        result = instrument.info()
        assert "instrument-name" in result
        assert "instrument-version" in result
        assert "updated" in result

    def test_instrument_name(self):
        assert instrument.info()["instrument-name"] == "ai-observability"

    def test_instrument_version(self):
        assert instrument.info()["instrument-version"] == "0.0.1"


# ── extract_json_candidate() ──────────────────────────────────────────────────

class TestExtractJsonCandidate:
    def test_strips_json_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        assert instrument.extract_json_candidate(raw) == '{"key": "value"}'

    def test_strips_plain_fence(self):
        raw = '```\n{"key": "value"}\n```'
        assert instrument.extract_json_candidate(raw) == '{"key": "value"}'

    def test_extracts_from_mixed_content(self):
        raw = 'Here is the result:\n{"key": "value"}\nThat\'s all.'
        assert instrument.extract_json_candidate(raw) == '{"key": "value"}'

    def test_passthrough_clean_json(self):
        raw = '{"key": "value"}'
        assert instrument.extract_json_candidate(raw) == raw

    def test_passthrough_no_braces(self):
        raw = "just plain text"
        assert instrument.extract_json_candidate(raw) == raw

    def test_nested_json_preserved(self):
        raw = '{"outer": {"inner": 1}}'
        assert instrument.extract_json_candidate(raw) == raw

    def test_strips_leading_whitespace(self):
        raw = '   {"key": "value"}   '
        result = instrument.extract_json_candidate(raw)
        # result is the content between first { and last }
        assert json.loads(result) == {"key": "value"}


# ── validate_output_json_object() ─────────────────────────────────────────────

class TestValidateJsonObject:
    def test_valid_json_no_issues(self):
        assert instrument.validate_output_json_object('{"key": "value"}') == []

    def test_invalid_json_returns_issue(self):
        issues = instrument.validate_output_json_object("not json at all")
        assert len(issues) == 1
        assert "invalid_json" in issues[0]

    def test_markdown_wrapped_json_no_issues(self):
        # The validator tries extract_json_candidate as a fallback
        wrapped = '```json\n{"key": "value"}\n```'
        assert instrument.validate_output_json_object(wrapped) == []

    def test_empty_string_returns_issue(self):
        issues = instrument.validate_output_json_object("")
        assert len(issues) == 1


# ── validate_output_json_schema() ─────────────────────────────────────────────

class TestValidateJsonSchema:
    VALID = '{"concept": "test", "risks": ["r1"], "benefit": ["b1"]}'

    def test_valid_schema_no_issues(self):
        assert instrument.validate_output_json_schema(self.VALID) == []

    def test_wrong_keys_flagged(self):
        bad = '{"concept": "test", "risks": ["r1"], "wrong_key": ["b1"]}'
        assert "wrong_keys" in instrument.validate_output_json_schema(bad)

    def test_concept_not_string_flagged(self):
        bad = '{"concept": 42, "risks": ["r1"], "benefit": ["b1"]}'
        assert "concept_not_string" in instrument.validate_output_json_schema(bad)

    def test_risks_not_list_flagged(self):
        bad = '{"concept": "x", "risks": "not a list", "benefit": ["b1"]}'
        assert "risks_not_string_array" in instrument.validate_output_json_schema(bad)

    def test_benefit_not_string_array_flagged(self):
        bad = '{"concept": "x", "risks": ["r1"], "benefit": [1, 2]}'
        assert "benefit_not_string_array" in instrument.validate_output_json_schema(bad)

    def test_invalid_json_returns_schema_error(self):
        issues = instrument.validate_output_json_schema("not json")
        assert "invalid_json_schema" in issues


# ── validate_output_sentences_1() ────────────────────────────────────────────

class TestValidateSentences1:
    def test_single_sentence_no_issues(self):
        assert instrument.validate_output_sentences_1("Just one sentence") == []

    def test_multiple_sentences_flagged(self):
        issues = instrument.validate_output_sentences_1("One. Two. Three.")
        assert "too_many_sentences" in issues

    def test_exactly_two_sentences(self):
        issues = instrument.validate_output_sentences_1("One. Two.")
        assert "too_many_sentences" in issues


# ── validate_output_min_length_20() ──────────────────────────────────────────

class TestValidateMinLength20:
    def test_short_string_flagged(self):
        issues = instrument.validate_output_min_length_20("short")
        assert "too_short_must_be_20_ch_min" in issues

    def test_long_string_no_issues(self):
        issues = instrument.validate_output_min_length_20("x" * 25)
        assert issues == []

    def test_exactly_20_chars_ok(self):
        assert instrument.validate_output_min_length_20("x" * 20) == []

    def test_whitespace_only_short_flagged(self):
        issues = instrument.validate_output_min_length_20("   ")
        assert "too_short_must_be_20_ch_min" in issues


# ── validate() dispatcher ─────────────────────────────────────────────────────

class TestValidateDispatcher:
    def test_empty_validators_list(self):
        assert instrument.validate("anything", []) == []

    def test_multiple_validators_combined(self):
        short_json = '{"bad'
        issues = instrument.validate(short_json, [
            "validate_output_json_object",
            "validate_output_min_length_20",
        ])
        assert any("invalid_json" in i for i in issues)

    def test_valid_passes_all_validators(self):
        valid = '{"concept": "test", "risks": ["r1"], "benefit": ["b1"]}'
        issues = instrument.validate(valid, [
            "validate_output_json_object",
            "validate_output_json_schema",
        ])
        assert issues == []


# ── run_prompt() ──────────────────────────────────────────────────────────────

class TestRunPrompt:
    MOCK_RESPONSE = '{"concept": "test", "risks": ["r1"], "benefit": ["b1"]}'

    def test_success_structure(self):
        with patch.object(instrument, "call_llm", return_value=self.MOCK_RESPONSE):
            result = instrument.run_prompt(
                prompt="test prompt",
                trace_id="trace-001",
                validators=["validate_output_json_object"],
            )
        assert result["status"] == "success"
        assert result["output"] == self.MOCK_RESPONSE
        assert result["is_valid"] is True
        assert "request_id" in result
        assert "latency" in result
        assert "trace_id" in result
        assert result["trace_id"] == "trace-001"

    def test_llm_error_captured(self):
        with patch.object(instrument, "call_llm", side_effect=Exception("API error")):
            result = instrument.run_prompt(
                prompt="test prompt",
                trace_id="trace-002",
                validators=[],
            )
        assert result["status"] == "error"
        assert "API error" in result["output"]

    def test_normalization_applied(self):
        wrapped = '```json\n{"key": "value"}\n```'
        with patch.object(instrument, "call_llm", return_value=wrapped):
            result = instrument.run_prompt(
                prompt="test prompt",
                trace_id="trace-003",
                validators=[],
                apply_json_normalization=True,
            )
        assert result["output"] == '{"key": "value"}'

    def test_normalization_not_applied_by_default(self):
        wrapped = '```json\n{"key": "value"}\n```'
        with patch.object(instrument, "call_llm", return_value=wrapped):
            result = instrument.run_prompt(
                prompt="test prompt",
                trace_id="trace-004",
                validators=[],
            )
        assert result["output"] == wrapped

    def test_invalid_output_flagged(self):
        with patch.object(instrument, "call_llm", return_value="not json"):
            result = instrument.run_prompt(
                prompt="test prompt",
                trace_id="trace-005",
                validators=["validate_output_json_object"],
            )
        assert result["is_valid"] is False
        assert len(result["issues"]) > 0

    def test_system_message_forwarded(self):
        with patch.object(instrument, "call_llm", return_value="ok") as mock_llm:
            instrument.run_prompt(
                prompt="p",
                trace_id="t",
                validators=[],
                system_message="be precise",
            )
        mock_llm.assert_called_once_with(prompt="p", system_message="be precise")

    def test_latency_is_non_negative(self):
        with patch.object(instrument, "call_llm", return_value="ok"):
            result = instrument.run_prompt("p", "t", [])
        assert result["latency"] >= 0

    def test_output_length_matches(self):
        resp = "hello world"
        with patch.object(instrument, "call_llm", return_value=resp):
            result = instrument.run_prompt("p", "t", [])
        assert result["output_length"] == len(resp)


# ── run_experiment() ──────────────────────────────────────────────────────────

class TestRunExperiment:
    VALID_RESPONSE = '{"concept": "x", "risks": ["r1"], "benefit": ["b1"]}'

    def _prompts(self, runs=2):
        return {
            "code": "test_exp",
            "description": "unit test run",
            "prompts": [
                {"prompt": "return json", "runs": runs, "validators": []}
            ],
        }

    def test_returns_trace_and_dataframe(self):
        with patch.object(instrument, "call_llm", return_value=self.VALID_RESPONSE), \
             patch.object(instrument, "store_log"):
            trace_log, pdf = instrument.run_experiment(self._prompts(runs=2))
        assert "trace_id" in trace_log
        assert "summary" in trace_log
        assert len(pdf) == 2

    def test_summary_counts(self):
        with patch.object(instrument, "call_llm", return_value=self.VALID_RESPONSE), \
             patch.object(instrument, "store_log"):
            trace_log, _ = instrument.run_experiment(self._prompts(runs=3))
        summary = trace_log["summary"]
        assert summary["total_runs"] == 3
        assert summary["success_count"] == 3

    def test_success_percentage_all_valid(self):
        with patch.object(instrument, "call_llm", return_value=self.VALID_RESPONSE), \
             patch.object(instrument, "store_log"):
            trace_log, _ = instrument.run_experiment({
                "code": "t",
                "prompts": [
                    {"prompt": "p", "runs": 4, "validators": ["validate_output_json_object"]}
                ],
            })
        assert trace_log["summary"]["valid_count"] == 4
        assert trace_log["summary"]["success_percentage"] == 100.0

    def test_invalid_responses_counted(self):
        with patch.object(instrument, "call_llm", return_value="not json"), \
             patch.object(instrument, "store_log"):
            trace_log, _ = instrument.run_experiment({
                "code": "t",
                "prompts": [
                    {"prompt": "p", "runs": 2, "validators": ["validate_output_json_object"]}
                ],
            })
        assert trace_log["summary"]["invalid_count"] == 2
        assert trace_log["summary"]["valid_count"] == 0

    def test_store_log_called(self):
        with patch.object(instrument, "call_llm", return_value=self.VALID_RESPONSE), \
             patch.object(instrument, "store_log") as mock_store:
            instrument.run_experiment(self._prompts())
        mock_store.assert_called_once()

    def test_avg_latency_present(self):
        with patch.object(instrument, "call_llm", return_value=self.VALID_RESPONSE), \
             patch.object(instrument, "store_log"):
            trace_log, _ = instrument.run_experiment(self._prompts())
        assert trace_log["summary"]["avg_latency"] >= 0
