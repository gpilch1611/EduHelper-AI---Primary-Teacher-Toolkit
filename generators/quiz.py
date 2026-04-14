# generators/quiz.py – AI-powered quiz / question bank generator
# Full implementation coming in Phase 2.

from __future__ import annotations

SYSTEM_PROMPT = """You are a primary school assessment specialist.
Generate quiz questions with multiple-choice options (A–D) and the correct answer clearly marked.
Include a mix of recall, understanding and application questions."""


def build_prompt(topic: str, year_group: str, num_questions: int = 10,
                 chapter_context: str = "") -> str:
    ctx = f"\n\nBook/chapter context:\n{chapter_context}" if chapter_context else ""
    return (
        f"Generate {num_questions} quiz questions for:\n"
        f"  Topic:      {topic}\n"
        f"  Year Group: {year_group}{ctx}\n\n"
        "Format: Q1. [question] A) ... B) ... C) ... D) ... Answer: [letter]"
    )
