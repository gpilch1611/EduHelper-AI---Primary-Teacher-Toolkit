# ui/ImportProgressDialog.py – Modal import dialog with live progress + log
#
# States
# ------
#  running  → indeterminate bar, scrolling log, Cancel button
#  done     → full green bar, summary, Close button, callback fired
#  error    → red bar, error detail, Close button (no callback)

from __future__ import annotations

import os
import threading
import tkinter as tk
from typing import Callable

import customtkinter as ctk


# ── colour tokens ─────────────────────────────────────────────────────────────
_GREEN  = "#22C55E"
_RED    = "#EF4444"
_YELLOW = "#F59E0B"
_BLUE   = "#3B82F6"
_GREY_T = ("gray40", "gray70")


class ImportProgressDialog(ctk.CTkToplevel):
    """
    Full-featured import progress modal.

    Parameters
    ----------
    master        : parent widget
    file_path     : absolute path to the PDF
    on_complete   : called with (book_id: int, analysis: dict) on success
    """

    def __init__(
        self,
        master,
        file_path:   str,
        on_complete: Callable[[int, dict], None],
    ):
        super().__init__(master)
        self.title("Importing Book")
        self.resizable(False, False)
        self.grab_set()          # modal – block main window
        self.protocol("WM_DELETE_WINDOW", self._on_close_btn)

        self._file_path   = file_path
        self._on_complete = on_complete
        self._cancel_evt  = threading.Event()
        self._finished    = False   # True when thread is done (success or error)
        self._book_id:  int  = -1
        self._analysis: dict = {}

        self._build_ui()
        self._center()
        self.after(120, self._start_import)   # slight delay for window to render

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.configure(width=520)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=("gray88", "gray16"), corner_radius=0)
        hdr.pack(fill="x")

        ctk.CTkLabel(
            hdr,
            text="Importing Book",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left", padx=18, pady=14)

        # ── File info ─────────────────────────────────────────────────────────
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=18, pady=(14, 0))

        fname = os.path.basename(self._file_path)
        fsize = self._human_size(self._file_path)

        ctk.CTkLabel(
            info_frame,
            text="File:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=_GREY_T,
            width=40,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            info_frame,
            text=fname,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        ctk.CTkLabel(
            info_frame,
            text="Size:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=_GREY_T,
            width=40,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkLabel(
            info_frame,
            text=fsize,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(2, 0))

        # ── Progress bar + percentage ─────────────────────────────────────────
        bar_row = ctk.CTkFrame(self, fg_color="transparent")
        bar_row.pack(fill="x", padx=18, pady=(14, 0))
        bar_row.columnconfigure(0, weight=1)

        self._bar = ctk.CTkProgressBar(bar_row, height=14, corner_radius=6)
        self._bar.set(0)
        self._bar.configure(mode="indeterminate",
                            progress_color=_BLUE,
                            fg_color=("gray82", "gray22"))
        self._bar.grid(row=0, column=0, sticky="ew")
        self._bar.start()

        self._pct_lbl = ctk.CTkLabel(
            bar_row,
            text="  0 %",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=46,
            anchor="e",
        )
        self._pct_lbl.grid(row=0, column=1, padx=(6, 0))

        # ── Current step label ────────────────────────────────────────────────
        self._step_lbl = ctk.CTkLabel(
            self,
            text="Starting…",
            font=ctk.CTkFont(size=11),
            text_color=_GREY_T,
            anchor="w",
        )
        self._step_lbl.pack(fill="x", padx=20, pady=(6, 0))

        # ── Log area ──────────────────────────────────────────────────────────
        log_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_frame.pack(fill="both", padx=18, pady=(8, 0), expand=True)

        ctk.CTkLabel(
            log_frame,
            text="Log",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray50", "gray55"),
            anchor="w",
        ).pack(fill="x")

        self._log = ctk.CTkTextbox(
            log_frame,
            height=170,
            font=ctk.CTkFont(family="Courier", size=11),
            state="disabled",
            wrap="word",
            fg_color=("gray92", "gray12"),
            border_width=1,
            border_color=("gray80", "gray28"),
        )
        self._log.pack(fill="both", expand=True)

        # ── Summary label (shown only on completion) ──────────────────────────
        self._summary_lbl = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_GREEN,
            wraplength=460,
            justify="left",
        )
        # not packed yet – shown on success/error

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=14)
        btn_row.columnconfigure(0, weight=1)

        self._cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=110,
            fg_color=("gray80", "gray25"),
            text_color=("gray20", "gray90"),
            hover_color=("gray70", "gray35"),
            command=self._request_cancel,
        )
        self._cancel_btn.grid(row=0, column=1, padx=(8, 0))

    # ── Thread management ─────────────────────────────────────────────────────

    def _start_import(self) -> None:
        t = threading.Thread(target=self._run_import, daemon=True)
        t.start()

    def _run_import(self) -> None:
        from pdf_importer import run_full_import
        try:
            book_id, analysis = run_full_import(
                self._file_path,
                on_progress=self._safe_progress,
                cancel_event=self._cancel_evt,
            )
            self._book_id  = book_id
            self._analysis = analysis
            self.after(0, self._on_success)
        except InterruptedError:
            self.after(0, lambda: self._on_error("Import cancelled."))
        except Exception as exc:
            self.after(0, lambda e=str(exc): self._on_error(e))

    # ── Thread-safe callbacks ─────────────────────────────────────────────────

    def _safe_progress(self, value: float, message: str) -> None:
        """Called from background thread – schedule on main thread."""
        self.after(0, lambda v=value, m=message: self._update_progress(v, m))

    def _update_progress(self, value: float, message: str) -> None:
        if not self.winfo_exists():
            return
        pct = int(value * 100)
        self._pct_lbl.configure(text=f"{pct:3d} %")
        self._step_lbl.configure(text=message)
        self._append_log(message)

    def _append_log(self, msg: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", f"  {msg}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── State transitions ─────────────────────────────────────────────────────

    def _on_success(self) -> None:
        if not self.winfo_exists():
            return
        self._finished = True
        title = self._analysis.get("title", "Book")
        chapters = len(self._analysis.get("chapters", []))

        self._bar.stop()
        self._bar.configure(mode="determinate", progress_color=_GREEN)
        self._bar.set(1.0)
        self._pct_lbl.configure(text="100 %")
        self._step_lbl.configure(text="Import successful!", text_color=_GREEN)

        self._append_log("─" * 46)
        self._append_log(f'Title:    {title}')
        self._append_log(f'Subject:  {self._analysis.get("subject","?")}')
        self._append_log(f'Year:     {self._analysis.get("year_group","?")}')
        self._append_log(f'Chapters: {chapters}')
        self._append_log("Import saved to database successfully.")

        self._summary_lbl.configure(
            text=f'"{title}" imported successfully with {chapters} chapter(s).',
            text_color=_GREEN,
        )
        self._summary_lbl.pack(fill="x", padx=20, pady=(0, 4))

        self._cancel_btn.configure(
            text="Close",
            fg_color=_GREEN,
            text_color="white",
            hover_color="#16A34A",
            command=self._close_after_success,
        )

        # Fire callback immediately so book appears in sidebar right away
        self._on_complete(self._book_id, self._analysis)

    def _on_error(self, error_msg: str) -> None:
        if not self.winfo_exists():
            return
        self._finished = True

        self._bar.stop()
        self._bar.configure(mode="determinate", progress_color=_RED)
        self._bar.set(1.0)
        self._pct_lbl.configure(text="ERR")
        self._step_lbl.configure(text="Import failed.", text_color=_RED)

        self._append_log("─" * 46)
        self._append_log(f"ERROR: {error_msg}")

        self._summary_lbl.configure(
            text=f"Error: {error_msg}",
            text_color=_RED,
        )
        self._summary_lbl.pack(fill="x", padx=20, pady=(0, 4))

        self._cancel_btn.configure(
            text="Close",
            fg_color=("gray80", "gray25"),
            text_color=("gray20", "gray90"),
            hover_color=("gray70", "gray35"),
            command=self.destroy,
        )

    def _request_cancel(self) -> None:
        if self._finished:
            self.destroy()
            return
        self._cancel_evt.set()
        self._cancel_btn.configure(state="disabled", text="Cancelling…")
        self._step_lbl.configure(text="Cancelling…", text_color=_YELLOW)
        self._append_log("Cancel requested – waiting for current operation…")

    def _close_after_success(self) -> None:
        self.destroy()

    def _on_close_btn(self) -> None:
        """Window X button."""
        if not self._finished:
            self._request_cancel()
        else:
            self.destroy()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _center(self) -> None:
        self.update_idletasks()
        w, h = 520, 480
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    @staticmethod
    def _human_size(path: str) -> str:
        try:
            b = os.path.getsize(path)
            for unit in ("B", "KB", "MB", "GB"):
                if b < 1024:
                    return f"{b:.1f} {unit}"
                b /= 1024
            return f"{b:.1f} TB"
        except OSError:
            return "unknown"
