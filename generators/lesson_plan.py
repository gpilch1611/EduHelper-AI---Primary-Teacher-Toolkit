# generators/lesson_plan.py – AI-powered lesson plan generator
# Full implementation coming in Phase 2.

from __future__ import annotations

SYSTEM_PROMPT = """You are an experienced primary school teacher and curriculum designer.
Generate detailed, structured lesson plans that align with the Cambridge Primary curriculum.
Always include: Learning Objectives, Resources Needed, Starter Activity, Main Teaching,
Guided Practice, Independent Work, Plenary / Assessment, Differentiation notes (SEN / EAL / Gifted)."""


def build_prompt(topic: str, year_group: str, duration: str = "60 minutes",
                 chapter_context: str = "") -> str:
    ctx = f"\n\nBook/chapter context:\n{chapter_context}" if chapter_context else ""
    return (
        f"Create a complete lesson plan for the following:\n"
        f"  Topic:      {topic}\n"
        f"  Year Group: {year_group}\n"
        f"  Duration:   {duration}{ctx}\n\n"
        "Format the output with clear headings and bullet points."
    )
