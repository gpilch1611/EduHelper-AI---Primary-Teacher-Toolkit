# ui/BookDashboardFrame.py – Per-book dashboard tab (the main workspace)

from __future__ import annotations

import threading
import tkinter as tk
import customtkinter as ctk
from typing import Callable

from config import SUBJECT_COLOURS, YEAR_GROUPS, GROQ_MODEL
from database import (
    get_book, get_chapters, update_book_last_used,
    save_lesson_plan, save_worksheet,
)
from groq_client import groq
import generators.lesson_plan as lp_gen
import generators.worksheet   as ws_gen
import generators.quiz        as quiz_gen
import generators.explanation as exp_gen


# ── Helper: scrollable output area ───────────────────────────────────────────

class _OutputBox(ctk.CTkFrame):
    """A read-only text area with a Copy button."""

    def __init__(self, master, height: int = 320, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._text = ctk.CTkTextbox(
            self,
            height=height,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12),
            state="disabled",
        )
        self._text.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        copy_btn = ctk.CTkButton(
            self,
            text="Copy to clipboard",
            width=140,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=("gray80", "gray25"),
            text_color=("gray20", "gray90"),
            hover_color=("gray70", "gray35"),
            command=self._copy,
        )
        copy_btn.grid(row=1, column=0, sticky="e", padx=4, pady=(4, 0))

    def set_text(self, text: str) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._text.configure(state="disabled")

    def append(self, chunk: str) -> None:
        self._text.configure(state="normal")
        self._text.insert("end", chunk)
        self._text.see("end")
        self._text.configure(state="disabled")

    def clear(self) -> None:
        self.set_text("")

    def get_text(self) -> str:
        return self._text.get("1.0", "end-1c")

    def _copy(self) -> None:
        content = self.get_text()
        self.clipboard_clear()
        self.clipboard_append(content)


# ── Main dashboard frame ──────────────────────────────────────────────────────

