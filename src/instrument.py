from pathlib import Path
import datetime as dt

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


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("analysis")


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
    raise NotImplementedError("")

# Validation
def validate(output: str, validators: list) -> list:
    issues = []
    for validator in validators:
        result = globals()[validator](output)
        if result:
            issues.append(result)
    return issues

def validate_output_sentences_2(output: str) -> str:
    # raise NotImplementedError("validate_output_sentences_2 is not implemented yet")
    return f'echo: {output}'

def validate_output_max_length_30(output: str) -> bool:
    raise NotImplementedError("")


def validate_output_min_length_20(output: str) -> str:
    return None if len(output.strip()) > 20 else "Output is too short, must be at least 20 characters"

def validate_output_json_object(output: str) -> bool:
    raise NotImplementedError("")

def validate_output_json_schema(output: str) -> bool:
    raise NotImplementedError("")

# Observation
def run_prompt(prompt: str, trace_id: str, system_message: str = None) -> str:
    raise NotImplementedError("")

def run_prompt(prompt: str, trace_id: str, validators: list, system_message: str = None) -> dict:
    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        response = call_llm(prompt=prompt, system_message=system_message)
        status = "success"
    except Exception as e:
        response = str(e)
        status = "error"

    latency = time.time() - start_time
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


def run_experiment(prompts: dict) -> dict:
    results = []
    trace_id = new_trace_id()
    for prompt in prompts.get("prompts", []):
        for idx in range(prompt.get('runs')):
            result = run_prompt(
                prompt.get('prompt'),
                trace_id=trace_id,
                validators=prompt.get('validators', []),
                system_message=prompt.get('system_message'))
            results.append(result)
            logging.info(json.dumps(result, indent=2))

    summary = {
        "total_runs": len(results),
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "valid_count": sum(1 for r in results if r["is_valid"]),
        "invalid_count": sum(1 for r in results if not r["is_valid"]),
        "success_percentage": (sum(1 for r in results if r["status"] == "success") * 100 / len(results)),
        "avg_latency": round(sum(r["latency"] for r in results) / len(results), 4),
    }

    trace_log = {
        'trace_id': trace_id,
        'runs': results,
        'summary': summary,
    }
    store_log(trace_log, prompts.get('code'), trace_id=trace_id)

    logging.info("\nSUMMARY")
    logging.info(json.dumps(summary, indent=2))
    return trace_log

