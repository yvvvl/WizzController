import customtkinter as ctk
import tkinter as tk
from tkinter import simpledialog, messagebox
from core.wiz_scenes_data import SCENES_DATA
from config.presets_manager import PresetsManager

class ScenesUI(ctk.CTkToplevel):
    def __init__(self, master, light_manager, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Galería de Luz")
        self.geometry("700x550")
        self.light_manager = light_manager
        self.presets_manager = PresetsManager()
        
        # Crear sistema de Pestañas
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_scenes = self.tab_view.add("Escenas WiZ")
        self.tab_colors = self.tab_view.add("Mis Colores")
        
        self._build_scenes_tab()
        self._build_colors_tab()

    def _build_scenes_tab(self):
        # Frame desplazable para que quepan todas
        scroll = ctk.CTkScrollableFrame(self.tab_scenes, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        for category, scenes in SCENES_DATA.items():
            # Título de Categoría
            ctk.CTkLabel(scroll, text=category, font=("Helvetica", 16, "bold"), anchor="w").pack(fill="x", pady=(15, 5), padx=5)
            
            # Grid para los botones
            grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            grid_frame.pack(fill="x", padx=5)
            
            # Crear botones en columnas de 3
            columns = 3
            for i, (name, scene_id, icon) in enumerate(scenes):
                btn = ctk.CTkButton(
                    grid_frame,
                    text=f"{icon}  {name}",
                    height=40,
                    fg_color="#2B2B2B", # Color oscuro tipo tarjeta
                    hover_color="#3A3A3A",
                    command=lambda sid=scene_id: self.light_manager.activate_scene(sid)
                )
                btn.grid(row=i // columns, column=i % columns, padx=5, pady=5, sticky="ew")
            
            # Configurar columnas para que se expandan
            for c in range(columns):
                grid_frame.grid_columnconfigure(c, weight=1)

    def _build_colors_tab(self):
        # Panel superior: Guardar color actual
        top_frame = ctk.CTkFrame(self.tab_colors)
        top_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            top_frame, 
            text="💾 Guardar Color Actual", 
            fg_color="#1f6aa5",
            command=self._save_current_color
        ).pack(side="left", expand=True, fill="x")

        # Área de colores guardados
        self.colors_scroll = ctk.CTkScrollableFrame(self.tab_colors, fg_color="transparent")
        self.colors_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._refresh_colors_grid()

    def _refresh_colors_grid(self):
        # Limpiar grid anterior
        for widget in self.colors_scroll.winfo_children():
            widget.destroy()

        presets = self.presets_manager.get_presets()
        if not presets:
            ctk.CTkLabel(self.colors_scroll, text="No hay colores guardados.", text_color="gray").pack(pady=20)
            return

        columns = 4
        i = 0
        for name, rgb in presets.items():
            # Convertir RGB lista a Hex para mostrar en el botón
            hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            
            # Contenedor de "Tarjeta"
            card = ctk.CTkFrame(self.colors_scroll, fg_color="#333333")
            card.grid(row=i // columns, column=i % columns, padx=5, pady=5, sticky="ew")
            
            # Muestra del color (Botón funcional)
            color_btn = ctk.CTkButton(
                card, 
                text="", 
                fg_color=hex_color, 
                hover_color=hex_color,
                height=50,
                width=50,
                command=lambda r=rgb: self.light_manager.set_color(tuple(r))
            )
            color_btn.pack(pady=5, padx=5)

            # Nombre
            ctk.CTkLabel(card, text=name, font=("Arial", 11)).pack(pady=(0,2))
            
            # Botón borrar (pequeño)
            del_btn = ctk.CTkButton(
                card, 
                text="X", 
                width=20, 
                height=20, 
                fg_color="#cc0000", 
                hover_color="#aa0000",
                command=lambda n=name: self._delete_color(n)
            )
            del_btn.pack(pady=(0, 5))
            
            i += 1
            
        for c in range(columns):
            self.colors_scroll.grid_columnconfigure(c, weight=1)

    def _save_current_color(self):
        # Intentamos obtener el último color enviado desde el manager
        last_rgb = getattr(self.light_manager, 'last_rgb', (255, 255, 255))
        
        name = simpledialog.askstring("Guardar Color", "Nombre para este color:")
        if name:
            self.presets_manager.add_preset(name, list(last_rgb))
            self._refresh_colors_grid()

    def _delete_color(self, name):
        if messagebox.askyesno("Confirmar", f"¿Eliminar '{name}'?"):
            self.presets_manager.delete_preset(name)
            self._refresh_colors_grid()