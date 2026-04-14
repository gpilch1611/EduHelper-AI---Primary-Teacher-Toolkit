#!/usr/bin/env python3
# main.py – EduHelper AI · Primary Teacher Toolkit
# Entry point: builds the main window, wires up all components.

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from config import (
    APP_NAME, DEFAULT_APPEARANCE, DEFAULT_COLOR_THEME,
    WINDOW_DEFAULT, WINDOW_MIN_W, WINDOW_MIN_H, GROQ_MODEL,
)
import database as db
from groq_client import groq

from ui.SidebarFrame          import SidebarFrame
from ui.HomeFrame             import HomeFrame
from ui.ImportProgressDialog  import ImportProgressDialog
from ui.BookDashboardFrame    import BookDashboardFrame


# Appearance must be set before any CTk widgets are created
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

        self._sidebar = SidebarFrame(
            self,
            on_import_book=self._on_import_book,
            on_select_book=self._on_select_book,
            on_delete_book=self._on_delete_book,
            on_home=self._show_home,
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        self._main = ctk.CTkFrame(self, fg_color="transparent")
        self._main.grid(row=0, column=1, sticky="nsew")
        self._main.grid_rowconfigure(0, weight=1)
        self._main.grid_columnconfigure(0, weight=1)

        self._home_frame = HomeFrame(self._main)
        self._home_frame.grid(row=0, column=0, sticky="nsew")

        self._tabview = ctk.CTkTabview(self._main, anchor="nw")
        # gridded only after first book is opened

        self._build_statusbar()

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self) -> None:
        bar = ctk.CTkFrame(self, height=26, corner_radius=0,
                           fg_color=("gray85", "gray15"))
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.columnconfigure(1, weight=1)

        self._status_dot = ctk.CTkLabel(
            bar, text="●", font=ctk.CTkFont(size=10), text_color="gray50"
        )
        self._status_dot.grid(row=0, column=0, padx=(10, 2))

        self._status_lbl = ctk.CTkLabel(
            bar,
            text="Connecting to Groq…",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        )
        self._status_lbl.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            bar,
            text=GROQ_MODEL,
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray55"),
        ).grid(row=0, column=2, padx=12, sticky="e")

    def _set_status(self, text: str, colour: str = "") -> None:
        self._status_lbl.configure(text=text)
        if colour:
            self._status_dot.configure(text_color=colour)

    # ── Groq connectivity ping ────────────────────────────────────────────────

    def _ping_groq_async(self) -> None:
        def _worker():
            ok = groq.ping()
            if ok:
                self.after(0, lambda: self._set_status(
                    f"Connected to Groq  •  {GROQ_MODEL}", "#22C55E"))
            else:
                self.after(0, lambda: self._set_status(
                    "Could not reach Groq API – check your network connection",
                    "#EF4444"))

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
        """
        Called by SidebarFrame when the user picks a PDF.
        Opens the ImportProgressDialog which handles the full pipeline
        (PyMuPDF extraction → Groq analysis → SQLite save) with live progress.
        """
        if db.book_exists(file_path):
            messagebox.showinfo(
                "Already in library",
                f'"{os.path.basename(file_path)}" is already in your library.',
            )
            return

        # Open modal progress dialog – fires _on_book_imported when done
        ImportProgressDialog(
            self,
            file_path=file_path,
            on_complete=self._on_book_imported,
        )

    def _on_book_imported(self, book_id: int, analysis: dict) -> None:
        """
        Callback fired by ImportProgressDialog immediately on successful import.
        Updates sidebar and opens the book's dashboard tab.
        """
        book = db.get_book(book_id)
        if not book:
            return
        self._sidebar.add_book_button(book_id, book["title"], book["subject"])
        self._open_book_tab(book_id, book["title"])

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
        # Shorten long titles for the tab label
        label = title if len(title) <= 24 else title[:22] + "…"

        # Ensure uniqueness if two books share a truncated label
        existing = list(self._book_tabs.values())
        if label in existing:
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
        if book_id in self._book_tabs:
            label = self._book_tabs.pop(book_id)
            try:
                self._tabview.delete(label)
            except Exception:
                pass

        db.delete_book(book_id)
        self._sidebar.refresh_books(db.get_all_books())

        if not self._book_tabs:
            self._show_home()

    # ── Startup: reload persisted books into sidebar ──────────────────────────

    def _load_saved_books(self) -> None:
        self._sidebar.refresh_books(db.get_all_books())


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
