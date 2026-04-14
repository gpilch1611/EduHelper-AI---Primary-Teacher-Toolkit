# ui/LessonPlanGenerator.py – Full lesson plan generator dialog
#
# Layout (1 140 × 720 px)
# ──────────────────────────────────────────────────────────────────────────
#  ┌─ HEADER ──────────────────────────────────────────────────────────────┐
#  │ 📋  Lesson Plan Generator   [book title]            [✕ close]         │
#  └───────────────────────────────────────────────────────────────────────┘
#  ┌─ SETTINGS (320 px) ──────────────┐  ┌─ OUTPUT (expands) ─────────────┐
#  │ Chapter / Unit                   │  │ [editable CTkTextbox]           │
#  │   [dropdown]                     │  │                                 │
#  │                                  │  │                                 │
#  │ Page range (optional)            │  │                                 │
#  │   From [____] To [____]          │  │                                 │
#  │                                  │  │                                 │
#  │ Lesson duration                  │  │                                 │
#  │   ○─────────●──── 60 min        │  │                                 │
#  │                                  │  │                                 │
#  │ Year group  [dropdown]           │  │                                 │
#  │                                  │  │                                 │
#  │ Focus topic (optional)           │  │                                 │
#  │   [_________________________________]│                                │
#  │                                  │  │                                 │
#  │ Additional notes                 │  │                                 │
#  │   [multiline textbox]            │  │                                 │
#  │                                  │  │                                 │
#  │ [  ⚡ Generate Lesson Plan  ]    │  │                                 │
#  └──────────────────────────────────┘  └─────────────────────────────────┘
#  ┌─ ACTION BAR ───────────────────────────────────────────────────────────┐
#  │ ● status text          [💾 Save PDF]  [📄 Export DOCX]  [📋 Copy]    │
#  └───────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import os
import threading
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from config         import YEAR_GROUPS, SUBJECT_COLOURS
from database       import save_lesson_plan, get_chapters
from groq_client    import groq
import generators.lesson_plan as lp_gen

# ── palette ───────────────────────────────────────────────────────────────────
_BLUE        = ("#2563EB", "#3B82F6")
_GREEN       = "#22C55E"
_RED         = "#EF4444"
_AMBER       = "#F59E0B"
_CARD_BG     = ("gray91", "gray17")
_CARD_BORDER = ("gray79", "gray30")
_TEXT_MAIN   = ("gray10", "gray95")
_TEXT_SUB    = ("gray45", "gray58")

_DIALOG_W, _DIALOG_H = 1150, 730
_PANEL_W = 310