class BookDashboardFrame(ctk.CTkFrame):
    """
    Displayed as a tab inside the main CTkTabview.
    Contains: book info banner + four tool panels (Lesson Plan, Worksheet,
    Quiz, Explain) in a nested CTkTabview.
    """

    def __init__(self, master, book_id: int, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._book_id = book_id
        self._book    = get_book(book_id)
        self._chapters = get_chapters(book_id)
        update_book_last_used(book_id)

        self._build_banner()
        self._build_tools()

    # ── Banner ────────────────────────────────────────────────────────────────

    def _build_banner(self) -> None:
        book  = self._book
        colour = SUBJECT_COLOURS.get(book["subject"], SUBJECT_COLOURS["Other"])

        banner = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color=("gray90", "gray18"),
            border_width=1,
            border_color=("gray78", "gray28"),
        )
        banner.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
        banner.columnconfigure(1, weight=1)

        # Coloured subject block
        badge = ctk.CTkFrame(banner, width=6, corner_radius=0, fg_color=colour)
        badge.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(12, 10),
                   pady=12)

        ctk.CTkLabel(
            banner,
            text=book["title"],
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(12, 0))

        info_txt = (
            f"{book['subject']}  •  {book['year_group']}  "
            f"•  {book['page_count']} pages"
        )
        ctk.CTkLabel(
            banner,
            text=info_txt,
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray60"),
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(0, 12))

        model_lbl = ctk.CTkLabel(
            banner,
            text=f"AI: {GROQ_MODEL}",
            font=ctk.CTkFont(size=10),
            text_color=("gray55", "gray50"),
        )
        model_lbl.grid(row=0, column=2, rowspan=2, padx=16, sticky="e")

    # ── Tool tabs ─────────────────────────────────────────────────────────────

    def _build_tools(self) -> None:
        tabs = ctk.CTkTabview(self, anchor="nw")
        tabs.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")

        for label in ("Lesson Plan", "Worksheet", "Quiz", "Explain"):
            tabs.add(label)

        self._build_lesson_plan_tab(tabs.tab("Lesson Plan"))
        self._build_worksheet_tab(tabs.tab("Worksheet"))
        self._build_quiz_tab(tabs.tab("Quiz"))
        self._build_explain_tab(tabs.tab("Explain"))

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _chapter_names(self) -> list[str]:
        if not self._chapters:
            return ["(no chapters)"]
        return [f"Ch {c['number']}: {c['title']}" for c in self._chapters]

    def _year_options(self) -> list[str]:
        return YEAR_GROUPS

    def _make_row(self, parent, label: str, widget_factory) -> ctk.CTkBaseClass:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=4)
        frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=label, width=110, anchor="e",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(0, 8))
        w = widget_factory(frame)
        w.grid(row=0, column=1, sticky="ew")
        return w

    def _make_generate_btn(self, parent, text: str, command) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            parent,
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            command=command,
        )
        btn.pack(fill="x", padx=2, pady=(8, 4))
        return btn

    def _set_busy(self, btn: ctk.CTkButton, output: _OutputBox,
                  busy: bool, label: str = "Generate") -> None:
        if busy:
            btn.configure(text="Generating…", state="disabled")
            output.clear()
        else:
            btn.configure(text=label, state="normal")

    # ── Lesson Plan tab ───────────────────────────────────────────────────────

    def _build_lesson_plan_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(5, weight=1)

        opts = ctk.CTkFrame(parent, fg_color="transparent")
        opts.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 0))
        opts.columnconfigure(1, weight=1)

        # Topic
        ctk.CTkLabel(opts, text="Topic", width=100, anchor="e").grid(
            row=0, column=0, padx=(0, 8), pady=4)
        self._lp_topic = ctk.CTkEntry(opts, placeholder_text="e.g. Fractions – addition")
        self._lp_topic.grid(row=0, column=1, sticky="ew", pady=4)

        # Year group
        ctk.CTkLabel(opts, text="Year Group", width=100, anchor="e").grid(
            row=1, column=0, padx=(0, 8), pady=4)
        self._lp_year = ctk.CTkOptionMenu(opts, values=YEAR_GROUPS,
                                          width=180)
        self._lp_year.set(self._book.get("year_group", YEAR_GROUPS[2]))
        self._lp_year.grid(row=1, column=1, sticky="w", pady=4)

        # Duration
        ctk.CTkLabel(opts, text="Duration", width=100, anchor="e").grid(
            row=2, column=0, padx=(0, 8), pady=4)
        self._lp_dur = ctk.CTkOptionMenu(
            opts,
            values=["30 minutes", "45 minutes", "60 minutes",
                    "90 minutes", "Double lesson"],
            width=180,
        )
        self._lp_dur.set("60 minutes")
        self._lp_dur.grid(row=2, column=1, sticky="w", pady=4)

        self._lp_save_var = ctk.BooleanVar(value=True)
        save_chk = ctk.CTkCheckBox(parent, text="Auto-save to library",
                                   variable=self._lp_save_var)
        save_chk.grid(row=1, column=0, sticky="w", padx=12, pady=(4, 0))

        self._lp_btn = ctk.CTkButton(
            parent,
            text="Generate Lesson Plan",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            command=self._generate_lesson_plan,
        )
        self._lp_btn.grid(row=2, column=0, padx=8, pady=(6, 4), sticky="ew")

        self._lp_status = ctk.CTkLabel(parent, text="",
                                       font=ctk.CTkFont(size=11),
                                       text_color=("gray45", "gray60"))
        self._lp_status.grid(row=3, column=0, sticky="w", padx=12)

        self._lp_output = _OutputBox(parent, height=300)
        self._lp_output.grid(row=4, column=0, padx=8, pady=(4, 8), sticky="nsew")
        parent.grid_rowconfigure(4, weight=1)

    def _generate_lesson_plan(self) -> None:
        topic = self._lp_topic.get().strip()
        if not topic:
            self._lp_status.configure(text="Please enter a topic.", text_color="red")
            return
        year = self._lp_year.get()
        dur  = self._lp_dur.get()

        self._lp_status.configure(text="Generating…", text_color=("gray45", "gray60"))
        self._lp_btn.configure(state="disabled", text="Generating…")
        self._lp_output.clear()

        prompt = lp_gen.build_prompt(topic, year, dur)

        def on_chunk(c):
            self._lp_output.append(c)

        def on_done():
            self._lp_btn.configure(state="normal", text="Generate Lesson Plan")
            self._lp_status.configure(text="Done.", text_color="#22C55E")
            if self._lp_save_var.get():
                save_lesson_plan(
                    title=f"{topic} – {year}",
                    content=self._lp_output.get_text(),
                    book_id=self._book_id,
                    year_group=year,
                    duration=dur,
                )

        def on_error(e):
            self._lp_btn.configure(state="normal", text="Generate Lesson Plan")
            self._lp_status.configure(text=f"Error: {e}", text_color="red")

        groq.stream_async(
            prompt,
            system=lp_gen.SYSTEM_PROMPT,
            on_chunk=on_chunk,
            on_done=on_done,
            on_error=on_error,
        )

    # ── Worksheet tab ─────────────────────────────────────────────────────────

    def _build_worksheet_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)

        opts = ctk.CTkFrame(parent, fg_color="transparent")
        opts.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 0))
        opts.columnconfigure(1, weight=1)

        ctk.CTkLabel(opts, text="Topic", width=110, anchor="e").grid(
            row=0, column=0, padx=(0, 8), pady=4)
        self._ws_topic = ctk.CTkEntry(opts, placeholder_text="e.g. Multiplication tables")
        self._ws_topic.grid(row=0, column=1, sticky="ew", pady=4)

        ctk.CTkLabel(opts, text="Year Group", width=110, anchor="e").grid(
            row=1, column=0, padx=(0, 8), pady=4)
        self._ws_year = ctk.CTkOptionMenu(opts, values=YEAR_GROUPS, width=180)
        self._ws_year.set(self._book.get("year_group", YEAR_GROUPS[2]))
        self._ws_year.grid(row=1, column=1, sticky="w", pady=4)

        ctk.CTkLabel(opts, text="Difficulty", width=110, anchor="e").grid(
            row=2, column=0, padx=(0, 8), pady=4)
        self._ws_diff = ctk.CTkOptionMenu(
            opts,
            values=["Foundation", "Core", "Extension", "Mixed"],
            width=180,
        )
        self._ws_diff.set("Mixed")
        self._ws_diff.grid(row=2, column=1, sticky="w", pady=4)

        ctk.CTkLabel(opts, text="Questions", width=110, anchor="e").grid(
            row=3, column=0, padx=(0, 8), pady=4)
        self._ws_num = ctk.CTkOptionMenu(
            opts, values=["5", "10", "15", "20"], width=180
        )
        self._ws_num.set("10")
        self._ws_num.grid(row=3, column=1, sticky="w", pady=4)

        self._ws_btn = ctk.CTkButton(
            parent,
            text="Generate Worksheet",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            command=self._generate_worksheet,
        )
        self._ws_btn.grid(row=1, column=0, padx=8, pady=(8, 4), sticky="ew")

        self._ws_status = ctk.CTkLabel(parent, text="",
                                       font=ctk.CTkFont(size=11),
                                       text_color=("gray45", "gray60"))
        self._ws_status.grid(row=2, column=0, sticky="w", padx=12)

        self._ws_output = _OutputBox(parent, height=300)
        self._ws_output.grid(row=3, column=0, padx=8, pady=(4, 8), sticky="nsew")
        parent.grid_rowconfigure(3, weight=1)

    def _generate_worksheet(self) -> None:
        topic = self._ws_topic.get().strip()
        if not topic:
            self._ws_status.configure(text="Please enter a topic.", text_color="red")
            return
        year = self._ws_year.get()
        diff = self._ws_diff.get()
        num  = int(self._ws_num.get())

        self._ws_status.configure(text="Generating…", text_color=("gray45","gray60"))
        self._ws_btn.configure(state="disabled", text="Generating…")
        self._ws_output.clear()

        prompt = ws_gen.build_prompt(topic, year, diff, num)

        def on_chunk(c):
            self._ws_output.append(c)

        def on_done():
            self._ws_btn.configure(state="normal", text="Generate Worksheet")
            self._ws_status.configure(text="Done.", text_color="#22C55E")
            save_worksheet(
                title=f"{topic} – {diff} – {year}",
                content=self._ws_output.get_text(),
                book_id=self._book_id,
                difficulty=diff,
            )

        def on_error(e):
            self._ws_btn.configure(state="normal", text="Generate Worksheet")
            self._ws_status.configure(text=f"Error: {e}", text_color="red")

        groq.stream_async(
            prompt,
            system=ws_gen.SYSTEM_PROMPT,
            on_chunk=on_chunk,
            on_done=on_done,
            on_error=on_error,
        )

    # ── Quiz tab ──────────────────────────────────────────────────────────────

    def _build_quiz_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)

        opts = ctk.CTkFrame(parent, fg_color="transparent")
        opts.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 0))
        opts.columnconfigure(1, weight=1)

        ctk.CTkLabel(opts, text="Topic", width=110, anchor="e").grid(
            row=0, column=0, padx=(0, 8), pady=4)
        self._qz_topic = ctk.CTkEntry(opts, placeholder_text="e.g. Place value")
        self._qz_topic.grid(row=0, column=1, sticky="ew", pady=4)

        ctk.CTkLabel(opts, text="Year Group", width=110, anchor="e").grid(
            row=1, column=0, padx=(0, 8), pady=4)
        self._qz_year = ctk.CTkOptionMenu(opts, values=YEAR_GROUPS, width=180)
        self._qz_year.set(self._book.get("year_group", YEAR_GROUPS[2]))
        self._qz_year.grid(row=1, column=1, sticky="w", pady=4)

        ctk.CTkLabel(opts, text="Questions", width=110, anchor="e").grid(
            row=2, column=0, padx=(0, 8), pady=4)
        self._qz_num = ctk.CTkOptionMenu(
            opts, values=["5", "10", "15", "20"], width=180
        )
        self._qz_num.set("10")
        self._qz_num.grid(row=2, column=1, sticky="w", pady=4)

        self._qz_btn = ctk.CTkButton(
            parent,
            text="Generate Quiz",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            command=self._generate_quiz,
        )
        self._qz_btn.grid(row=1, column=0, padx=8, pady=(8, 4), sticky="ew")

        self._qz_status = ctk.CTkLabel(parent, text="",
                                       font=ctk.CTkFont(size=11),
                                       text_color=("gray45", "gray60"))
        self._qz_status.grid(row=2, column=0, sticky="w", padx=12)

        self._qz_output = _OutputBox(parent, height=300)
        self._qz_output.grid(row=3, column=0, padx=8, pady=(4, 8), sticky="nsew")
        parent.grid_rowconfigure(3, weight=1)

    def _generate_quiz(self) -> None:
        topic = self._qz_topic.get().strip()
        if not topic:
            self._qz_status.configure(text="Please enter a topic.", text_color="red")
            return
        year = self._qz_year.get()
        num  = int(self._qz_num.get())

        self._qz_status.configure(text="Generating…", text_color=("gray45","gray60"))
        self._qz_btn.configure(state="disabled", text="Generating…")
        self._qz_output.clear()

        prompt = quiz_gen.build_prompt(topic, year, num)

        groq.stream_async(
            prompt,
            system=quiz_gen.SYSTEM_PROMPT,
            on_chunk=lambda c: self._qz_output.append(c),
            on_done=lambda: (
                self._qz_btn.configure(state="normal", text="Generate Quiz"),
                self._qz_status.configure(text="Done.", text_color="#22C55E"),
            ),
            on_error=lambda e: (
                self._qz_btn.configure(state="normal", text="Generate Quiz"),
                self._qz_status.configure(text=f"Error: {e}", text_color="red"),
            ),
        )

    # ── Explain tab ───────────────────────────────────────────────────────────

    def _build_explain_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)

        opts = ctk.CTkFrame(parent, fg_color="transparent")
        opts.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 0))
        opts.columnconfigure(1, weight=1)

        ctk.CTkLabel(opts, text="Concept", width=110, anchor="e").grid(
            row=0, column=0, padx=(0, 8), pady=4)
        self._ex_concept = ctk.CTkEntry(
            opts, placeholder_text="e.g. Long division"
        )
        self._ex_concept.grid(row=0, column=1, sticky="ew", pady=4)

        ctk.CTkLabel(opts, text="Year Group", width=110, anchor="e").grid(
            row=1, column=0, padx=(0, 8), pady=4)
        self._ex_year = ctk.CTkOptionMenu(opts, values=YEAR_GROUPS, width=180)
        self._ex_year.set(self._book.get("year_group", YEAR_GROUPS[2]))
        self._ex_year.grid(row=1, column=1, sticky="w", pady=4)

        self._ex_btn = ctk.CTkButton(
            parent,
            text="Explain Concept",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            command=self._explain_concept,
        )
        self._ex_btn.grid(row=1, column=0, padx=8, pady=(8, 4), sticky="ew")

        self._ex_status = ctk.CTkLabel(parent, text="",
                                       font=ctk.CTkFont(size=11),
                                       text_color=("gray45", "gray60"))
        self._ex_status.grid(row=2, column=0, sticky="w", padx=12)

        self._ex_output = _OutputBox(parent, height=300)
        self._ex_output.grid(row=3, column=0, padx=8, pady=(4, 8), sticky="nsew")
        parent.grid_rowconfigure(3, weight=1)

    def _explain_concept(self) -> None:
        concept = self._ex_concept.get().strip()
        if not concept:
            self._ex_status.configure(text="Please enter a concept.", text_color="red")
            return
        year = self._ex_year.get()

        self._ex_status.configure(text="Generating…", text_color=("gray45","gray60"))
        self._ex_btn.configure(state="disabled", text="Generating…")
        self._ex_output.clear()

        prompt = exp_gen.build_prompt(concept, year)

        groq.stream_async(
            prompt,
            system=exp_gen.SYSTEM_PROMPT,
            on_chunk=lambda c: self._ex_output.append(c),
            on_done=lambda: (
                self._ex_btn.configure(state="normal", text="Explain Concept"),
                self._ex_status.configure(text="Done.", text_color="#22C55E"),
            ),
            on_error=lambda e: (
                self._ex_btn.configure(state="normal", text="Explain Concept"),
                self._ex_status.configure(text=f"Error: {e}", text_color="red"),
            ),
        )
