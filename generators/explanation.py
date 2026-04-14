# generators/explanation.py – AI concept explainer for teachers
# Full implementation coming in Phase 2.

from __future__ import annotations

SYSTEM_PROMPT = """You are a friendly, expert primary school teacher explaining concepts clearly.
Use simple language appropriate for the year group, relatable analogies,
and step-by-step breakdowns. Suggest visual aids or manipulatives where helpful."""


def build_prompt(concept: str, year_group: str,
                 chapter_context: str = "") -> str:
    ctx = f"\n\nBook/chapter context:\n{chapter_context}" if chapter_context else ""
    return (
        f"Explain the following concept in a way suitable for {year_group} pupils:\n"
        f"  Concept: {concept}{ctx}\n\n"
        "Include: plain-language explanation, a real-world example, "
        "and 2–3 questions to check understanding."
    )