class LessonPlanDialog(ctk.CTkToplevel):
    """
    Full-featured lesson plan generator window.

    Parameters
    ----------
    master   : parent widget
    book     : dict from database.get_book(book_id)
    chapters : list of dicts from database.get_chapters(book_id)
    """

    def __init__(self, master, book: dict, chapters: list[dict]):
        super().__init__(master)
        self.title("Lesson Plan Generator")
        self.resizable(True, True)
        self.minsize(900, 600)

        self._book      = book
        self._chapters  = chapters
        self._busy      = False
        self._content   = ""     # current text in the editor

        self._build_ui()
        self._center()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._build_action_bar()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        colour = SUBJECT_COLOURS.get(
            self._book["subject"], SUBJECT_COLOURS["Other"]
        )

        hdr = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=("gray89", "gray15"),
            border_width=0,
        )
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(1, weight=1)

        # Accent bar
        ctk.CTkFrame(hdr, width=5, corner_radius=0, fg_color=colour).grid(
            row=0, column=0, rowspan=2, sticky="ns", padx=(12, 10), pady=12
        )

        ctk.CTkLabel(
            hdr,
            text="Lesson Plan Generator",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=_TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(12, 0))

        ctk.CTkLabel(
            hdr,
            text=self._book["title"],
            font=ctk.CTkFont(size=11),
            text_color=_TEXT_SUB,
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(0, 12))

        ctk.CTkButton(
            hdr,
            text="✕  Close",
            width=90,
            height=28,
            fg_color=("gray80", "gray26"),
            text_color=_TEXT_MAIN,
            hover_color=("gray72", "gray34"),
            font=ctk.CTkFont(size=11),
            command=self.destroy,
        ).grid(row=0, column=2, rowspan=2, padx=14, sticky="e")

    # ── Body (settings + output) ──────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, minsize=_PANEL_W)
        body.grid_columnconfigure(1, weight=0)   # divider
        body.grid_columnconfigure(2, weight=1)

        self._build_settings_panel(body)

        # Divider
        ctk.CTkFrame(body, width=1, fg_color=("gray80", "gray28")).grid(
            row=0, column=1, sticky="ns", padx=0, pady=10
        )

        self._build_output_panel(body)

    # ── Settings panel ────────────────────────────────────────────────────────

    def _build_settings_panel(self, parent) -> None:
        panel = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=("gray70", "gray40"),
        )
        panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        panel.columnconfigure(0, weight=1)

        PAD = {"padx": 14, "pady": (0, 8)}

        # ── Chapter selector ──────────────────────────────────────────────────
        self._field_label(panel, "Chapter / Unit")
        ch_options = ["— Entire Book —"] + [
            f"Ch {c['number']}: {c['title']}" for c in self._chapters
        ]
        self._ch_var = ctk.StringVar(value=ch_options[0])
        ctk.CTkOptionMenu(
            panel,
            values=ch_options,
            variable=self._ch_var,
            command=self._on_chapter_changed,
            font=ctk.CTkFont(size=12),
        ).pack(fill="x", **PAD)

        # ── Chapter learning objectives (shown when chapter selected) ─────────
        self._obj_frame = ctk.CTkFrame(
            panel,
            fg_color=("gray88", "gray19"),
            corner_radius=8,
            border_width=1,
            border_color=("gray78", "gray30"),
        )
        self._obj_lbl = ctk.CTkLabel(
            self._obj_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=_TEXT_SUB,
            anchor="w",
            wraplength=_PANEL_W - 40,
            justify="left",
        )
        self._obj_lbl.pack(padx=10, pady=8, fill="x")

        # ── Page range ────────────────────────────────────────────────────────
        self._field_label(panel, "Page range  (optional)")
        pg_row = ctk.CTkFrame(panel, fg_color="transparent")
        pg_row.pack(fill="x", **PAD)
        pg_row.columnconfigure((0, 2), weight=1)

        self._pg_from = ctk.CTkEntry(
            pg_row, placeholder_text="From", width=80,
            font=ctk.CTkFont(size=12),
        )
        self._pg_from.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            pg_row, text="–", font=ctk.CTkFont(size=13),
            text_color=_TEXT_SUB,
        ).grid(row=0, column=1, padx=8)
        self._pg_to = ctk.CTkEntry(
            pg_row, placeholder_text="To", width=80,
            font=ctk.CTkFont(size=12),
        )
        self._pg_to.grid(row=0, column=2, sticky="ew")

        # ── Duration slider ───────────────────────────────────────────────────
        dur_hdr = ctk.CTkFrame(panel, fg_color="transparent")
        dur_hdr.pack(fill="x", padx=14, pady=(0, 4))
        dur_hdr.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dur_hdr,
            text="Lesson duration",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._dur_lbl = ctk.CTkLabel(
            dur_hdr,
            text="60 minutes",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_BLUE,
            anchor="e",
            width=80,
        )
        self._dur_lbl.grid(row=0, column=1, sticky="e")

        self._dur_slider = ctk.CTkSlider(
            panel,
            from_=30, to=180,
            number_of_steps=10,
            command=self._on_duration_changed,
        )
        self._dur_slider.set(60)
        self._dur_slider.pack(fill="x", padx=14, pady=(0, 10))

        # Duration marks row
        marks = ctk.CTkFrame(panel, fg_color="transparent")
        marks.pack(fill="x", padx=14, pady=(0, 8))
        for t in ("30", "60", "90", "120", "150", "180"):
            ctk.CTkLabel(
                marks,
                text=t,
                font=ctk.CTkFont(size=9),
                text_color=_TEXT_SUB,
            ).pack(side="left", expand=True)

        # ── Year group ────────────────────────────────────────────────────────
        self._field_label(panel, "Year group")
        self._year_var = ctk.StringVar(
            value=self._book.get("year_group", YEAR_GROUPS[2])
        )
        ctk.CTkOptionMenu(
            panel,
            values=YEAR_GROUPS,
            variable=self._year_var,
            font=ctk.CTkFont(size=12),
        ).pack(fill="x", **PAD)

        # ── Focus topic ───────────────────────────────────────────────────────
        self._field_label(panel, "Focus topic  (optional override)")
        self._focus_entry = ctk.CTkEntry(
            panel,
            placeholder_text="e.g. Column subtraction with borrowing",
            font=ctk.CTkFont(size=12),
        )
        self._focus_entry.pack(fill="x", **PAD)

        # ── Additional notes ──────────────────────────────────────────────────
        self._field_label(panel, "Additional notes / requirements")
        self._notes_box = ctk.CTkTextbox(
            panel,
            height=72,
            font=ctk.CTkFont(size=11),
            border_width=1,
            border_color=_CARD_BORDER,
            fg_color=("gray92", "gray14"),
        )
        self._notes_box.pack(fill="x", **PAD)

        # Placeholder text
        self._notes_box.insert(
            "1.0",
            "e.g. Class has 3 EAL learners, include visual aids…",
        )
        self._notes_box.bind("<FocusIn>", self._notes_focus_in)

        # ── Generate button ───────────────────────────────────────────────────
        ctk.CTkFrame(
            panel, height=1, fg_color=("gray80", "gray28")
        ).pack(fill="x", padx=14, pady=(8, 10))

        self._gen_btn = ctk.CTkButton(
            panel,
            text="  ⚡  Generate Lesson Plan",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=46,
            corner_radius=8,
            fg_color=_BLUE,
            hover_color=("#1D4ED8", "#2563EB"),
            text_color="white",
            command=self._generate,
        )
        self._gen_btn.pack(fill="x", padx=14, pady=(0, 16))

    @staticmethod
    def _field_label(parent, text: str) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=_TEXT_MAIN,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 3))

    # ── Output panel ──────────────────────────────────────────────────────────

    def _build_output_panel(self, parent) -> None:
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Header row
        out_hdr = ctk.CTkFrame(panel, fg_color="transparent")
        out_hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        out_hdr.columnconfigure(0, weight=1)

        self._out_title = ctk.CTkLabel(
            out_hdr,
            text="LESSON PLAN",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=_TEXT_SUB,
            anchor="w",
        )
        self._out_title.grid(row=0, column=0, sticky="w")

        self._edit_hint = ctk.CTkLabel(
            out_hdr,
            text="✎  editable",
            font=ctk.CTkFont(size=9),
            text_color=_TEXT_SUB,
            anchor="e",
        )
        self._edit_hint.grid(row=0, column=1, sticky="e")

        # Editable textbox
        self._editor = ctk.CTkTextbox(
            panel,
            wrap="word",
            font=ctk.CTkFont(family="Courier New", size=12),
            fg_color=("gray92", "gray12"),
            border_width=1,
            border_color=_CARD_BORDER,
            corner_radius=8,
            state="normal",
        )
        self._editor.grid(
            row=1, column=0, sticky="nsew", padx=14, pady=(0, 8)
        )

        # Placeholder
        self._set_editor_placeholder()

    def _set_editor_placeholder(self) -> None:
        self._editor.configure(state="normal")
        self._editor.delete("1.0", "end")
        self._editor.insert(
            "1.0",
            "Your lesson plan will appear here.\n\n"
            "Configure the settings on the left and click\n"
            "\"⚡ Generate Lesson Plan\" to begin.\n\n"
            "After generation you can edit this text freely\n"
            "before saving or exporting.",
        )
        self._editor.configure(text_color=_TEXT_SUB)

    # ── Action bar ────────────────────────────────────────────────────────────

    def _build_action_bar(self) -> None:
        bar = ctk.CTkFrame(
            self,
            height=48,
            corner_radius=0,
            fg_color=("gray88", "gray15"),
        )
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.columnconfigure(1, weight=1)

        # Status indicator
        self._bar_dot = ctk.CTkLabel(
            bar, text="●", font=ctk.CTkFont(size=10),
            text_color=("gray60", "gray50"),
        )
        self._bar_dot.grid(row=0, column=0, padx=(14, 4), pady=12)

        self._bar_lbl = ctk.CTkLabel(
            bar,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=_TEXT_SUB,
            anchor="w",
        )
        self._bar_lbl.grid(row=0, column=1, sticky="w")

        # Export buttons
        btn_cfg = dict(height=32, corner_radius=6, font=ctk.CTkFont(size=11))
        btns = [
            ("💾  Save PDF",     "#16A34A", "#15803D", self._save_pdf),
            ("📄  Export DOCX",  "#7C3AED", "#6D28D9", self._export_docx),
            ("📋  Copy",         ("gray76", "gray28"), ("gray66", "gray36"),
             self._copy_to_clipboard),
        ]
        for col_offset, (text, fg, hover, cmd) in enumerate(btns, start=2):
            ctk.CTkButton(
                bar,
                text=text,
                fg_color=fg,
                hover_color=hover,
                text_color="white",
                command=cmd,
                **btn_cfg,
            ).grid(row=0, column=col_offset, padx=(0, 8), pady=8)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_duration_changed(self, raw_val: float) -> None:
        snapped = round(raw_val / 15) * 15
        snapped = max(30, min(180, snapped))
        self._dur_lbl.configure(text=f"{snapped} minutes")

    def _on_chapter_changed(self, choice: str) -> None:
        if choice == "— Entire Book —":
            self._obj_frame.pack_forget()
            return

        idx = [
            f"Ch {c['number']}: {c['title']}" for c in self._chapters
        ].index(choice)
        ch = self._chapters[idx]

        info_parts = []
        if ch.get("learning_objectives"):
            first_obj = ch["learning_objectives"].strip().split("\n")[0]
            info_parts.append(f"Obj: {first_obj}")
        if ch.get("key_vocabulary"):
            vocab = ch["key_vocabulary"][:60]
            info_parts.append(f"Vocab: {vocab}…")
        if ch.get("start_page") and ch.get("end_page"):
            info_parts.append(
                f"Pages {ch['start_page']}–{ch['end_page']}"
            )

        if info_parts:
            self._obj_lbl.configure(text="  •  ".join(info_parts))
            self._obj_frame.pack(fill="x", padx=14, pady=(0, 8))
        else:
            self._obj_frame.pack_forget()

    def _notes_focus_in(self, _) -> None:
        if self._notes_box.get("1.0", "end-1c").startswith(
            "e.g. Class has"
        ):
            self._notes_box.delete("1.0", "end")

    # ── Generation ────────────────────────────────────────────────────────────

    def _get_duration(self) -> int:
        raw = self._dur_slider.get()
        return max(30, min(180, round(raw / 15) * 15))

    def _build_chapter_context(self) -> str:
        choice = self._ch_var.get()
        if choice == "— Entire Book —":
            return ""
        try:
            idx = [
                f"Ch {c['number']}: {c['title']}" for c in self._chapters
            ].index(choice)
            ch = self._chapters[idx]
        except (ValueError, IndexError):
            return ""

        parts = [f"Chapter {ch['number']}: {ch['title']}"]
        for field, label in [
            ("learning_objectives", "Learning objectives"),
            ("exercise_types",      "Exercise types"),
            ("key_vocabulary",      "Key vocabulary"),
            ("topics",              "Topics"),
        ]:
            val = (ch.get(field) or "").strip()
            if val:
                parts.append(f"{label}:\n{val}")
        return "\n\n".join(parts)

    def _generate(self) -> None:
        if self._busy:
            return

        duration    = self._get_duration()
        year        = self._year_var.get()
        focus       = self._focus_entry.get().strip()
        notes_raw   = self._notes_box.get("1.0", "end-1c").strip()
        notes       = "" if notes_raw.startswith("e.g.") else notes_raw
        ch_ctx      = self._build_chapter_context()

        pg_from = self._pg_from.get().strip()
        pg_to   = self._pg_to.get().strip()
        page_range = f"{pg_from}–{pg_to}" if (pg_from or pg_to) else ""

        prompt = lp_gen.build_prompt(
            book_title=self._book["title"],
            subject=self._book["subject"],
            year_group=year,
            duration=duration,
            chapter_ctx=ch_ctx,
            page_range=page_range,
            focus_topic=focus,
            notes=notes,
        )

        # Clear editor + lock
        self._busy = True
        self._gen_btn.configure(state="disabled", text="  ⚡  Generating…")
        self._editor.configure(state="normal", text_color=_TEXT_MAIN)
        self._editor.delete("1.0", "end")
        self._set_status("Generating lesson plan…", _AMBER)

        def on_chunk(chunk: str) -> None:
            self._editor.insert("end", chunk)
            self._editor.see("end")

        def on_done() -> None:
            self._content = self._editor.get("1.0", "end-1c")
            # Auto-save to DB
            try:
                ch_choice = self._ch_var.get()
                title_line = self._content.split("\n")[0]
                title = title_line.replace("LESSON PLAN:", "").strip() or (
                    f"{focus or ch_choice} – {year}"
                )
                save_lesson_plan(
                    title=title,
                    content=self._content,
                    book_id=self._book["id"],
                    year_group=year,
                    duration=f"{duration} minutes",
                )
            except Exception:
                pass

            self._busy = False
            self._gen_btn.configure(
                state="normal", text="  ⚡  Generate Lesson Plan"
            )
            self._set_status(
                "Lesson plan generated  •  auto-saved to library  •  "
                "edit freely before exporting",
                _GREEN,
            )

        def on_error(err: str) -> None:
            self._editor.insert("end", f"\n\n[Error: {err}]")
            self._busy = False
            self._gen_btn.configure(
                state="normal", text="  ⚡  Generate Lesson Plan"
            )
            self._set_status(f"Error: {err}", _RED)

        groq.stream_async(
            prompt,
            system=lp_gen.SYSTEM_PROMPT,
            on_chunk=on_chunk,
            on_done=on_done,
            on_error=on_error,
            max_tokens=3500,
            temperature=0.55,
        )

    # ── Export actions ────────────────────────────────────────────────────────

    def _get_content(self) -> str | None:
        content = self._editor.get("1.0", "end-1c").strip()
        if not content or content.startswith("Your lesson plan"):
            messagebox.showwarning(
                "Nothing to export",
                "Generate a lesson plan first.",
            )
            return None
        return content

    def _save_pdf(self) -> None:
        content = self._get_content()
        if not content:
            return
        path = filedialog.asksaveasfilename(
            title="Save Lesson Plan as PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile="lesson_plan.pdf",
        )
        if not path:
            return
        self._set_status("Saving PDF…", _AMBER)
        try:
            from exporters.pdf_export import export_pdf
            export_pdf(content, path)
            self._set_status(
                f"PDF saved: {os.path.basename(path)}", _GREEN
            )
        except ImportError as e:
            messagebox.showerror("Missing package", str(e))
            self._set_status("PDF export requires reportlab", _RED)
        except Exception as e:
            messagebox.showerror("Export error", str(e))
            self._set_status(f"PDF export failed: {e}", _RED)

    def _export_docx(self) -> None:
        content = self._get_content()
        if not content:
            return
        path = filedialog.asksaveasfilename(
            title="Export Lesson Plan as DOCX",
            defaultextension=".docx",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")],
            initialfile="lesson_plan.docx",
        )
        if not path:
            return
        self._set_status("Exporting DOCX…", _AMBER)
        try:
            from exporters.docx_export import export_docx
            export_docx(content, path)
            self._set_status(
                f"DOCX saved: {os.path.basename(path)}", _GREEN
            )
        except ImportError as e:
            messagebox.showerror("Missing package", str(e))
            self._set_status("DOCX export requires python-docx", _RED)
        except Exception as e:
            messagebox.showerror("Export error", str(e))
            self._set_status(f"DOCX export failed: {e}", _RED)

    def _copy_to_clipboard(self) -> None:
        content = self._get_content()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self._set_status("Copied to clipboard!", _GREEN)

    # ── Status bar helpers ────────────────────────────────────────────────────

    def _set_status(self, text: str, colour: str) -> None:
        self._bar_lbl.configure(text=text)
        self._bar_dot.configure(text_color=colour)

    # ── Window centering ──────────────────────────────────────────────────────

    def _center(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(_DIALOG_W, sw - 40)
        h  = min(_DIALOG_H, sh - 60)
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
