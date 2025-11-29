import customtkinter as ctk
import threading
import logging
import tkinter as tk
from core.light_manager import LightManager
from config.bulbs_manager import BulbsManager
from ui.color_picker import ColorPickerWidget
from ui.hotkeys_settings import HotkeysSettings
from config.hotkeys_manager import HotkeysManager

class MainWindow(ctk.CTk):
    """
    Ventana principal de la app WiZ. Permite controlar bombillas y acceder a configuraciones.
    """
    def __init__(self, light_manager: LightManager, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.light_manager = light_manager
        self.selected_bulb = getattr(light_manager, 'selected_bulb', None)
        self.title("Control de Bombillas WiZ")
        self.geometry("600x400")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Color Picker con callback
        self.color_picker = ColorPickerWidget(self.main_frame, on_color_change=self._on_color_change)
        self.color_picker.grid(row=0, column=0, pady=10)

        # Controles de Brillo y Temperatura
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.controls_frame.grid_columnconfigure(1, weight=1)

        # Slider de Brillo
        self.brightness_label = ctk.CTkLabel(self.controls_frame, text="Brillo")
        self.brightness_label.grid(row=0, column=0, padx=10, pady=5)
        self.brightness_slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, command=self._on_brightness_change)
        self.brightness_slider.grid(row=1, column=0, padx=10, pady=5)

        # Slider de Temperatura
        self.temperature_label = ctk.CTkLabel(self.controls_frame, text="Temperatura (K)")
        self.temperature_label.grid(row=0, column=1, padx=10, pady=5)
        self.temperature_slider = ctk.CTkSlider(self.controls_frame, from_=2200, to=6500, command=self._on_temperature_change)
        self.temperature_slider.grid(row=1, column=1, padx=10, pady=5)

        # Botones de Control
        self.create_controls()
        self._bind_hotkeys()
        self._build_menu()

        # Función para actualizar hotkeys globales
        def update_hotkeys():
            from config.hotkeys_manager import HotkeysManager
            from core.actions import get_action
            import keyboard
            hotkeys_manager = HotkeysManager()
            keyboard.unhook_all()
            for combo, entry in hotkeys_manager.get_hotkeys().items():
                try:
                    action_id = entry["action"] if isinstance(entry, dict) else entry
                    color = entry.get("color") if isinstance(entry, dict) else None
                    def run_action(aid=action_id, col=color):
                        if aid == "set_color_custom" and col:
                            get_action("set_color_custom")(self.light_manager, col)
                        else:
                            get_action(aid)(self.light_manager)
                    keyboard.add_hotkey(combo, run_action, suppress=False)
                except Exception as e:
                    print(f"Error registrando hotkey {combo}: {e}")

        # Registrar hotkeys globales al iniciar la app
        update_hotkeys()

        # Abrir ventana de hotkeys pasando managers y función de reinicio
        from config.hotkeys_manager import HotkeysManager
        hotkeys_manager = HotkeysManager()
        self.btn_hotkeys = ctk.CTkButton(
            self.main_frame,
            text="Configurar Hotkeys",
            command=lambda: HotkeysSettings(
                self,
                hotkeys_manager,
                update_hotkeys
            )
        )
        self.btn_hotkeys.grid(row=2, column=0, pady=10)

    def _bind_hotkeys(self):
        # Encender bombilla: Ctrl+E
        self.bind_all('<Control-e>', lambda e: self.light_manager.turn_on())
        # Apagar bombilla: Ctrl+A
        self.bind_all('<Control-a>', lambda e: self.light_manager.turn_off())
        # Brillo máximo: Ctrl+Shift+Up
        self.bind_all('<Control-Shift-Up>', lambda e: self.light_manager.set_brightness(100))
        # Brillo mínimo: Ctrl+Shift+Down
        self.bind_all('<Control-Shift-Down>', lambda e: self.light_manager.set_brightness(0))
        # Buscar ampolleta: Ctrl+B
        self.bind_all('<Control-b>', lambda e: self._search_bulb())

    def create_controls(self):
        # Botón Encender
        self.on_btn = ctk.CTkButton(self.controls_frame, text="Encender", command=self._turn_on)
        self.on_btn.grid(row=2, column=0, padx=10, pady=10)
        # Botón Apagar
        self.off_btn = ctk.CTkButton(self.controls_frame, text="Apagar", command=self._turn_off)
        self.off_btn.grid(row=2, column=1, padx=10, pady=10)
        # Botón Buscar Ampolleta
        self.search_btn = ctk.CTkButton(self.controls_frame, text="Buscar Ampolleta", command=self._search_bulb)
        self.search_btn.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    def _turn_on(self) -> None:
        self.light_manager.turn_on()

    def _turn_off(self) -> None:
        self.light_manager.turn_off()

    def _search_bulb(self) -> None:
        # Ejecutar la búsqueda en segundo plano para evitar congelar la UI
        threading.Thread(target=self._discover_bulbs_thread, daemon=True).start()

    def _discover_bulbs_thread(self) -> None:
        try:
            bulbs = self.light_manager.discover_bulbs()
        except Exception as e:
            logging.error(f"Error buscando bombillas: {e}")
            bulbs = []
        self.after(0, lambda: self._show_bulb_list(bulbs))

    def _show_bulb_list(self, bulbs: list[dict]) -> None:
        # Permite seleccionar una ampolleta encontrada
        popup = ctk.CTkToplevel(self)
        popup.title("Ampolletas encontradas")
        popup.geometry("350x350")
        label = ctk.CTkLabel(popup, text="Ampolletas encontradas:", font=("Helvetica", 14))
        label.pack(pady=10)
        self.selected_bulb = None
        if not bulbs:
            no_bulb_label = ctk.CTkLabel(popup, text="No se encontraron ampolletas.", font=("Helvetica", 12))
            no_bulb_label.pack(pady=10)
        for bulb in bulbs:
            btn = ctk.CTkButton(popup, text=f"{bulb.get('ip', '')} - {bulb.get('mac', '')}", command=lambda b=bulb: self._select_bulb(b, popup))
            btn.pack(pady=2)
        ctk.CTkButton(popup, text="Cerrar", command=popup.destroy).pack(pady=10)

    def _select_bulb(self, bulb: dict, popup: ctk.CTkToplevel) -> None:
        try:
            self.selected_bulb = bulb
            self.light_manager.set_selected_bulb(bulb)
            from config.bulbs_manager import BulbsManager
            bulbs_manager = BulbsManager()
            bulbs_manager.add_bulb(bulb)
        except Exception as e:
            logging.error(f"Error guardando bombilla: {e}")
            self.show_toast(f"Error guardando bombilla: {e}")
        popup.destroy()
        self._show_selected_bulb()

    def _show_selected_bulb(self) -> None:
        # Muestra la ampolleta seleccionada en la UI principal
        if hasattr(self, 'bulb_label'):
            self.bulb_label.destroy()
        if self.selected_bulb:
            info = f"Ampolleta seleccionada: IP={self.selected_bulb.get('ip', '')} MAC={self.selected_bulb.get('mac', '')}"
        else:
            info = "No hay ampolleta seleccionada."
        self.bulb_label = ctk.CTkLabel(self.main_frame, text=info, font=("Helvetica", 12))
        self.bulb_label.grid(row=2, column=0, pady=5)

    def _on_color_change(self, rgb: tuple[int, int, int]) -> None:
        self.light_manager.set_color(rgb)

    def _on_brightness_change(self, value):
        """Callback para manejar cambios en el brillo."""
        self.light_manager.set_brightness(int(value))

    def _on_temperature_change(self, value):
        """Callback para manejar cambios en la temperatura."""
        self.light_manager.set_temperature(int(value))

    def discover_bulbs(self):
        def background_discover():
            async def discover():
                bulbs = await BulbDiscovery.discover_bulbs()
                self.bulb_list.configure(values=[f"{bulb['ip']} ({bulb['mac']})" for bulb in bulbs])
            asyncio.run(discover())

        threading.Thread(target=background_discover, daemon=True).start()

    def select_bulb(self):
        selected = self.bulb_list.get()
        if selected:
            ip = selected.split(" ")[0]
            bulb_id = ip  # Use IP as ID for simplicity
            self.light_manager.register_bulb(bulb_id, ip)
            self.light_manager.set_active_bulb(bulb_id)
            # Save bulb to bulbs.json
            self.bulbs_manager.add_bulb({"id": bulb_id, "ip": ip, "name": "Nueva Ampolleta"})

    def show_toast(self, message, duration=2500):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.geometry(f"300x40+{self.winfo_x()+50}+{self.winfo_y()+50}")
        label = ctk.CTkLabel(toast, text=message, font=("Helvetica", 12), fg_color="#222", text_color="white")
        label.pack(expand=True, fill="both")
        toast.after(duration, toast.destroy)

    def notify_no_bulb_found(self):
        self.show_toast("No se encontró ninguna ampolleta en la red.")

    def open_hotkeys_settings(self):
        hotkeys_manager = HotkeysManager()
        # Usa la misma función update_hotkeys que en el botón principal
        def update_hotkeys():
            import keyboard
            keyboard.unhook_all()
            for combo, entry in hotkeys_manager.get_hotkeys().items():
                try:
                    action_id = entry["action"] if isinstance(entry, dict) else entry
                    color = entry.get("color") if isinstance(entry, dict) else None
                    from core.actions import get_action
                    def run_action(aid=action_id, col=color):
                        if aid == "set_color_custom" and col:
                            get_action("set_color_custom")(self.light_manager, col)
                        else:
                            get_action(aid)(self.light_manager)
                    keyboard.add_hotkey(combo, run_action, suppress=False)
                except Exception as e:
                    print(f"Error registrando hotkey {combo}: {e}")
        HotkeysSettings(self, hotkeys_manager, update_hotkeys)

    def _build_menu(self):
        menubar = tk.Menu(self)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Configurar Hotkeys", command=self.open_hotkeys_settings)
        # Nueva opción para comandos de voz
        settings_menu.add_command(label="Comandos de Voz", command=self.open_voice_commands_ui)
        menubar.add_cascade(label="Opciones", menu=settings_menu)
        self.config(menu=menubar)

    def open_voice_commands_ui(self):
        from core.voice_commands import VoiceCommandManager
        from ui.voice_commands_ui import VoiceCommandsUI
        # Instancia única para la sesión
        if not hasattr(self, '_voice_manager'):
            self._voice_manager = VoiceCommandManager()
        VoiceCommandsUI(self, self._voice_manager)

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")
    app = MainWindow(LightManager())
    app.mainloop()