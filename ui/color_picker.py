import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser

class ColorPickerWidget(ctk.CTkFrame):
    """
    Widget de selección de color para la app WiZ.
    """
    def __init__(self, master: ctk.CTkFrame, on_color_change: callable = None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.on_color_change = on_color_change
        self.selected_color = "#0087c3"
        self._build_ui()

    def _build_ui(self) -> None:
        self.label = ctk.CTkLabel(self, text="Color Picker", font=("Helvetica", 16))
        self.label.grid(row=0, column=0, columnspan=2, pady=10)

        self.color_preview = ctk.CTkLabel(self, text="", width=40, height=40, fg_color=self.selected_color)
        self.color_preview.grid(row=1, column=0, padx=10, pady=10)

        self.pick_btn = ctk.CTkButton(self, text="Elegir color...", command=self._choose_color)
        self.pick_btn.grid(row=1, column=1, padx=10, pady=10)

        self.hex_entry = ctk.CTkEntry(self, width=80)
        self.hex_entry.insert(0, self.selected_color)
        self.hex_entry.grid(row=2, column=0, padx=10, pady=10)
        self.hex_entry.bind("<Return>", self._on_hex_enter)

        self.done_btn = ctk.CTkButton(self, text="Aplicar", command=self._apply_color)
        self.done_btn.grid(row=2, column=1, padx=10, pady=10)

    def _choose_color(self) -> None:
        try:
            color = colorchooser.askcolor(title="Elige un color")[1]
            if color:
                self.selected_color = color
                self.color_preview.configure(fg_color=color)
                self.hex_entry.delete(0, tk.END)
                self.hex_entry.insert(0, color)
        except Exception as e:
            print(f"Error eligiendo color: {e}")

    def _on_hex_enter(self, event: tk.Event) -> None:
        try:
            color = self.hex_entry.get()
            if color:
                self.selected_color = color
                self.color_preview.configure(fg_color=color)
        except Exception as e:
            print(f"Error aplicando color hex: {e}")

    def _apply_color(self) -> None:
        color = self.selected_color
        if self.on_color_change:
            # Convertir HEX a RGB
            rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            self.on_color_change(rgb)