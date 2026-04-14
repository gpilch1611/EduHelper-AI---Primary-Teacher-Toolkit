#!/usr/bin/env python3
# main.py – EduHelper AI · Primary Teacher Toolkit
# Entry point: builds the main window, wires up all components.

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
import customtkinter as ctk

# ── Bootstrap ─────────────────────────────────────────────────────────────────
from config import (
    APP_NAME, DEFAULT_APPEARANCE, DEFAULT_COLOR_THEME,
    WINDOW_DEFAULT, WINDOW_MIN_W, WINDOW_MIN_H, GROQ_MODEL,
)
import database as db
from groq_client import groq

from ui.SidebarFrame      import SidebarFrame
from ui.HomeFrame         import HomeFrame
from ui.ImportBookDialog  import ImportBookDialog
from ui.BookDashboardFrame import BookDashboardFrame


# ── Appearance (must be set before any CTk widgets are created) ───────────────
ctk.set_appearance_mode(DEFAULT_APPEARANCE)
ctk.set_default_color_theme(DEFAULT_COLOR_THEME)


class App(ctk.CTk):
    """Root application window."""

    def __init__(self) -> None:
        super().__init__()

        self.title(APP_NAME)
        self.geometry(WINDOW_DEFAULT)
        self.minsize(WINDOW_MIN_W, WINDOW_MIN_H)

        db.initialise_db()

        self._book_tabs: dict[int, str] = {}   # book_id → tab label
        self._setup_layout()
        self._load_saved_books()
        self._ping_groq_async()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _setup_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar
        self._sidebar = SidebarFrame(
            self,
            on_import_book=self._on_import_book,
            on_select_book=self._on_select_book,
            on_delete_book=self._on_delete_book,
            on_home=self._show_home,
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        # Main content area
        self._main = ctk.CTkFrame(self, fg_color="transparent")
        self._main.grid(row=0, column=1, sticky="nsew")
        self._main.grid_rowconfigure(0, weight=1)
        self._main.grid_columnconfigure(0, weight=1)

        # Home frame (shown when no book is open)
        self._home_frame = HomeFrame(self._main)
        self._home_frame.grid(row=0, column=0, sticky="nsew")

        # Tab view (shown when at least one book is open)
        self._tabview = ctk.CTkTabview(self._main, anchor="nw")
        # Don't grid it yet – only shown after first book

        # Status bar
        self._build_statusbar()

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self) -> None:
        bar = ctk.CTkFrame(self, height=26, corner_radius=0,
                           fg_color=("gray85", "gray15"))
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.columnconfigure(1, weight=1)

        # Left: connection status
        self._status_dot = ctk.CTkLabel(
            bar, text="●", font=ctk.CTkFont(size=10),
            text_color="gray50",
        )
        self._status_dot.grid(row=0, column=0, padx=(10, 2))

        self._status_lbl = ctk.CTkLabel(
            bar,
            text=f"Connecting to Groq…",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        )
        self._status_lbl.grid(row=0, column=1, sticky="w")

        # Right: model badge
        ctk.CTkLabel(
            bar,
            text=f"{GROQ_MODEL}",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray55"),
        ).grid(row=0, column=2, padx=12, sticky="e")

    def _set_status(self, text: str, colour: str = "") -> None:
        self._status_lbl.configure(text=text)
        if colour:
            self._status_dot.configure(text_color=colour)

    # ── Groq connectivity ─────────────────────────────────────────────────────

    def _ping_groq_async(self) -> None:
        def _worker():
            ok = groq.ping()
            if ok:
                self.after(0, lambda: self._set_status(
                    f"Connected to Groq  •  {GROQ_MODEL}", "#22C55E"))
            else:
                self.after(0, lambda: self._set_status(
                    "Could not reach Groq API – check your connection", "#EF4444"))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Home / tab visibility ─────────────────────────────────────────────────

    def _show_home(self) -> None:
        self._tabview.grid_remove()
        self._home_frame.grid(row=0, column=0, sticky="nsew")

    def _show_tabs(self) -> None:
        self._home_frame.grid_remove()
        self._tabview.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

    # ── Import book ───────────────────────────────────────────────────────────

    def _on_import_book(self, file_path: str) -> None:
        # Duplicate check
        if db.book_exists(file_path):
            from tkinter import messagebox
            messagebox.showinfo(
                "Already imported",
                f'"{os.path.basename(file_path)}" is already in your library.',
            )
            return

        # Show metadata dialog
        dialog = ImportBookDialog(self, file_path)
        self.wait_window(dialog)

        if dialog.result is None:
            return   # user cancelled

        meta = dialog.result

        # Count PDF pages (best-effort; requires PyPDF2 / pypdf)
        page_count = 0
        try:
            import importlib
            for pkg in ("pypdf", "PyPDF2"):
                spec = importlib.util.find_spec(pkg)
                if spec:
                    mod = importlib.import_module(pkg)
                    reader = mod.PdfReader(file_path)
                    page_count = len(reader.pages)
                    break
        except Exception:
            pass

        book_id = db.add_book(
            title=meta["title"],
            subject=meta["subject"],
            year_group=meta["year_group"],
            file_path=meta["file_path"],
            page_count=page_count,
        )

        self._sidebar.add_book_button(book_id, meta["title"], meta["subject"])
        self._open_book_tab(book_id, meta["title"])

    # ── Book tab management ───────────────────────────────────────────────────

    def _on_select_book(self, book_id: int) -> None:
        if book_id in self._book_tabs:
            self._show_tabs()
            self._tabview.set(self._book_tabs[book_id])
        else:
            book = db.get_book(book_id)
            if book:
                self._open_book_tab(book_id, book["title"])

    def _open_book_tab(self, book_id: int, title: str) -> None:
        # Truncate long titles for the tab label
        label = title if len(title) <= 22 else title[:20] + "…"

        if label in [self._tabview.tab(t) for t in self._tabview._name_list
                     if self._tabview.tab(t)]:
            # same label already exists – make unique
            label = f"{label[:18]}…{book_id}"

        self._tabview.add(label)
        self._book_tabs[book_id] = label

        tab_frame = self._tabview.tab(label)
        tab_frame.grid_rowconfigure(0, weight=1)
        tab_frame.grid_columnconfigure(0, weight=1)

        dashboard = BookDashboardFrame(tab_frame, book_id=book_id)
        dashboard.grid(row=0, column=0, sticky="nsew")

        self._show_tabs()
        self._tabview.set(label)

    def _on_delete_book(self, book_id: int) -> None:
        # Remove tab if open
        if book_id in self._book_tabs:
            label = self._book_tabs.pop(book_id)
            try:
                self._tabview.delete(label)
            except Exception:
                pass

        db.delete_book(book_id)

        # Refresh sidebar
        books = db.get_all_books()
        self._sidebar.refresh_books(books)

        # Back to home if no tabs left
        if not self._book_tabs:
            self._show_home()

    # ── Load persisted books on startup ──────────────────────────────────────

    def _load_saved_books(self) -> None:
        books = db.get_all_books()
        self._sidebar.refresh_books(books)
        # Don't auto-open tabs – wait for user to click a book


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
