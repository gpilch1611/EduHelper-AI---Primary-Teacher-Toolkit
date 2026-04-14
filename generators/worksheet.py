# generators/worksheet.py – AI-powered worksheet generator
# Full implementation coming in Phase 2.

from __future__ import annotations

SYSTEM_PROMPT = """You are an expert primary school teacher creating high-quality worksheets.
Worksheets should be age-appropriate, clearly structured and include:
instructions, worked examples where relevant, questions at three levels
(Foundation / Core / Extension), and a self-assessment section."""


def build_prompt(topic: str, year_group: str, difficulty: str = "Mixed",
                 num_questions: int = 10, chapter_context: str = "") -> str:
    ctx = f"\n\nBook/chapter context:\n{chapter_context}" if chapter_context else ""
    return (
        f"Create a printable worksheet for the following:\n"
        f"  Topic:       {topic}\n"
        f"  Year Group:  {year_group}\n"
        f"  Difficulty:  {difficulty}\n"
        f"  Questions:   {num_questions}{ctx}\n\n"
        "Use clear formatting with numbered questions and answer lines."
    )
