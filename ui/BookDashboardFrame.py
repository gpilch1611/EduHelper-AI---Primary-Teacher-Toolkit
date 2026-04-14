# ui/BookDashboardFrame.py – Per-book dashboard tab
#
# Layout
# ──────
#  ┌─ HEADER ─────────────────────────────────────────────────────────────────┐
#  │ Title • Subject badge • Year badge • page-count                          │
#  └──────────────────────────────────────────────────────────────────────────┘
#  ┌─ CHAPTER LIST (fixed 240 px) ──┐  ┌─ TOOLS AREA ────────────────────────┐
#  │ Scrollable chapter cards       │  │ 6 large action buttons (2 × 3 grid) │
#  │ Each: number badge, title,     │  │                                      │
#  │       page range               │  │ ── Output area ───────────────────── │
#  │                                │  │ AI-generated content (streamable)    │
#  └────────────────────────────────┘  └──────────────────────────────────────┘
#  ┌─ STATUS BAR ─────────────────────────────────────────────────────────────┐
#  │ ● Ready  /  Generating…                                                  │
#  └──────────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import customtkinter as ctk
from typing import Callable

from config import SUBJECT_COLOURS, YEAR_GROUPS, GROQ_MODEL
from database import (
    get_book, get_chapters, update_book_last_used,
    save_lesson_plan, save_worksheet,
)
from groq_client import groq
import generators.lesson_plan  as lp_gen
import generators.worksheet    as ws_gen
# LessonPlanDialog imported lazily inside _tool_clicked to avoid circular issues
import generators.quiz         as quiz_gen
import generators.explanation  as exp_gen

# ── palette ───────────────────────────────────────────────────────────────────
_CARD_BG     = ("gray91", "gray17")
_CARD_BORDER = ("gray79", "gray30")
_TEXT_MAIN   = ("gray10", "gray95")
_TEXT_SUB    = ("gray45", "gray58")
_GREEN       = "#22C55E"
_RED         = "#EF4444"

# ── tool button definitions ───────────────────────────────────────────────────
_TOOLS = [
    {
        "key":   "lesson_plan",
        "icon":  "📋",
        "title": "Lesson Plan",
        "desc":  "Full structured lesson\naligned to curriculum",
        "color": "#2563EB",
    },
    {
        "key":   "worksheet",
        "icon":  "📄",
        "title": "Worksheet",
        "desc":  "Printable exercises\nat every level",
        "color": "#16A34A",
    },
    {
        "key":   "similar",
        "icon":  "✏️",
        "title": "Similar Exercises",
        "desc":  "New practice tasks\nbased on this chapter",
        "color": "#7C3AED",
    },
    {
        "key":   "quiz",
        "icon":  "❓",
        "title": "Quiz / Test",
        "desc":  "MCQ question bank\nwith answer key",
        "color": "#DC2626",
    },
    {
        "key":   "flashcards",
        "icon":  "🃏",
        "title": "Flashcards",
        "desc":  "Key vocabulary &\nconcept cards",
        "color": "#D97706",
    },
    {
        "key":   "games",
        "icon":  "🎮",
        "title": "Games & Activities",
        "desc":  "Fun activities &\ngroup games",
        "color": "#DB2777",
    },
]


# ── Custom action button widget ───────────────────────────────────────────────

class _ActionButton(ctk.CTkFrame):
    """Large card-style button with icon, title, description and hover glow."""

    def __init__(
        self,
        master,
        icon:    str,
        title:   str,
        desc:    str,
        color:   str,
        command: Callable,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=12,
            fg_color=_CARD_BG,
            border_width=1,
            border_color=_CARD_BORDER,
            cursor="hand2",
            **kwargs,
        )
        self._color   = color
        self._command = command
        self._active  = True
        self.columnconfigure(0, weight=1)

        # Coloured top stripe
        top = ctk.CTkFrame(self, height=4, corner_radius=0, fg_color=color)
        top.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        # Icon
        ctk.CTkLabel(
            self,
            text=icon,
            font=ctk.CTkFont(size=28),
        ).grid(row=1, column=0, pady=(14, 0))

        # Title
        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=color,
        ).grid(row=2, column=0, padx=10, pady=(4, 0))

        # Description
        ctk.CTkLabel(
            self,
            text=desc,
            font=ctk.CTkFont(size=10),
            text_color=_TEXT_SUB,
            justify="center",
        ).grid(row=3, column=0, padx=10, pady=(2, 14))

        # Bind hover + click to all children
        self._bind_recursive(self)

    def _bind_recursive(self, widget) -> None:
        widget.bind("<Enter>",    self._on_enter)
        widget.bind("<Leave>",    self._on_leave)
        widget.bind("<Button-1>", self._on_click)
        for child in widget.winfo_children():
            self._bind_recursive(child)

    def _on_enter(self, _) -> None:
        if self._active:
            self.configure(
                fg_color=("gray84", "gray22"),
                border_color=self._color,
            )

    def _on_leave(self, _) -> None:
        self.configure(
            fg_color=_CARD_BG,
            border_color=_CARD_BORDER,
        )

    def _on_click(self, _) -> None:
        if self._active:
            self._command()

    def set_enabled(self, enabled: bool) -> None:
        self._active = enabled
        self.configure(
            fg_color=_CARD_BG,
            border_color=_CARD_BORDER if enabled else ("gray82", "gray26"),
        )


