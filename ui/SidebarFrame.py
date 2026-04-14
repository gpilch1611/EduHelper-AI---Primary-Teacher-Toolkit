# ui/SidebarFrame.py – Collapsible sidebar with book list and navigation

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from typing import Callable

from config import (
    APP_NAME, SIDEBAR_WIDTH, SUBJECT_COLOURS, GROQ_MODEL,
)


class SidebarFrame(ctk.CTkFrame):
    """Left navigation panel: logo, book list, import button, settings."""

    def __init__(
        self,
        master,
        on_import_book: Callable[[str], None],
        on_select_book: Callable[[int], None],
        on_delete_book: Callable[[int], None],
        on_home:        Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, width=SIDEBAR_WIDTH, corner_radius=0, **kwargs)
        self.grid_rowconfigure(4, weight=1)
        self.grid_propagate(False)

        self._on_import_book = on_import_book
        self._on_select_book = on_select_book
        self._on_delete_book = on_delete_book
        self._on_home        = on_home
        self._book_buttons: dict[int, ctk.CTkButton] = {}

        self._build_header()
        self._build_import_btn()
        self._build_book_list()
        self._build_footer()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(20, 8), sticky="ew")

        logo_lbl = ctk.CTkLabel(
            header,
            text="EduHelper AI",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        logo_lbl.grid(row=0, column=0, sticky="w")

        sub_lbl = ctk.CTkLabel(
            header,
            text="Primary Teacher Toolkit",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        )
        sub_lbl.grid(row=1, column=0, sticky="w")

        sep = ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30"))
        sep.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="ew")

        home_btn = ctk.CTkButton(
            self,
            text="  Home",
            image=None,
            anchor="w",
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray20", "gray90"),
            font=ctk.CTkFont(size=13),
            command=self._on_home,
        )
        home_btn.grid(row=2, column=0, padx=10, pady=(0, 4), sticky="ew")

    # ── Import button ─────────────────────────────────────────────────────────

    def _build_import_btn(self) -> None:
        btn = ctk.CTkButton(
            self,
            text="+ Import Book (PDF)",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            command=self._import_clicked,
        )
        btn.grid(row=3, column=0, padx=12, pady=(4, 10), sticky="ew")

    def _import_clicked(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF book(s)",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        for path in paths:
            if path:
                self._on_import_book(path)

    # ── Scrollable book list ──────────────────────────────────────────────────

    def _build_book_list(self) -> None:
        section_lbl = ctk.CTkLabel(
            self,
            text="MY BOOKS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray50", "gray55"),
            anchor="w",
        )
        section_lbl.grid(row=4, column=0, padx=18, pady=(0, 4), sticky="ew")

        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=("gray70", "gray40"),
        )
        self._scroll.grid(row=5, column=0, padx=6, pady=0, sticky="nsew")
        self.grid_rowconfigure(5, weight=1)

        self._no_books_lbl = ctk.CTkLabel(
            self._scroll,
            text="No books yet.\nImport a PDF above.",
            font=ctk.CTkFont(size=12),
            text_color=("gray55", "gray55"),
            justify="center",
        )
        self._no_books_lbl.pack(pady=20)

    def add_book_button(self, book_id: int, title: str, subject: str) -> None:
        """Add or refresh a book entry in the list."""
        self._no_books_lbl.pack_forget()

        colour = SUBJECT_COLOURS.get(subject, SUBJECT_COLOURS["Other"])

        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=2, pady=2)
        frame.columnconfigure(0, weight=1)

        btn = ctk.CTkButton(
            frame,
            text=f"  {title}",
            anchor="w",
            height=34,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray15", "gray90"),
            font=ctk.CTkFont(size=12),
            border_width=0,
            command=lambda bid=book_id: self._on_select_book(bid),
        )
        btn.grid(row=0, column=0, sticky="ew")

        tag = ctk.CTkLabel(
            frame,
            text=subject[:3].upper(),
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="white",
            fg_color=colour,
            corner_radius=4,
            width=28,
            height=18,
        )
        tag.grid(row=0, column=1, padx=(0, 4), pady=0)

        del_btn = ctk.CTkButton(
            frame,
            text="✕",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray50", "gray55"),
            font=ctk.CTkFont(size=10),
            command=lambda bid=book_id: self._confirm_delete(bid, title),
        )
        del_btn.grid(row=0, column=2, padx=(0, 2))

        self._book_buttons[book_id] = btn

    def _confirm_delete(self, book_id: int, title: str) -> None:
        if messagebox.askyesno(
            "Remove Book",
            f'Remove "{title}" from your library?\n'
            "(The original file will not be deleted.)",
        ):
            self._on_delete_book(book_id)

    def refresh_books(self, books: list[dict]) -> None:
        """Rebuild the entire book list from a list of book dicts."""
        for widget in self._scroll.winfo_children():
            widget.destroy()
        self._book_buttons.clear()

        if not books:
            self._no_books_lbl = ctk.CTkLabel(
                self._scroll,
                text="No books yet.\nImport a PDF above.",
                font=ctk.CTkFont(size=12),
                text_color=("gray55", "gray55"),
                justify="center",
            )
            self._no_books_lbl.pack(pady=20)
            return

        for book in books:
            self.add_book_button(book["id"], book["title"], book["subject"])

    # ── Footer: theme toggle + status ─────────────────────────────────────────

    def _build_footer(self) -> None:
        sep = ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30"))
        sep.grid(row=6, column=0, padx=16, pady=(8, 4), sticky="ew")

        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.grid(row=7, column=0, padx=12, pady=(0, 4), sticky="ew")
        theme_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            theme_frame,
            text="Dark mode",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        ).grid(row=0, column=0, sticky="w")

        self._theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="",
            width=44,
            command=self._toggle_theme,
        )
        self._theme_switch.grid(row=0, column=1, sticky="e")
        if ctk.get_appearance_mode() == "Dark":
            self._theme_switch.select()

        status_frame = ctk.CTkFrame(
            self,
            fg_color=("gray90", "gray15"),
            corner_radius=8,
        )
        status_frame.grid(row=8, column=0, padx=10, pady=(0, 14), sticky="ew")

        dot = ctk.CTkLabel(
            status_frame,
            text="●",
            font=ctk.CTkFont(size=10),
            text_color="#22C55E",
        )
        dot.grid(row=0, column=0, padx=(8, 2), pady=6)

        ctk.CTkLabel(
            status_frame,
            text=f"Connected to Groq",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray30", "gray80"),
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            status_frame,
            text=f"{GROQ_MODEL}",
            font=ctk.CTkFont(size=9),
            text_color=("gray50", "gray55"),
        ).grid(row=1, column=1, columnspan=2, padx=(0, 8), pady=(0, 6), sticky="w")

    def _toggle_theme(self) -> None:
        mode = "Dark" if self._theme_switch.get() else "Light"
        ctk.set_appearance_mode(mode)
