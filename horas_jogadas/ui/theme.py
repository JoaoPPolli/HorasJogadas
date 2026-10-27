"""Tema escuro do aplicativo."""
import tkinter as tk
from tkinter import ttk

from ..constants import (
    COR_ACCENT, COR_BG, COR_BORDA, COR_BTN, COR_CARD, COR_PAUSA, COR_PERIGO, COR_TEXTO, COR_TEXTO_SUAVE,
)


def aplicar_tema_moderno(root: tk.Misc) -> None:
    """Aplica o tema escuro a uma janela (root ou Toplevel)."""
    root.configure(bg=COR_BG)
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("TFrame", background=COR_BG)
    style.configure("Card.TFrame", background=COR_CARD)

    style.configure("TLabel", background=COR_BG, foreground=COR_TEXTO, font=("Segoe UI", 10))
    style.configure("Small.TLabel", background=COR_BG, foreground=COR_TEXTO_SUAVE, font=("Segoe UI", 9))
    style.configure("Card.TLabel", background=COR_CARD, foreground=COR_TEXTO, font=("Segoe UI", 10))
    style.configure("CardSmall.TLabel", background=COR_CARD, foreground=COR_TEXTO_SUAVE, font=("Segoe UI", 8))
    style.configure("CardTitle.TLabel", background=COR_CARD, foreground=COR_TEXTO, font=("Segoe UI", 11, "bold"))
    style.configure("CardPausa.TLabel", background=COR_CARD, foreground=COR_PAUSA)
    style.configure("CardPausaSmall.TLabel", background=COR_CARD, foreground=COR_PAUSA, font=("Segoe UI", 8, "bold"))
    style.configure("CardValue.TLabel", background=COR_CARD, foreground=COR_TEXTO, font=("Segoe UI", 13, "bold"))

    style.configure("TEntry", fieldbackground="#222226", foreground=COR_TEXTO, padding=6)
    style.configure("TCombobox", fieldbackground="#222226", background=COR_BTN, foreground=COR_TEXTO,
                    arrowcolor=COR_TEXTO, padding=4)
    style.map("TCombobox", fieldbackground=[("readonly", "#222226")],
              foreground=[("readonly", COR_TEXTO)])

    style.configure("TRadiobutton", background=COR_BG, foreground=COR_TEXTO)
    style.map("TRadiobutton", background=[("active", COR_BG)])
    style.configure("Zerados.TCheckbutton", background=COR_BG, foreground=COR_TEXTO)
    style.map("Zerados.TCheckbutton", background=[("active", COR_BG)])

    style.configure("TButton", background=COR_BTN, foreground=COR_TEXTO, bordercolor=COR_BORDA,
                    focusthickness=0, padding=6)
    style.map("TButton", background=[("active", "#4a4a50")])
    style.configure("Accent.TButton", background=COR_ACCENT, foreground="white")
    style.map("Accent.TButton", background=[("active", "#7aa0ff")])
    style.configure("Danger.TButton", background=COR_PERIGO, foreground="white")
    style.map("Danger.TButton", background=[("active", "#ff6f6b")])

    style.configure("Vertical.TScrollbar", troughcolor=COR_BG, background=COR_CARD, arrowcolor=COR_TEXTO)
