import copy
import json
import os
import sys
from typing import Any


BASE_DIR = os.path.dirname(__file__)
SOURCE_QUESTIONS_PATH = os.path.join(BASE_DIR, "reflection_questions.json")
RUNTIME_QUESTIONS_FILENAME = "reflection_questions.local.json"

DEFAULT_REFLECTION_QUESTIONS = [
    {
        "text": "How many clusters of purple seaweed were in the background?",
        "choices": ["2", "3", "1", "4"],
        "correct": 3,
    },
    {
        "text": "What color was the seashell in the sea background?",
        "choices": ["Blue", "Red", "Purple", "Green"],
        "correct": 2,
    },
    {
        "text": "How many sea rocks were in the background?",
        "choices": ["1", "2", "3", "4"],
        "correct": 1,
    },
    {
        "text": "How many red flowers were in the forest background?",
        "choices": ["2", "3", "1", "4"],
        "correct": 1,
    },
    {
        "text": "What color was the other flower in the forest background?",
        "choices": ["Blue", "Red", "Purple", "Green"],
        "correct": 0,
    },
    {
        "text": "In the space background how many planets were there?",
        "choices": ["1", "2", "3", "4"],
        "correct": 1,
    },
    {
        "text": "What color was the spaceship in the space background?",
        "choices": ["Blue", "Red", "White", "Green"],
        "correct": 2,
    },
]


def _runtime_questions_path() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = BASE_DIR
    return os.path.join(base_dir, RUNTIME_QUESTIONS_FILENAME)


def _read_questions_file(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _normalize_questions(data)


def _normalize_question(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Each question must be an object.")

    text = str(raw.get("text", "")).strip()
    if not text:
        raise ValueError("Question text cannot be empty.")

    raw_choices = raw.get("choices")
    if not isinstance(raw_choices, list):
        raise ValueError("Choices must be a list.")
    if len(raw_choices) != 4:
        raise ValueError("Each question must have exactly 4 choices.")

    choices = [str(choice).strip() for choice in raw_choices]
    if any(not choice for choice in choices):
        raise ValueError("Choices cannot be empty.")

    correct = raw.get("correct")
    if not isinstance(correct, int):
        raise ValueError("Correct answer index must be an integer.")
    if correct < 0 or correct > 3:
        raise ValueError("Correct answer index must be between 0 and 3.")

    return {"text": text, "choices": choices, "correct": correct}


def _normalize_questions(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("Question set must be a list.")
    if not raw:
        raise ValueError("At least one reflection question is required.")
    return [_normalize_question(question) for question in raw]


def get_questions() -> list[dict[str, Any]]:
    runtime_path = _runtime_questions_path()
    if os.path.exists(runtime_path):
        return _read_questions_file(runtime_path)

    if not getattr(sys, "frozen", False) and os.path.exists(SOURCE_QUESTIONS_PATH):
        return _read_questions_file(SOURCE_QUESTIONS_PATH)

    return _normalize_questions(copy.deepcopy(DEFAULT_REFLECTION_QUESTIONS))


def save_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = _normalize_questions(questions)
    runtime_path = _runtime_questions_path()
    os.makedirs(os.path.dirname(runtime_path), exist_ok=True)
    with open(runtime_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=True)
    return normalized


def reset_to_defaults() -> list[dict[str, Any]]:
    defaults = copy.deepcopy(DEFAULT_REFLECTION_QUESTIONS)
    return save_questions(defaults)
