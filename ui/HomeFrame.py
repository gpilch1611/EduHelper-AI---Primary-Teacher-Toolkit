# ui/HomeFrame.py – Welcome / landing screen shown before any book is selected

from __future__ import annotations

import customtkinter as ctk
from config import APP_VERSION, GROQ_MODEL


class HomeFrame(ctk.CTkFrame):
    """Full-area welcome card shown when no book tab is active."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        card = ctk.CTkFrame(self, corner_radius=16, width=540)
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=540)

        # ── Banner ────────────────────────────────────────────────────────────
        banner = ctk.CTkFrame(card, corner_radius=12, height=90,
                               fg_color=("gray85", "gray18"))
        banner.pack(fill="x", padx=24, pady=(28, 0))
        banner.pack_propagate(False)

        ctk.CTkLabel(
            banner,
            text="EduHelper AI",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).place(relx=0.5, rely=0.38, anchor="center")
        ctk.CTkLabel(
            banner,
            text="Primary Teacher Toolkit",
            font=ctk.CTkFont(size=13),
            text_color=("gray45", "gray65"),
        ).place(relx=0.5, rely=0.72, anchor="center")

        # ── Tagline ───────────────────────────────────────────────────────────
        ctk.CTkLabel(
            card,
            text="AI-powered lesson plans, worksheets & quizzes\n"
                 "tailored to your Cambridge Primary books.",
            font=ctk.CTkFont(size=13),
            text_color=("gray35", "gray70"),
            justify="center",
        ).pack(pady=(16, 0))

        # ── Feature tiles ─────────────────────────────────────────────────────
        tiles_frame = ctk.CTkFrame(card, fg_color="transparent")
        tiles_frame.pack(padx=24, pady=16, fill="x")
        tiles_frame.columnconfigure((0, 1), weight=1)

        features = [
            ("Lesson Plans",  "Structured plans\naligned to curriculum", "#2563EB"),
            ("Worksheets",    "Printable exercises\nat every level",       "#16A34A"),
            ("Quizzes",       "Question banks\nfor any topic",            "#9333EA"),
            ("Explanations",  "Clear concept\nbreakdowns for pupils",     "#D97706"),
        ]
        for i, (title, desc, colour) in enumerate(features):
            tile = ctk.CTkFrame(
                tiles_frame,
                corner_radius=10,
                fg_color=("gray90", "gray20"),
                border_width=1,
                border_color=("gray80", "gray30"),
            )
            tile.grid(row=i // 2, column=i % 2, padx=6, pady=6, sticky="nsew")

            ctk.CTkLabel(
                tile,
                text=title,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=colour,
            ).pack(anchor="w", padx=12, pady=(12, 0))
            ctk.CTkLabel(
                tile,
                text=desc,
                font=ctk.CTkFont(size=11),
                text_color=("gray45", "gray60"),
                justify="left",
            ).pack(anchor="w", padx=12, pady=(2, 12))

        # ── Getting started hint ──────────────────────────────────────────────
        hint = ctk.CTkFrame(card, corner_radius=8,
                            fg_color=("gray90", "gray18"),
                            border_width=1, border_color=("gray80", "gray28"))
        hint.pack(fill="x", padx=24, pady=(0, 8))

        ctk.CTkLabel(
            hint,
            text="To get started, click  \"+  Import Book (PDF)\"  in the sidebar.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
        ).pack(pady=12)

        # ── Version / model badge ─────────────────────────────────────────────
        ctk.CTkLabel(
            card,
            text=f"v{APP_VERSION}  •  {GROQ_MODEL}",
            font=ctk.CTkFont(size=10),
            text_color=("gray60", "gray50"),
        ).pack(pady=(0, 20))
