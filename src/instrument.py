from pathlib import Path
import pandas as pd

import json
import logging
import os
import datetime as dt
import time
import uuid
from dotenv import load_dotenv

load_dotenv(".env.local")

SESSION_ID = f'{dt.datetime.now().strftime("%Y-%m-%d")}/{time.time_ns()}-{uuid.uuid4()}'

LOGS_ROOT_DIR = os.environ['LOGS_ROOT_DIR']
assert LOGS_ROOT_DIR, 'LOGS_ROOT_DIR env variable is not set. Please configure .env.local file'

LOGS_SESSION_DIR = os.path.join(LOGS_ROOT_DIR, SESSION_ID)
os.makedirs(LOGS_SESSION_DIR, exist_ok=True)

#
# logging.basicConfig(level=logging.INFO, format='%(message)s')
# logger = logging.getLogger("analysis")

logging.basicConfig(
    filename='logs/system/instrument.log',
    filemode='a',
    level=logging.INFO,
    format='%(message)s'
)

from openai import OpenAI
client = OpenAI()

def info()  -> dict:
    result = {
        "instrument-name": "ai-observability",
        "instrument-version": "0.0.1",
        "updated": dt.datetime.fromtimestamp(Path(__file__).stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
    }
    return result

# system functions
def call_llm(prompt: str, system_message: str = None) -> str:
    messages = []
    if system_message:
        messages.append({ "role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model="gpt-4o-mini", messages=messages,)
    return response.choices[0].message.content or ""

def store_log(log, experiment_name, trace_id):
    os.makedirs(os.path.join(LOGS_SESSION_DIR, experiment_name), exist_ok=True)
    with open(os.path.join(LOGS_SESSION_DIR, experiment_name, f'{trace_id}.json'), 'w') as f:
        f.write(json.dumps(log, indent=2))
        f.close()

def new_trace_id():
    return f'{time.time_ns()}-{uuid.uuid4()}'


# Normalization
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
        return output[start:end + 1]

    return output

# Validation
def validate(output: str, validators: list) -> list:
    issues = []
    for validator in validators:
        result = globals()[validator](output)
        if result:
            issues += result
    return issues

def validate_output_sentences_1(output: str) -> list:
    issues = []
    sentence_count = output.count(".") + output.count("!") + output.count("?")
    if sentence_count > 1:
        issues.append("too_many_sentences")
    return issues


def validate_output_sentences_2(output: str) -> list:
    issues = []
    sentence_count = output.count(".") + output.count("!") + output.count("?")
    if sentence_count == 2:
        issues.append("exactly_two_sentences_expected")
    return issues

def validate_output_max_length_30(output: str) -> list:
    issues = []
    if len(output) < 30:
        issues.append("too_long")
    return issues


def validate_output_min_length_20(output: str) -> list:
    issues = []
    if len(output.strip()) < 20:
        issues.append("too_short_must_be_20_ch_min")
    return issues

def validate_output_json_object(output: str) -> list:
    issues = []
    try:
        json.loads(output)
    except Exception as e:
        try:
            json.loads(extract_json_candidate(output))
        except Exception as e:
            issues.append(f"invalid_json: {str(e)[:10]}")

    return issues

def validate_output_json_schema(output: str) -> list:
    issues = []
    try:
        parsed = json.loads(output)

        required_keys = {"concept", "risks", "benefit"}
        if set(parsed.keys()) != required_keys:
            issues.append("wrong_keys")

        if not isinstance(parsed.get("concept"), str):
            issues.append("concept_not_string")

        if not isinstance(parsed.get("risks"), list) or not all(isinstance(x, str) for x in parsed["risks"]):
            issues.append("risks_not_string_array")

        if not isinstance(parsed.get("benefit"), list) or not all(isinstance(x, str) for x in parsed["benefit"]):
            issues.append("benefit_not_string_array")

    except Exception as e:
        issues.append("invalid_json_schema")

    return issues

# Observation
def run_prompt(prompt: str, trace_id: str, validators: list, system_message: str = None, apply_json_normalization: bool = False) -> dict:
    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        response = call_llm(prompt=prompt, system_message=system_message)
        status = "success"
    except Exception as e:
        response = str(e)
        status = "error"

    latency = time.time() - start_time
    if apply_json_normalization:
        response = extract_json_candidate(response)
    issues = validate(response, validators)
    return {
        "request_id": request_id,
        "trace_id": trace_id,
        "prompt": prompt,
        "output": response,
        "latency": round(latency, 4),
        "output_length": len(response),
        "status": status,
        "is_valid": len(issues) == 0,
        "issues": issues,
    }


def run_experiment(prompts: dict) -> list:
    results = []
    trace_id = new_trace_id()
    issues = []
    data = []
    for prompt in prompts.get("prompts", []):
        for idx in range(prompt.get('runs')):
            result = run_prompt(
                prompt.get('prompt'),
                trace_id=trace_id,
                validators=prompt.get('validators', []),
                system_message=prompt.get('system_message'),
                apply_json_normalization=prompt.get('apply_json_normalization'),
            )
            results.append(result)
            issues += result["issues"]
            logging.info(json.dumps(result, indent=2))
            data.append({
                "scenario": prompt.get("scenario", ""),
                "prompt": prompt.get('prompt'),
                "trace_id": trace_id,
                "validators": prompt.get('validators', []),
                "system_message": prompt.get('system_message'),
                "output": result["output"],
                "issues": result["issues"],
                "latency": round(result["latency"], 4),
                "success": 1 if result["is_valid"] else 0,
            })
    valid_count = sum(1 for r in results if r["is_valid"])
    invalid_count = sum(1 for r in results if not r["is_valid"])
    observed_issue_types = list(set(issues))
    summary = {
        "total_runs": len(results),
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "success_percentage": (valid_count * 100.0 / len(results)),
        "avg_latency": round(sum(r["latency"] for r in results) / len(results), 4),
        "observed_issue_types": observed_issue_types
    }
    pdf = pd.DataFrame(data=data)
    trace_log = {
        'trace_id': trace_id,
        'runs': results,
        'summary': summary,
    }
    store_log(trace_log, prompts.get('code'), trace_id=trace_id)

    logging.info("\nSUMMARY")
    logging.info(json.dumps(summary, indent=2))
    return [trace_log, pdf]

