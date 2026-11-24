"""
gui.py
-------

Participant information dialog.

Uses Tkinter (included with Python) to collect participant
information before the experiment starts.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox


@dataclass(slots=True)
class ParticipantInfo:
    """
    Stores participant information for the experiment.
    """
    participant: str
    session: str
    block_order: str
    date: str

    @property
    def base_name(self) -> str:
        return f"{self.participant}{self.session}"
    
class ParticipantDialog:
    """
    Simple GUI dialog for participant information.
    """
    def __init__(self):

        self.result = None

        self.root = tk.Tk()
        self.root.title("Dynamic Stability Study")
        self.root.resizable(False, False)

        # ---------- Main Frame ----------

        frame = ttk.Frame(self.root, padding=20)
        frame.grid(row=0, column=0)

        # ---------- Participant ----------

        ttk.Label(frame, text="Participant ID").grid(
            row=0,
            column=0,
            sticky="w",
            pady=5
        )

        self.participant_var = tk.StringVar()

        participant_entry = ttk.Entry(
            frame,
            width=25,
            textvariable=self.participant_var
        )

        participant_entry.grid(row=0, column=1)
        participant_entry.focus()

        # ---------- Session ----------

        ttk.Label(frame, text="Session").grid(
            row=1,
            column=0,
            sticky="w",
            pady=5
        )

        self.session_var = tk.StringVar(value="001")

        ttk.Entry(
            frame,
            width=25,
            textvariable=self.session_var
        ).grid(row=1, column=1)

        # ---------- Block Order ----------

        ttk.Label(frame, text="Block Order").grid(
            row=2,
            column=0,
            sticky="w",
            pady=(15, 5)
        )

        self.block_var = tk.StringVar(value="normal")

        ttk.Radiobutton(
            frame,
            text="Normal",
            value="normal",
            variable=self.block_var
        ).grid(row=2, column=1, sticky="w")

        ttk.Radiobutton(
            frame,
            text="Reversed",
            value="reversed",
            variable=self.block_var
        ).grid(row=3, column=1, sticky="w")

        # ---------- Buttons ----------

        button_frame = ttk.Frame(frame)
        button_frame.grid(
            row=4,
            column=0,
            columnspan=2,
            pady=20
        )

        ttk.Button(
            button_frame,
            text="Start Experiment",
            command=self.start
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel
        ).pack(side="left", padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.cancel)

    def start(self):

        participant = self.participant_var.get().strip()

        if participant == "":
            messagebox.showwarning(
                "Missing Information",
                "Please enter a Participant ID."
            )
            return

        self.result = ParticipantInfo(
            participant=participant,
            session=self.session_var.get().strip(),
            block_order=self.block_var.get(),
            date=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )

        self.root.destroy()

    def cancel(self):

        self.result = None
        self.root.destroy()

    def show(self) -> ParticipantInfo | None:

        self.root.mainloop()
        return self.result


def get_participant_info() -> ParticipantInfo | None:
    """
    Launch participant dialog.

    Returns
    -------
    ParticipantInfo
        Filled participant information.

    None
        If the user cancels.
    """

    dialog = ParticipantDialog()
    return dialog.show()