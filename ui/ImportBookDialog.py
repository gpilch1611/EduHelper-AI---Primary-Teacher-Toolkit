# ui/ImportBookDialog.py – Modal dialog to fill in book metadata before saving

from __future__ import annotations

import os
import customtkinter as ctk
from config import SUBJECT_COLOURS, YEAR_GROUPS


class ImportBookDialog(ctk.CTkToplevel):
    """
    Shown after the user picks a PDF.  Lets them confirm/edit:
      - Title (pre-filled from filename)
      - Subject
      - Year group
    Returns via self.result: dict | None
    """

    def __init__(self, master, file_path: str):
        super().__init__(master)
        self.title("Import Book")
        self.resizable(False, False)
        self.grab_set()          # modal

        self.result: dict | None = None
        self._file_path = file_path

        default_title = os.path.splitext(os.path.basename(file_path))[0]
        default_title = default_title.replace("_", " ").replace("-", " ")

        self._build(default_title)
        self._center()

    def _build(self, default_title: str) -> None:
        pad = {"padx": 20, "pady": 6}

        ctk.CTkLabel(
            self,
            text="Book Details",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=20, pady=(20, 4))

        ctk.CTkLabel(
            self,
            text=f"File: {os.path.basename(self._file_path)}",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray60"),
        ).pack(padx=20, pady=(0, 12))

        # Title
        ctk.CTkLabel(self, text="Title", anchor="w").pack(fill="x", **pad)
        self._title_entry = ctk.CTkEntry(self, width=360, placeholder_text="Book title")
        self._title_entry.insert(0, default_title)
        self._title_entry.pack(fill="x", **pad)

        # Subject
        ctk.CTkLabel(self, text="Subject", anchor="w").pack(fill="x", **pad)
        subjects = list(SUBJECT_COLOURS.keys())
        self._subject_var = ctk.StringVar(value=subjects[0])
        self._subject_menu = ctk.CTkOptionMenu(
            self, values=subjects, variable=self._subject_var, width=360
        )
        self._subject_menu.pack(fill="x", **pad)

        # Year group
        ctk.CTkLabel(self, text="Year Group", anchor="w").pack(fill="x", **pad)
        self._year_var = ctk.StringVar(value=YEAR_GROUPS[2])
        self._year_menu = ctk.CTkOptionMenu(
            self, values=YEAR_GROUPS, variable=self._year_var, width=360
        )
        self._year_menu.pack(fill="x", **pad)

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(16, 20))
        btn_row.columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color=("gray80", "gray25"),
            text_color=("gray20", "gray90"),
            hover_color=("gray70", "gray35"),
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btn_row, text="Import",
            command=self._on_import,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _on_import(self) -> None:
        title = self._title_entry.get().strip()
        if not title:
            self._title_entry.configure(border_color="red")
            return
        self.result = {
            "title":      title,
            "subject":    self._subject_var.get(),
            "year_group": self._year_var.get(),
            "file_path":  self._file_path,
        }
        self.destroy()

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