# ── Chapter list entry ────────────────────────────────────────────────────────

class _ChapterRow(ctk.CTkFrame):
    """Single chapter card in the left panel."""

    def __init__(
        self,
        master,
        number:     int,
        title:      str,
        start_page: int | None,
        end_page:   int | None,
        color:      str,
        on_select:  Callable[[int], None],
        chapter_id: int,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=8,
            fg_color=_CARD_BG,
            border_width=1,
            border_color=_CARD_BORDER,
            cursor="hand2",
            **kwargs,
        )
        self._chapter_id = chapter_id
        self._on_select  = on_select
        self._selected   = False
        self._color      = color
        self.columnconfigure(1, weight=1)

        # Number badge
        badge = ctk.CTkLabel(
            self,
            text=str(number),
            width=26, height=26,
            corner_radius=6,
            fg_color=color,
            text_color="white",
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        badge.grid(row=0, column=0, rowspan=2, padx=(8, 6), pady=8, sticky="n")

        # Title
        short = title if len(title) <= 28 else title[:26] + "…"
        title_lbl = ctk.CTkLabel(
            self,
            text=short,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=_TEXT_MAIN,
            anchor="w",
        )
        title_lbl.grid(row=0, column=1, sticky="ew", pady=(8, 0))

        # Page range
        if start_page and end_page:
            pages_str = f"pp. {start_page}–{end_page}"
        elif start_page:
            pages_str = f"p. {start_page}+"
        else:
            pages_str = ""

        pages_lbl = ctk.CTkLabel(
            self,
            text=pages_str,
            font=ctk.CTkFont(size=10),
            text_color=_TEXT_SUB,
            anchor="w",
        )
        pages_lbl.grid(row=1, column=1, sticky="ew", pady=(0, 8))

        for w in (self, badge, title_lbl, pages_lbl):
            w.bind("<Button-1>", lambda e: self._on_select(self._chapter_id))
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

    def _hover(self, entering: bool) -> None:
        if not self._selected:
            self.configure(
                fg_color=("gray85", "gray22") if entering else _CARD_BG
            )

    def select(self, active: bool) -> None:
        self._selected = active
        self.configure(
            fg_color=("gray84", "gray23") if active else _CARD_BG,
            border_color=self._color if active else _CARD_BORDER,
        )


# ── Output box ────────────────────────────────────────────────────────────────

class _OutputBox(ctk.CTkFrame):
    """Streaming-capable read-only text area with Copy button."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._box = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12),
            state="disabled",
            fg_color=("gray92", "gray13"),
            border_width=1,
            border_color=_CARD_BORDER,
            corner_radius=8,
        )
        self._box.grid(row=0, column=0, sticky="nsew")

        copy_btn = ctk.CTkButton(
            self,
            text="Copy",
            width=70, height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("gray82", "gray26"),
            text_color=_TEXT_MAIN,
            hover_color=("gray74", "gray34"),
            command=self._copy,
        )
        copy_btn.grid(row=1, column=0, sticky="e", pady=(4, 0))

    def set(self, text: str) -> None:
        self._box.configure(state="normal")
        self._box.delete("1.0", "end")
        self._box.insert("1.0", text)
        self._box.configure(state="disabled")

    def append(self, chunk: str) -> None:
        self._box.configure(state="normal")
        self._box.insert("end", chunk)
        self._box.see("end")
        self._box.configure(state="disabled")

    def clear(self) -> None:
        self.set("")

    def get(self) -> str:
        return self._box.get("1.0", "end-1c")

    def _copy(self) -> None:
        text = self.get()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)


# ── Main dashboard ────────────────────────────────────────────────────────────

class BookDashboardFrame(ctk.CTkFrame):
    """Full-area dashboard for one imported book."""

    def __init__(self, master, book_id: int, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._book_id         = book_id
        self._book            = get_book(book_id)
        self._chapters        = get_chapters(book_id)
        self._selected_ch_id: int | None = None
        self._chapter_rows:   dict[int, _ChapterRow] = {}
        self._busy            = False

        update_book_last_used(book_id)

        self._build_header()
        self._build_body()
        self._build_status_bar()

    # ── Header banner ─────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        book   = self._book
        colour = SUBJECT_COLOURS.get(book["subject"], SUBJECT_COLOURS["Other"])

        banner = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=("gray90", "gray16"),
            border_width=0,
        )
        banner.grid(row=0, column=0, columnspan=2, sticky="ew",
                    padx=0, pady=0)
        banner.columnconfigure(1, weight=1)

        # Left accent bar
        ctk.CTkFrame(
            banner, width=6, corner_radius=0, fg_color=colour
        ).grid(row=0, column=0, rowspan=2, sticky="ns",
               padx=(14, 10), pady=14)

        # Title
        ctk.CTkLabel(
            banner,
            text=book["title"],
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=_TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(14, 0))

        # Meta row
        meta_row = ctk.CTkFrame(banner, fg_color="transparent")
        meta_row.grid(row=1, column=1, sticky="w", pady=(2, 14))

        for badge_text, bg in [
            (book["subject"],    colour),
            (book["year_group"], ("gray70", "gray35")),
        ]:
            if badge_text:
                ctk.CTkLabel(
                    meta_row,
                    text=f"  {badge_text}  ",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color="white",
                    fg_color=bg,
                    corner_radius=6,
                ).pack(side="left", padx=(0, 6))

        pg = book.get("page_count", 0)
        ch = len(self._chapters)
        ctk.CTkLabel(
            meta_row,
            text=f"{pg} pages  •  {ch} chapter{'s' if ch != 1 else ''}",
            font=ctk.CTkFont(size=11),
            text_color=_TEXT_SUB,
        ).pack(side="left", padx=(4, 0))

        # Right: model tag
        ctk.CTkLabel(
            banner,
            text=f"AI: {GROQ_MODEL}",
            font=ctk.CTkFont(size=10),
            text_color=_TEXT_SUB,
        ).grid(row=0, column=2, rowspan=2, padx=16, sticky="e")

    # ── Body (chapters + tools) ───────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, minsize=248)
        body.grid_columnconfigure(1, weight=0)
        body.grid_columnconfigure(2, weight=1)

        self._build_chapter_panel(body)
        self._build_divider(body, col=1)
        self._build_tools_panel(body)

    def _build_divider(self, parent, col: int) -> None:
        ctk.CTkFrame(
            parent,
            width=1,
            fg_color=("gray80", "gray28"),
        ).grid(row=0, column=col, sticky="ns", padx=0, pady=12)

    # ── Chapter list panel ────────────────────────────────────────────────────

    def _build_chapter_panel(self, parent) -> None:
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Section header
        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        hdr.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="CHAPTERS & UNITS",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=_TEXT_SUB,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        count_lbl = ctk.CTkLabel(
            hdr,
            text=str(len(self._chapters)),
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="white",
            fg_color=("gray60", "gray42"),
            corner_radius=8,
            width=22, height=18,
        )
        count_lbl.grid(row=0, column=1, sticky="e")

        # Scrollable list
        scroll = ctk.CTkScrollableFrame(
            panel,
            fg_color="transparent",
            scrollbar_button_color=("gray72", "gray38"),
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        scroll.columnconfigure(0, weight=1)

        colour = SUBJECT_COLOURS.get(
            self._book["subject"], SUBJECT_COLOURS["Other"]
        )

        if not self._chapters:
            ctk.CTkLabel(
                scroll,
                text="No chapters found.\nRe-import this book to\nextract chapter data.",
                font=ctk.CTkFont(size=11),
                text_color=_TEXT_SUB,
                justify="center",
            ).pack(pady=28)
            return

        for ch in self._chapters:
            row = _ChapterRow(
                scroll,
                number=ch["number"],
                title=ch["title"],
                start_page=ch.get("start_page"),
                end_page=ch.get("end_page"),
                color=colour,
                on_select=self._select_chapter,
                chapter_id=ch["id"],
            )
            row.pack(fill="x", padx=4, pady=3)
            self._chapter_rows[ch["id"]] = row

    def _select_chapter(self, chapter_id: int) -> None:
        # Deselect previous
        if self._selected_ch_id in self._chapter_rows:
            self._chapter_rows[self._selected_ch_id].select(False)
        self._selected_ch_id = chapter_id
        self._chapter_rows[chapter_id].select(True)

        # Update status
        ch = next((c for c in self._chapters if c["id"] == chapter_id), None)
        if ch:
            self._set_status(f"Selected: {ch['title']}", "")

    # ── Tools panel ───────────────────────────────────────────────────────────

    def _build_tools_panel(self, parent) -> None:
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure((0, 1), weight=1)

        # Section label
        ctk.CTkLabel(
            panel,
            text="AI TOOLS",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=_TEXT_SUB,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w",
               padx=14, pady=(12, 6))

        # 6 buttons – 2 columns × 3 rows
        self._tool_btns: dict[str, _ActionButton] = {}
        for i, tool in enumerate(_TOOLS):
            btn = _ActionButton(
                panel,
                icon=tool["icon"],
                title=tool["title"],
                desc=tool["desc"],
                color=tool["color"],
                command=lambda t=tool: self._tool_clicked(t),
            )
            btn.grid(
                row=1 + i // 2,
                column=i % 2,
                padx=(12 if i % 2 == 0 else 6, 6 if i % 2 == 0 else 12),
                pady=4,
                sticky="nsew",
            )
            panel.grid_rowconfigure(1 + i // 2, minsize=110)
            self._tool_btns[tool["key"]] = btn

        # Output section
        out_hdr = ctk.CTkFrame(panel, fg_color="transparent")
        out_hdr.grid(row=4, column=0, columnspan=2, sticky="ew",
                     padx=14, pady=(10, 4))
        out_hdr.columnconfigure(0, weight=1)

        self._output_title_lbl = ctk.CTkLabel(
            out_hdr,
            text="OUTPUT",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=_TEXT_SUB,
            anchor="w",
        )
        self._output_title_lbl.grid(row=0, column=0, sticky="w")

        self._output_box = _OutputBox(panel)
        self._output_box.grid(
            row=5, column=0, columnspan=2,
            padx=12, pady=(0, 12),
            sticky="nsew",
        )
        panel.grid_rowconfigure(5, weight=1)

        # Placeholder text
        self._output_box.set(
            "Select a chapter on the left, then choose an AI tool above.\n\n"
            "The generated content will appear here and can be copied\n"
            "to your clipboard or saved automatically."
        )

    # ── Tool dispatcher ───────────────────────────────────────────────────────

    def _tool_clicked(self, tool: dict) -> None:
        if self._busy:
            return

        key = tool["key"]

        # ── Lesson Plan → dedicated dialog ────────────────────────────────────
        if key == "lesson_plan":
            from ui.LessonPlanGenerator import LessonPlanDialog
            LessonPlanDialog(
                self.winfo_toplevel(),
                book=self._book,
                chapters=self._chapters,
            )
            return

        # Build chapter context string for the other tools
        ch_context = ""
        if self._selected_ch_id:
            ch = next(
                (c for c in self._chapters if c["id"] == self._selected_ch_id),
                None,
            )
            if ch:
                parts = [f"Chapter {ch['number']}: {ch['title']}"]
                if ch.get("learning_objectives"):
                    parts.append("Objectives:\n" + ch["learning_objectives"])
                if ch.get("key_vocabulary"):
                    parts.append("Key vocabulary: " + ch["key_vocabulary"])
                if ch.get("topics"):
                    parts.append("Topics: " + ch["topics"])
                ch_context = "\n".join(parts)

        year = self._book.get("year_group", "Year 3")

        if self._selected_ch_id:
            ch = next(
                (c for c in self._chapters if c["id"] == self._selected_ch_id),
                None,
            )
            topic = ch["title"] if ch else self._book["title"]
        else:
            topic = self._book["title"]

        # Map key → (prompt_builder, system, save_fn | None, display_label)
        dispatch = {
            "worksheet": (
                lambda: ws_gen.build_prompt(topic, year, "Mixed", 10, ch_context),
                ws_gen.SYSTEM_PROMPT,
                lambda content: save_worksheet(
                    title=f"{topic} – Mixed – {year}",
                    content=content,
                    book_id=self._book_id,
                ),
                "Worksheet",
            ),
            "similar": (
                lambda: (
                    f"Create 12 new practice exercises similar to the exercises in:\n"
                    f"  Book:    {self._book['title']}\n"
                    f"  Topic:   {topic}\n"
                    f"  Year:    {year}\n"
                    + (f"  Context: {ch_context}\n" if ch_context else "")
                    + "\nVary difficulty across Foundation, Core and Extension levels."
                ),
                ws_gen.SYSTEM_PROMPT,
                None,
                "Similar Exercises",
            ),
            "quiz": (
                lambda: quiz_gen.build_prompt(topic, year, 10, ch_context),
                quiz_gen.SYSTEM_PROMPT,
                None,
                "Quiz / Test",
            ),
            "flashcards": (
                lambda: (
                    f"Create 15 flashcards for:\n"
                    f"  Topic: {topic}  |  Year: {year}\n"
                    + (f"  Context: {ch_context}\n" if ch_context else "")
                    + "\nFormat each card as:\n"
                    "FRONT: [term or question]\n"
                    "BACK:  [definition or answer]\n"
                    "---"
                ),
                "You are a primary school teacher creating concise, age-appropriate flashcards.",
                None,
                "Flashcards",
            ),
            "games": (
                lambda: (
                    f"Design 3 classroom games or activities for:\n"
                    f"  Topic: {topic}  |  Year: {year}\n"
                    + (f"  Context: {ch_context}\n" if ch_context else "")
                    + "\nFor each game include: Name, Objective, Materials needed, "
                    "Instructions (step-by-step), Differentiation tips."
                ),
                "You are a creative primary school teacher specialising in engaging classroom activities.",
                None,
                "Games & Activities",
            ),
        }

        if key not in dispatch:
            return

        prompt_fn, system, save_fn, label = dispatch[key]
        prompt = prompt_fn()

        self._start_generation(label, prompt, system, save_fn)

    # ── Generation flow ───────────────────────────────────────────────────────

    def _start_generation(
        self,
        label:   str,
        prompt:  str,
        system:  str,
        save_fn,
    ) -> None:
        self._busy = True
        for btn in self._tool_btns.values():
            btn.set_enabled(False)

        self._output_box.clear()
        self._output_title_lbl.configure(
            text=f"OUTPUT  –  {label.upper()}"
        )
        self._set_status(f"Generating {label}…", "#F59E0B")

        def on_chunk(chunk: str) -> None:
            self._output_box.append(chunk)

        def on_done() -> None:
            content = self._output_box.get()
            if save_fn:
                try:
                    save_fn(content)
                except Exception:
                    pass
            self._busy = False
            for btn in self._tool_btns.values():
                btn.set_enabled(True)
            self._set_status(f"{label} generated  •  auto-saved", _GREEN)

        def on_error(err: str) -> None:
            self._output_box.append(f"\n\n[Error: {err}]")
            self._busy = False
            for btn in self._tool_btns.values():
                btn.set_enabled(True)
            self._set_status(f"Error: {err}", _RED)

        groq.stream_async(
            prompt,
            system=system,
            on_chunk=on_chunk,
            on_done=on_done,
            on_error=on_error,
            max_tokens=2048,
        )

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        bar = ctk.CTkFrame(
            self,
            height=28,
            corner_radius=0,
            fg_color=("gray88", "gray14"),
        )
        bar.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        bar.grid_propagate(False)
        bar.columnconfigure(1, weight=1)

        self._status_dot = ctk.CTkLabel(
            bar,
            text="●",
            font=ctk.CTkFont(size=9),
            text_color=_GREEN,
        )
        self._status_dot.grid(row=0, column=0, padx=(12, 4))

        self._status_lbl = ctk.CTkLabel(
            bar,
            text="Ready  —  select a chapter then choose an AI tool",
            font=ctk.CTkFont(size=11),
            text_color=_TEXT_SUB,
            anchor="w",
        )
        self._status_lbl.grid(row=0, column=1, sticky="w")

        # Right: chapter hint
        self._ch_hint = ctk.CTkLabel(
            bar,
            text="No chapter selected",
            font=ctk.CTkFont(size=10),
            text_color=_TEXT_SUB,
        )
        self._ch_hint.grid(row=0, column=2, padx=12, sticky="e")

    def _set_status(self, text: str, colour: str) -> None:
        self._status_lbl.configure(text=text)
        if colour:
            self._status_dot.configure(text_color=colour)
        # Update chapter hint
        if self._selected_ch_id:
            ch = next(
                (c for c in self._chapters if c["id"] == self._selected_ch_id),
                None,
            )
            hint = f"Chapter {ch['number']}  •  pp. {ch.get('start_page','?')}–{ch.get('end_page','?')}" if ch else ""
        else:
            hint = "No chapter selected"
        self._ch_hint.configure(text=hint)
