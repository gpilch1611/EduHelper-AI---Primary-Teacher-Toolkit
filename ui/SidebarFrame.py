# ui/SidebarFrame.py – Left navigation panel

from __future__ import annotations

from tkinter import filedialog, messagebox
import customtkinter as ctk
from typing import Callable

from config import SIDEBAR_WIDTH, SUBJECT_COLOURS, GROQ_MODEL


class SidebarFrame(ctk.CTkFrame):
    """Left navigation panel: logo, big import button, book list, footer."""

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
        self.grid_rowconfigure(5, weight=1)   # scroll list is row 5
        self.grid_propagate(False)

        self._on_import_book = on_import_book
        self._on_select_book = on_select_book
        self._on_delete_book = on_delete_book
        self._on_home        = on_home
        self._book_frames:   dict[int, ctk.CTkFrame]  = {}
        self._no_books_lbl:  ctk.CTkLabel | None       = None

        self._build_header()      # row 0 – logo + subtitle
        self._build_separator(1)  # row 1 – thin line
        self._build_home_btn()    # row 2 – Home nav
        self._build_import_btn()  # row 3 – BIG import button
        self._build_book_list()   # row 4 (label) + 5 (scroll)
        self._build_footer()      # rows 6-8

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=16, pady=(20, 6), sticky="ew")

        ctk.CTkLabel(
            hdr,
            text="EduHelper AI",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hdr,
            text="Primary Teacher Toolkit",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        ).grid(row=1, column=0, sticky="w")

    def _build_separator(self, row: int) -> None:
        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).grid(
            row=row, column=0, padx=16, pady=(0, 4), sticky="ew"
        )

    # ── Home button ───────────────────────────────────────────────────────────

    def _build_home_btn(self) -> None:
        ctk.CTkButton(
            self,
            text="  \u2302  Home",
            anchor="w",
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray20", "gray90"),
            font=ctk.CTkFont(size=13),
            height=32,
            command=self._on_home,
        ).grid(row=2, column=0, padx=10, pady=(0, 6), sticky="ew")

    # ── Import button (large, prominent) ─────────────────────────────────────

    def _build_import_btn(self) -> None:
        # Outer card gives a subtle coloured background
        card = ctk.CTkFrame(
            self,
            fg_color=("gray88", "gray18"),
            corner_radius=10,
            border_width=1,
            border_color=("gray76", "gray32"),
        )
        card.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Import a new book",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray50", "gray55"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self._import_btn = ctk.CTkButton(
            card,
            text="+  Import Book (PDF)",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=46,
            corner_radius=8,
            fg_color=("#2563EB", "#1D4ED8"),
            hover_color=("#1D4ED8", "#1E40AF"),
            text_color="white",
            command=self._import_clicked,
        )
        self._import_btn.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

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
        ctk.CTkLabel(
            self,
            text="MY BOOKS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray50", "gray55"),
            anchor="w",
        ).grid(row=4, column=0, padx=18, pady=(0, 2), sticky="ew")

        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=("gray70", "gray40"),
        )
        self._scroll.grid(row=5, column=0, padx=6, pady=0, sticky="nsew")

        self._show_empty_label()

    def _show_empty_label(self) -> None:
        if self._no_books_lbl and self._no_books_lbl.winfo_exists():
            return
        self._no_books_lbl = ctk.CTkLabel(
            self._scroll,
            text="No books yet.\nImport a PDF above.",
            font=ctk.CTkFont(size=11),
            text_color=("gray55", "gray55"),
            justify="center",
        )
        self._no_books_lbl.pack(pady=24)

    def _hide_empty_label(self) -> None:
        if self._no_books_lbl and self._no_books_lbl.winfo_exists():
            self._no_books_lbl.pack_forget()

    # ── Book entry ────────────────────────────────────────────────────────────

    def add_book_button(self, book_id: int, title: str, subject: str) -> None:
        """Append a new book row (called after successful import)."""
        self._hide_empty_label()

        colour = SUBJECT_COLOURS.get(subject, SUBJECT_COLOURS["Other"])

        row = ctk.CTkFrame(
            self._scroll,
            fg_color=("gray90", "gray18"),
            corner_radius=7,
            border_width=1,
            border_color=("gray80", "gray28"),
        )
        row.pack(fill="x", padx=4, pady=3)
        row.columnconfigure(0, weight=1)

        # Subject colour stripe
        stripe = ctk.CTkFrame(row, width=4, corner_radius=0, fg_color=colour)
        stripe.grid(row=0, column=0, rowspan=2, sticky="ns",
                    padx=(6, 0), pady=6)

        # Title button
        btn = ctk.CTkButton(
            row,
            text=f"  {title}",
            anchor="w",
            height=32,
            fg_color="transparent",
            hover_color=("gray82", "gray24"),
            text_color=("gray10", "gray92"),
            font=ctk.CTkFont(size=12),
            border_width=0,
            command=lambda bid=book_id: self._on_select_book(bid),
        )
        btn.grid(row=0, column=1, sticky="ew", pady=(4, 0))

        # Subject badge + delete on second sub-row
        meta_row = ctk.CTkFrame(row, fg_color="transparent")
        meta_row.grid(row=1, column=1, sticky="ew", padx=(2, 4), pady=(0, 4))
        meta_row.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            meta_row,
            text=subject,
            font=ctk.CTkFont(size=9),
            text_color=colour,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            meta_row,
            text="Remove",
            width=52,
            height=18,
            corner_radius=4,
            fg_color="transparent",
            hover_color=("gray80", "gray28"),
            text_color=("gray50", "gray55"),
            font=ctk.CTkFont(size=9),
            command=lambda bid=book_id, t=title: self._confirm_delete(bid, t),
        ).grid(row=0, column=1, sticky="e")

        self._book_frames[book_id] = row

    def _confirm_delete(self, book_id: int, title: str) -> None:
        if messagebox.askyesno(
            "Remove Book",
            f'Remove "{title}" from your library?\n'
            "(The original PDF file will NOT be deleted.)",
        ):
            self._on_delete_book(book_id)

    def refresh_books(self, books: list[dict]) -> None:
        """Rebuild the entire list from scratch."""
        for w in self._scroll.winfo_children():
            w.destroy()
        self._book_frames.clear()
        self._no_books_lbl = None

        if not books:
            self._show_empty_label()
            return

        for book in books:
            self.add_book_button(book["id"], book["title"], book["subject"])

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self) -> None:
        self._build_separator(6)

        theme_row = ctk.CTkFrame(self, fg_color="transparent")
        theme_row.grid(row=7, column=0, padx=12, pady=(0, 6), sticky="ew")
        theme_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            theme_row,
            text="Dark mode",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        ).grid(row=0, column=0, sticky="w")

        self._theme_sw = ctk.CTkSwitch(
            theme_row,
            text="",
            width=44,
            command=self._toggle_theme,
        )
        self._theme_sw.grid(row=0, column=1, sticky="e")
        if ctk.get_appearance_mode() == "Dark":
            self._theme_sw.select()

        # Status pill
        pill = ctk.CTkFrame(
            self,
            fg_color=("gray90", "gray15"),
            corner_radius=8,
        )
        pill.grid(row=8, column=0, padx=10, pady=(0, 14), sticky="ew")

        ctk.CTkLabel(pill, text="●",
                     font=ctk.CTkFont(size=10),
                     text_color="#22C55E").grid(
            row=0, column=0, padx=(8, 2), pady=6)

        ctk.CTkLabel(pill, text="Connected to Groq",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=("gray30", "gray80")).grid(
            row=0, column=1, sticky="w")

        ctk.CTkLabel(pill, text=GROQ_MODEL,
                     font=ctk.CTkFont(size=9),
                     text_color=("gray50", "gray55")).grid(
            row=1, column=1, columnspan=2, padx=(0, 8), pady=(0, 6), sticky="w")

    def _toggle_theme(self) -> None:
        ctk.set_appearance_mode(
            "Dark" if self._theme_sw.get() else "Light"
        )
