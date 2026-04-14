# ui/SidebarFrame.py – Left navigation panel

from __future__ import annotations

from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from config import SIDEBAR_WIDTH, SUBJECT_COLOURS, GROQ_MODEL

# ── palette ───────────────────────────────────────────────────────────────────
_ACCENT      = ("#2563EB", "#3B82F6")
_CARD_BG     = ("gray91", "gray17")
_CARD_ACTIVE = ("gray84", "gray23")
_CARD_BORDER = ("gray79", "gray30")
_CARD_ACTIVE_BORDER = ("#2563EB", "#3B82F6")
_TEXT_MAIN   = ("gray10", "gray95")
_TEXT_SUB    = ("gray45", "gray58")


class SidebarFrame(ctk.CTkFrame):
    """Left navigation panel: logo, import button, book list, status footer."""

    def __init__(
        self,
        master,
        on_import_book: Callable[[str], None],
        on_select_book: Callable[[int], None],
        on_delete_book: Callable[[int], None],
        on_home:        Callable[[], None],
        **kwargs,
    ):
        super().__init__(
            master,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=("gray94", "gray13"),
            **kwargs,
        )
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        # rows: 0=logo 1=sep 2=home 3=import-card 4=section-hdr 5=scroll 6=sep 7=theme 8=status
        self.grid_rowconfigure(5, weight=1)

        self._on_import_book = on_import_book
        self._on_select_book = on_select_book
        self._on_delete_book = on_delete_book
        self._on_home        = on_home

        self._book_cards:   dict[int, ctk.CTkFrame] = {}
        self._active_id:    int | None = None
        self._no_books_lbl: ctk.CTkLabel | None = None

        self._build_logo()
        self._build_separator(row=1)
        self._build_home_row()
        self._build_import_card()
        self._build_books_section()
        self._build_separator(row=6)
        self._build_footer()

    # ── Logo ──────────────────────────────────────────────────────────────────

    def _build_logo(self) -> None:
        logo = ctk.CTkFrame(self, fg_color="transparent")
        logo.grid(row=0, column=0, padx=16, pady=(18, 8), sticky="ew")

        # Icon circle
        circle = ctk.CTkLabel(
            logo,
            text="E",
            width=36, height=36,
            corner_radius=10,
            fg_color=_ACCENT,
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        circle.grid(row=0, column=0, rowspan=2, padx=(0, 10), sticky="ns")

        ctk.CTkLabel(
            logo,
            text="EduHelper AI",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=_TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            logo,
            text="Primary Teacher Toolkit",
            font=ctk.CTkFont(size=10),
            text_color=_TEXT_SUB,
            anchor="w",
        ).grid(row=1, column=1, sticky="w")

    # ── Separator ─────────────────────────────────────────────────────────────

    def _build_separator(self, row: int) -> None:
        ctk.CTkFrame(
            self, height=1, fg_color=("gray82", "gray28")
        ).grid(row=row, column=0, padx=14, pady=2, sticky="ew")

    # ── Home ──────────────────────────────────────────────────────────────────

    def _build_home_row(self) -> None:
        ctk.CTkButton(
            self,
            text="  \u2302  Home",
            anchor="w",
            height=30,
            fg_color="transparent",
            hover_color=("gray86", "gray22"),
            text_color=_TEXT_MAIN,
            font=ctk.CTkFont(size=12),
            command=self._on_home,
        ).grid(row=2, column=0, padx=10, pady=(4, 2), sticky="ew")

    # ── Import card ───────────────────────────────────────────────────────────

    def _build_import_card(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=("gray88", "gray19"),
            corner_radius=10,
            border_width=1,
            border_color=("gray78", "gray32"),
        )
        card.grid(row=3, column=0, padx=10, pady=(6, 8), sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="ADD A TEXTBOOK",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=_TEXT_SUB,
            anchor="w",
        ).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self._import_btn = ctk.CTkButton(
            card,
            text="  +   Import New Book",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=44,
            corner_radius=8,
            fg_color=_ACCENT,
            hover_color=("#1D4ED8", "#2563EB"),
            text_color="white",
            command=self._import_clicked,
        )
        self._import_btn.grid(
            row=1, column=0, padx=10, pady=(0, 10), sticky="ew"
        )

    def _import_clicked(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF book(s) to import",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        for path in paths:
            if path:
                self._on_import_book(path)

    # ── Books section ─────────────────────────────────────────────────────────

    def _build_books_section(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=4, column=0, padx=14, pady=(2, 4), sticky="ew")
        hdr.columnconfigure(0, weight=1)

        self._section_lbl = ctk.CTkLabel(
            hdr,
            text="MY BOOKS",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=_TEXT_SUB,
            anchor="w",
        )
        self._section_lbl.grid(row=0, column=0, sticky="w")

        self._count_badge = ctk.CTkLabel(
            hdr,
            text="",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="white",
            fg_color=("gray60", "gray40"),
            corner_radius=8,
            width=20, height=18,
        )
        # shown only when count > 0

        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=("gray72", "gray38"),
            scrollbar_button_hover_color=("gray60", "gray50"),
        )
        self._scroll.grid(row=5, column=0, padx=6, pady=0, sticky="nsew")
        self._scroll.columnconfigure(0, weight=1)

        self._show_empty_placeholder()

    def _show_empty_placeholder(self) -> None:
        if self._no_books_lbl and self._no_books_lbl.winfo_exists():
            return
        self._no_books_lbl = ctk.CTkLabel(
            self._scroll,
            text="No books yet.\nImport a PDF to get started.",
            font=ctk.CTkFont(size=11),
            text_color=_TEXT_SUB,
            justify="center",
        )
        self._no_books_lbl.pack(pady=28)

    def _hide_empty_placeholder(self) -> None:
        if self._no_books_lbl and self._no_books_lbl.winfo_exists():
            self._no_books_lbl.pack_forget()
            self._no_books_lbl = None

    def _update_count_badge(self, n: int) -> None:
        if n == 0:
            self._count_badge.grid_remove()
        else:
            self._count_badge.configure(text=f" {n} ")
            self._count_badge.grid(row=0, column=1, sticky="e")

    # ── Book card ─────────────────────────────────────────────────────────────

    def add_book_button(
        self,
        book_id:       int,
        title:         str,
        subject:       str,
        chapter_count: int  = 0,
        added_at:      str  = "",
    ) -> None:
        """Append one book card to the scrollable list."""
        self._hide_empty_placeholder()

        colour   = SUBJECT_COLOURS.get(subject, SUBJECT_COLOURS["Other"])
        date_str = self._fmt_date(added_at)
        ch_str   = f"{chapter_count} chapter{'s' if chapter_count != 1 else ''}"
        trunc    = title if len(title) <= 26 else title[:24] + "…"

        card = ctk.CTkFrame(
            self._scroll,
            fg_color=_CARD_BG,
            corner_radius=8,
            border_width=1,
            border_color=_CARD_BORDER,
            cursor="hand2",
        )
        card.pack(fill="x", padx=4, pady=3)
        card.columnconfigure(1, weight=1)

        # Colour stripe
        stripe = ctk.CTkFrame(
            card, width=5, corner_radius=0, fg_color=colour
        )
        stripe.grid(row=0, column=0, rowspan=3, sticky="ns",
                    padx=(6, 0), pady=8)

        # Title
        title_lbl = ctk.CTkLabel(
            card,
            text=trunc,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_TEXT_MAIN,
            anchor="w",
        )
        title_lbl.grid(row=0, column=1, padx=(8, 4), pady=(8, 0), sticky="ew")

        # Chapter count + date
        meta_lbl = ctk.CTkLabel(
            card,
            text=f"{ch_str}  •  {date_str}",
            font=ctk.CTkFont(size=10),
            text_color=_TEXT_SUB,
            anchor="w",
        )
        meta_lbl.grid(row=1, column=1, padx=(8, 4), pady=(0, 0), sticky="ew")

        # Subject badge
        badge = ctk.CTkLabel(
            card,
            text=subject,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=colour,
            anchor="w",
        )
        badge.grid(row=2, column=1, padx=(8, 0), pady=(0, 8), sticky="w")

        # Delete button
        del_btn = ctk.CTkButton(
            card,
            text="✕",
            width=22, height=22,
            corner_radius=4,
            fg_color="transparent",
            hover_color=("gray80", "gray28"),
            text_color=_TEXT_SUB,
            font=ctk.CTkFont(size=10),
            command=lambda bid=book_id, t=title: self._confirm_delete(bid, t),
        )
        del_btn.grid(row=0, column=2, padx=(0, 6), pady=(6, 0), sticky="ne")

        # Click anywhere on card → select book
        for widget in (card, title_lbl, meta_lbl, badge, stripe):
            widget.bind(
                "<Button-1>",
                lambda e, bid=book_id: self._on_select_book(bid),
            )
        # Hover effects
        for widget in (card, title_lbl, meta_lbl, badge, stripe):
            widget.bind(
                "<Enter>",
                lambda e, c=card, bid=book_id: self._card_hover(c, bid, True),
            )
            widget.bind(
                "<Leave>",
                lambda e, c=card, bid=book_id: self._card_hover(c, bid, False),
            )

        self._book_cards[book_id] = card
        self._update_count_badge(len(self._book_cards))

    def _card_hover(self, card: ctk.CTkFrame, book_id: int, entering: bool) -> None:
        if book_id == self._active_id:
            return   # active card keeps its own style
        card.configure(fg_color=_CARD_ACTIVE if entering else _CARD_BG)

    def set_active_book(self, book_id: int | None) -> None:
        """Highlight the active book card."""
        # Deactivate previous
        if self._active_id and self._active_id in self._book_cards:
            prev = self._book_cards[self._active_id]
            prev.configure(
                fg_color=_CARD_BG,
                border_color=_CARD_BORDER,
            )
        self._active_id = book_id
        if book_id and book_id in self._book_cards:
            self._book_cards[book_id].configure(
                fg_color=_CARD_ACTIVE,
                border_color=_CARD_ACTIVE_BORDER,
            )

    def _confirm_delete(self, book_id: int, title: str) -> None:
        if messagebox.askyesno(
            "Remove Book",
            f'Remove "{title}" from your library?\n'
            "(The original PDF file will NOT be deleted.)",
        ):
            self._on_delete_book(book_id)

    def refresh_books(self, books: list[dict]) -> None:
        """Rebuild entire list from a fresh books query result."""
        for w in self._scroll.winfo_children():
            w.destroy()
        self._book_cards.clear()
        self._no_books_lbl = None
        self._active_id    = None

        if not books:
            self._show_empty_placeholder()
            self._update_count_badge(0)
            return

        for b in books:
            chapters = b.get("chapter_count", 0)
            self.add_book_button(
                book_id=b["id"],
                title=b["title"],
                subject=b["subject"],
                chapter_count=chapters,
                added_at=b.get("added_at", ""),
            )

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self) -> None:
        # Theme toggle row
        theme_row = ctk.CTkFrame(self, fg_color="transparent")
        theme_row.grid(row=7, column=0, padx=14, pady=(4, 6), sticky="ew")
        theme_row.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            theme_row,
            text="Dark mode",
            font=ctk.CTkFont(size=11),
            text_color=_TEXT_SUB,
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

        # Groq status pill
        pill = ctk.CTkFrame(
            self,
            fg_color=("gray88", "gray16"),
            corner_radius=8,
            border_width=1,
            border_color=("gray80", "gray28"),
        )
        pill.grid(row=8, column=0, padx=10, pady=(0, 14), sticky="ew")
        pill.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            pill,
            text="●",
            font=ctk.CTkFont(size=10),
            text_color="#22C55E",
        ).grid(row=0, column=0, padx=(10, 4), pady=(8, 2))

        ctk.CTkLabel(
            pill,
            text="Connected to Groq",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=_TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(8, 2))

        ctk.CTkLabel(
            pill,
            text=GROQ_MODEL,
            font=ctk.CTkFont(size=9),
            text_color=_TEXT_SUB,
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 8), sticky="w")

    def _toggle_theme(self) -> None:
        ctk.set_appearance_mode(
            "Dark" if self._theme_sw.get() else "Light"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_date(iso: str) -> str:
        try:
            dt = datetime.fromisoformat(iso)
            return dt.strftime("%b %d, %Y")
        except Exception:
            return ""
