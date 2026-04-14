# pdf_importer.py – Full PDF extraction + Groq AI analysis pipeline
#
# Pipeline:
#   1. PyMuPDF (fitz) – page-by-page text extraction
#   2. Groq llama-3.3-70b – structural analysis (JSON response)
#   3. SQLite – persist book, chapters, pages

from __future__ import annotations

import json
import os
import re
import threading
from typing import Callable

# ── constants ─────────────────────────────────────────────────────────────────

# First N pages fed to Groq (ToC + first chapters usually live here)
PAGES_FOR_ANALYSIS = 45

# Hard cap on characters sent per API call (~40 k chars ≈ ~10 k tokens)
MAX_ANALYSIS_CHARS = 42_000

# Progress milestones (0.0 – 1.0)
_P_EXTRACT_END  = 0.38
_P_PREP         = 0.42
_P_GROQ_DONE    = 0.76
_P_PARSE        = 0.80
_P_SAVE_START   = 0.82
_P_DONE         = 1.00


# ── Groq prompt ───────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are an expert primary school teacher for Grade 1–6 Math and English. "
    "Respond ONLY with valid JSON – no markdown fences, no prose outside the JSON."
)

_PROMPT_TMPL = """\
You are an expert primary school teacher for Grade 1-2 Math and English. \
Analyze this textbook. Extract: full title, all units/chapters with page numbers, \
learning objectives, types of exercises on each page, key vocabulary, and main topics.

Return a single JSON object with EXACTLY this structure (no extra keys):

{{
  "title": "<full book title>",
  "subject": "<Mathematics|English|Science|Computing|Art & Design|Other>",
  "year_group": "<Reception|Year 1|Year 2|Year 3|Year 4|Year 5|Year 6>",
  "chapters": [
    {{
      "number": <integer starting at 1>,
      "title": "<unit or chapter title>",
      "start_page": <integer>,
      "end_page": <integer>,
      "learning_objectives": ["<obj1>", "<obj2>"],
      "exercise_types": ["<type1>", "<type2>"],
      "key_vocabulary": ["<word1>", "<word2>"],
      "topics": ["<topic1>", "<topic2>"]
    }}
  ],
  "key_vocabulary": ["<global word list>"],
  "main_topics": ["<topic1>", "<topic2>"]
}}

Rules:
- List EVERY unit / chapter / lesson you can identify.
- Estimate start_page / end_page from context if not stated explicitly.
- Provide at least 3 learning_objectives per chapter.
- If subject is ambiguous, choose the closest match from the allowed values.

--- TEXTBOOK CONTENT (first {n_pages} pages of {total_pages} total) ---
{text}
--- END OF CONTENT ---
"""


# ── Step 1 – PDF extraction ───────────────────────────────────────────────────

