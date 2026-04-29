#!/usr/bin/env python3

import argparse
import datetime as dt
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(message)s")


DEFAULT_SYSTEM_MESSAGE = (
    "You are a precise API that returns only raw JSON when asked for JSON. "
    "Do not include markdown, code fences, commentary, or any extra text."
)

DEFAULT_PROMPT = (
    "Return only valid JSON with exactly these top-level keys: concept, risks, benefit. "
    "concept must be a string. risks must be an array of strings. "
    "benefit must be an array of strings."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lightweight LLM observability harness for structured-output testing."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of repeated runs for each prompt.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="Model name to use.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="json",
        choices=["json", "general"],
        help="Validation mode.",
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        default=None,
        help="Path to a prompt text file. If omitted, uses built-in default prompt.",
    )
    parser.add_argument(
        "--system-file",
        type=str,
        default=None,
        help="Path to a system message text file. If omitted, uses built-in default system message.",
    )
    parser.add_argument(
        "--logs-root",
        type=str,
        default=None,
        help="Directory to store logs. Falls back to LOGS_ROOT_DIR env var, then ./logs",
    )
    parser.add_argument(
        "--session-name",
        type=str,
        default=None,
        help="Optional session name. If omitted, one is generated automatically.",
    )
    parser.add_argument(
        "--note",
        type=str,
        default="Block 3 repeated JSON reliability test",
        help="Optional note stored in the summary.",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=".env.local",
        help="Path to env file for OPENAI_API_KEY and optional LOGS_ROOT_DIR.",
    )
    return parser.parse_args()


def load_text_file(path: str | None, fallback: str) -> str:
    if not path:
        return fallback
    return Path(path).read_text(encoding="utf-8").strip()


def build_prompts(prompt_text: str, runs: int) -> list[str]:
    return [prompt_text for _ in range(runs)]


def resolve_logs_root(cli_value: str | None) -> Path:
    if cli_value:
        return Path(cli_value)
    env_value = os.getenv("LOGS_ROOT_DIR")
    if env_value:
        return Path(env_value)
    return Path("logs")


def build_session_name(explicit_name: str | None) -> str:
    if explicit_name:
        return explicit_name
    return f"block3-{time.time_ns()}"


def ensure_session_dir(logs_root: Path, session_name: str) -> Path:
    session_dir = logs_root / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def persist_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def persist_json(path: Path, record: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)


def extract_json_candidate(output: str) -> str:
    output = output.strip()

    if output.startswith("```json"):
        output = output.removeprefix("```json").strip()
    if output.startswith("```"):
        output = output.removeprefix("```").strip()
    if output.endswith("```"):
        output = output[:-3].strip()

    start = output.find("{")
    end = output.rfind("}")

    if start != -1 and end != -1 and end > start:
        return output[start : end + 1]

    return output


def validate_output(mode: str, prompt: str, raw_output: str) -> tuple[bool, list[str], str | None]:
    issues: list[str] = []
    json_candidate: str | None = None

    if not raw_output.strip():
        issues.append("empty_output")

    if len(raw_output.strip()) < 20:
        issues.append("too_short")

    if mode == "json" or "json" in prompt.lower():
        try:
            json_candidate = extract_json_candidate(raw_output)
            parsed = json.loads(json_candidate)

            required_keys = {"concept", "risks", "benefit"}
            if set(parsed.keys()) != required_keys:
                issues.append("wrong_keys")

            if not isinstance(parsed.get("concept"), str):
                issues.append("concept_not_string")

            risks = parsed.get("risks")
            if not isinstance(risks, list) or not all(isinstance(x, str) for x in risks):
                issues.append("risks_not_string_array")

            benefits = parsed.get("benefit")
            if not isinstance(benefits, list) or not all(isinstance(x, str) for x in benefits):
                issues.append("benefit_not_string_array")

        except Exception:
            issues.append("invalid_json")

    if "one sentence" in prompt.lower():
        sentence_count = raw_output.count(".") + raw_output.count("!") + raw_output.count("?")
        if sentence_count > 1:
            issues.append("too_many_sentences")

    return (len(issues) == 0, issues, json_candidate)


def call_llm(client: OpenAI, model: str, system_message: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


def run_prompt(
    client: OpenAI,
    model: str,
    mode: str,
    system_message: str,
    prompt: str,
    run_index: int,
) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    start_time = time.time()

    try:
        raw_output = call_llm(client, model, system_message, prompt)
        status = "success"
        error_message = None
    except Exception as e:
        raw_output = ""
        status = "error"
        error_message = str(e)

    latency = round(time.time() - start_time, 4)
    is_valid, issues, json_candidate = validate_output(mode, prompt, raw_output)

    processed_output = json_candidate if json_candidate is not None else raw_output

    return {
        "request_id": request_id,
        "run_index": run_index,
        "timestamp_utc": started_at,
        "mode": mode,
        "model": model,
        "prompt": prompt,
        "status": status,
        "error_message": error_message,
        "latency": latency,
        "raw_output": raw_output,
        "processed_output": processed_output,
        "output_length": len(raw_output),
        "is_valid": is_valid,
        "issues": issues,
    }


def build_summary(
    results: list[dict[str, Any]],
    session_name: str,
    note: str,
    system_message: str,
    prompt_source: str,
    model: str,
    mode: str,
) -> dict[str, Any]:
    total_runs = len(results)
    success_count = sum(1 for r in results if r["status"] == "success")
    valid_count = sum(1 for r in results if r["is_valid"])
    invalid_count = total_runs - valid_count
    avg_latency = round(sum(r["latency"] for r in results) / total_runs, 4) if total_runs else 0.0
    json_success_rate = round(valid_count / total_runs, 4) if total_runs else 0.0

    return {
        "session_name": session_name,
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "note": note,
        "mode": mode,
        "model": model,
        "prompt_source": prompt_source,
        "system_message": system_message,
        "total_runs": total_runs,
        "success_count": success_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "avg_latency": avg_latency,
        "json_success_rate": json_success_rate,
    }


def main() -> None:
    args = parse_args()
    load_dotenv(args.env_file)

    system_message = load_text_file(args.system_file, DEFAULT_SYSTEM_MESSAGE)
    prompt_text = load_text_file(args.prompt_file, DEFAULT_PROMPT)
    prompts = build_prompts(prompt_text, args.runs)

    logs_root = resolve_logs_root(args.logs_root)
    session_name = build_session_name(args.session_name)
    session_dir = ensure_session_dir(logs_root, session_name)

    events_path = session_dir / "events.jsonl"
    summary_path = session_dir / "summary.json"

    prompt_source = args.prompt_file if args.prompt_file else "builtin:DEFAULT_PROMPT"

    client = OpenAI()
    results: list[dict[str, Any]] = []

    for idx, prompt in enumerate(prompts, start=1):
        result = run_prompt(
            client=client,
            model=args.model,
            mode=args.mode,
            system_message=system_message,
            prompt=prompt,
            run_index=idx,
        )
        results.append(result)
        persist_jsonl(events_path, result)

        logging.info(f"\n--- RUN {idx} ---")
        logging.info(json.dumps(result, indent=2, ensure_ascii=False))

    summary = build_summary(
        results=results,
        session_name=session_name,
        note=args.note,
        system_message=system_message,
        prompt_source=prompt_source,
        model=args.model,
        mode=args.mode,
    )

    persist_json(summary_path, summary)

    logging.info("\nSUMMARY")
    logging.info(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()