def extract_pdf(
    file_path: str,
    on_progress: Callable[[float, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[list[dict], int]:
    """
    Extract text from every page with PyMuPDF.

    Returns
    -------
    pages : list of {"page_number": int, "raw_text": str}
    total : int   total page count
    """
    try:
        import fitz          # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is not installed.\n"
            "Run:  pip install pymupdf"
        )

    doc   = fitz.open(file_path)
    total = len(doc)
    pages: list[dict] = []

    _report(on_progress, 0.01, f"Opened PDF  –  {total} pages detected")

    for i, page in enumerate(doc):
        if cancel_event and cancel_event.is_set():
            doc.close()
            raise InterruptedError("Import cancelled by user.")

        text = page.get_text("text")
        pages.append({"page_number": i + 1, "raw_text": text})

        # Report every 15 pages so the UI doesn't flood
        if i % 15 == 0 or i == total - 1:
            frac = 0.01 + (i + 1) / total * (_P_EXTRACT_END - 0.01)
            _report(on_progress, frac,
                    f"Extracting text  –  page {i + 1} / {total}")

    doc.close()
    _report(on_progress, _P_EXTRACT_END,
            f"Extraction complete  –  {total} pages read")
    return pages, total


# ── Step 2 – AI analysis ──────────────────────────────────────────────────────

def _build_sample_text(pages: list[dict], total: int) -> tuple[str, int]:
    """
    Build the text snippet sent to Groq.

    Includes:
    - All pages up to PAGES_FOR_ANALYSIS (capped at MAX_ANALYSIS_CHARS)
    Returns (text_sample, n_pages_included).
    """
    sample = pages[:PAGES_FOR_ANALYSIS]
    parts: list[str] = []
    chars = 0

    for p in sample:
        raw = (p["raw_text"] or "").strip()
        if not raw:
            continue
        chunk = f"[Page {p['page_number']}]\n{raw}\n\n"
        if chars + len(chunk) > MAX_ANALYSIS_CHARS:
            parts.append(f"[... remaining pages truncated for brevity ...]\n")
            break
        parts.append(chunk)
        chars += len(chunk)

    return "".join(parts), len(sample)


def analyse_with_groq(
    pages: list[dict],
    total_pages: int,
    on_progress: Callable[[float, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> dict:
    """
    Send a page sample to Groq and return the parsed analysis dict.
    Raises ValueError if JSON cannot be recovered from the response.
    """
    from groq_client import groq

    _report(on_progress, _P_PREP, "Preparing text sample for AI analysis…")

    if cancel_event and cancel_event.is_set():
        raise InterruptedError("Import cancelled by user.")

    text_sample, n_pages = _build_sample_text(pages, total_pages)

    _report(on_progress, _P_PREP + 0.01,
            f"Sending {n_pages} pages ({len(text_sample):,} chars) to Groq…")

    prompt = _PROMPT_TMPL.format(
        n_pages=n_pages,
        total_pages=total_pages,
        text=text_sample,
    )

    _report(on_progress, _P_PREP + 0.02,
            "AI analysing book structure  –  this may take 20–40 s…")

    raw = groq.complete(
        prompt,
        system=_SYSTEM,
        max_tokens=3500,
        temperature=0.05,   # near-deterministic for JSON reliability
    )

    if cancel_event and cancel_event.is_set():
        raise InterruptedError("Import cancelled by user.")

    _report(on_progress, _P_GROQ_DONE, "AI response received  –  parsing JSON…")

    result = _parse_json(raw)

    _report(on_progress, _P_PARSE,
            f"Parsed: \"{result.get('title', '?')}\"  "
            f"–  {len(result.get('chapters', []))} chapters found")

    return result


def _parse_json(raw: str) -> dict:
    """Robustly parse Groq's response into a dict."""
    # Strip markdown fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find the outermost JSON object
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Groq returned a response that could not be parsed as JSON.\n"
        f"First 300 chars:\n{raw[:300]}"
    )


# ── Step 3 – Persist to SQLite ────────────────────────────────────────────────

def save_to_db(
    file_path:   str,
    pages:       list[dict],
    analysis:    dict,
    on_progress: Callable[[float, str], None] | None = None,
) -> int:
    """
    Write book + chapters + pages to the database.
    Returns the new book_id.
    """
    from database import add_book, add_chapter, save_pages

    title      = (analysis.get("title") or "").strip() or _title_from_path(file_path)
    subject    = analysis.get("subject", "Other")
    year_group = analysis.get("year_group", "")

    _report(on_progress, _P_SAVE_START, f"Saving book: \"{title}\"…")

    book_id = add_book(
        title=title,
        subject=subject,
        year_group=year_group,
        file_path=file_path,
        page_count=len(pages),
    )

    chapters = analysis.get("chapters", [])
    _report(on_progress, _P_SAVE_START + 0.04,
            f"Saving {len(chapters)} chapter(s)…")

    for ch in chapters:
        add_chapter(
            book_id=book_id,
            number=int(ch.get("number") or 0),
            title=str(ch.get("title") or "Chapter"),
            start_page=_int_or_none(ch.get("start_page")),
            end_page=_int_or_none(ch.get("end_page")),
            learning_objectives=_join(ch.get("learning_objectives")),
            exercise_types=_join(ch.get("exercise_types")),
            key_vocabulary=_join(ch.get("key_vocabulary")),
            topics=_join(ch.get("topics")),
        )

    _report(on_progress, _P_SAVE_START + 0.08,
            f"Saving {len(pages)} page records…")

    save_pages(book_id, pages)

    _report(on_progress, _P_DONE, "Import complete!")
    return book_id


# ── Public orchestrator ───────────────────────────────────────────────────────

def run_full_import(
    file_path:    str,
    on_progress:  Callable[[float, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[int, dict]:
    """
    Full pipeline: extract → analyse → save.

    Returns
    -------
    book_id  : int   the new SQLite book id
    analysis : dict  the parsed Groq response

    Raises
    ------
    FileExistsError    – PDF already in library
    ImportError        – PyMuPDF not installed
    InterruptedError   – user pressed Cancel
    ValueError         – JSON parse failure
    Exception          – any Groq / network error
    """
    from database import book_exists

    if book_exists(file_path):
        raise FileExistsError(
            f'"{os.path.basename(file_path)}" is already in your library.'
        )

    pages, total = extract_pdf(file_path, on_progress, cancel_event)
    analysis     = analyse_with_groq(pages, total, on_progress, cancel_event)
    book_id      = save_to_db(file_path, pages, analysis, on_progress)

    return book_id, analysis


# ── Internal helpers ──────────────────────────────────────────────────────────

def _report(cb, value: float, msg: str) -> None:
    if cb:
        cb(value, msg)


def _join(items) -> str:
    if not items:
        return ""
    if isinstance(items, list):
        return "\n".join(str(x) for x in items)
    return str(items)


def _int_or_none(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _title_from_path(file_path: str) -> str:
    base = os.path.splitext(os.path.basename(file_path))[0]
    return base.replace("_", " ").replace("-", " ").strip()
