import customtkinter as ctk
import threading
import logging
import tkinter as tk
from core.light_manager import LightManager
from ui.hotkeys_settings import HotkeysSettings
from config.hotkeys_manager import HotkeysManager
from ui.widgets.modern_color_picker import ModernColorPicker # Asegúrate de la ruta

class MainWindow(ctk.CTk):
    """
    Ventana principal de la app WiZ. UI Renovada.
    """
    def __init__(self, light_manager: LightManager, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.light_manager = light_manager
        self.selected_bulb = getattr(light_manager, 'selected_bulb', None)
        self.title("WizZ Controller")
        self.geometry("800x500") # Un poco más ancha para que quepa todo bien
        
        # Configuración de Grid Principal
        self.grid_columnconfigure(0, weight=1) # Panel Izquierdo (Color)
        self.grid_columnconfigure(1, weight=2) # Panel Derecho (Controles)
        self.grid_rowconfigure(0, weight=1)

        # --- PANEL IZQUIERDO: Rueda de Color ---
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Instanciamos nuestro NUEVO Color Picker
        # OJO: Asegúrate de crear la carpeta ui/widgets/ o ajusta la importación
        self.modern_picker = ModernColorPicker(
            self.left_frame, 
            on_color_change=self._on_color_change
        )
        self.modern_picker.pack(fill="both", expand=True)


        # --- PANEL DERECHO: Controles Generales ---
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        self.right_frame.grid_columnconfigure(0, weight=1)
        
        # 1. Info Ampolleta
        self.bulb_info_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.bulb_info_frame.pack(fill="x", padx=20, pady=20)
        
        self.lbl_status = ctk.CTkLabel(self.bulb_info_frame, text="Estado: --", font=("Arial", 16, "bold"))
        self.lbl_status.pack(anchor="w")
        
        self.bulb_label = ctk.CTkLabel(self.bulb_info_frame, text="No hay ampolleta seleccionada", text_color="gray")
        self.bulb_label.pack(anchor="w")

        # 2. Sliders
        self.sliders_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.sliders_frame.pack(fill="x", padx=20, pady=10)

        # Brillo
        ctk.CTkLabel(self.sliders_frame, text="Brillo").pack(anchor="w")
        self.brightness_slider = ctk.CTkSlider(self.sliders_frame, from_=0, to=100, command=self._on_brightness_change)
        self.brightness_slider.set(100)
        self.brightness_slider.pack(fill="x", pady=(0, 15))

        # Temperatura
        ctk.CTkLabel(self.sliders_frame, text="Temperatura (Calidez)").pack(anchor="w")
        self.temperature_slider = ctk.CTkSlider(self.sliders_frame, from_=2200, to=6500, command=self._on_temperature_change)
        self.temperature_slider.set(4000)
        self.temperature_slider.pack(fill="x", pady=(0, 15))

        # 3. Botones Grandes de Acción
        self.actions_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.actions_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_on = ctk.CTkButton(self.actions_frame, text="ENCENDER", height=40, fg_color="#27ae60", hover_color="#2ecc71", command=self._turn_on)
        self.btn_on.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_off = ctk.CTkButton(self.actions_frame, text="APAGAR", height=40, fg_color="#c0392b", hover_color="#e74c3c", command=self._turn_off)
        self.btn_off.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # 4. Extras
        self.btn_search = ctk.CTkButton(self.right_frame, text="Buscar Dispositivos en Red", fg_color="#2980b9", command=self._search_bulb)
        self.btn_search.pack(pady=20)


        # Inicialización
        self._bind_hotkeys()
        self._build_menu()
        self._show_selected_bulb()
        
        # Hotkeys Init
        self._init_hotkeys_system()

    def _init_hotkeys_system(self):
        def update_hotkeys():
            from config.hotkeys_manager import HotkeysManager
            from core.actions import get_action_func 
            import keyboard
            
            hotkeys_manager = HotkeysManager()
            keyboard.unhook_all()
            
            hotkeys = hotkeys_manager.get_hotkeys()
            for combo, entry in hotkeys.items():
                try:
                    if isinstance(entry, str): entry = {"action": entry, "enabled": True}
                    if not entry.get("enabled", True): continue

                    action_id = entry.get("action")
                    if not action_id: continue

                    action_func = get_action_func(action_id)
                    
                    def run_action_wrapper(func=action_func, p=entry, aid=action_id):
                        if aid == "set_color_custom" and "color" in p:
                            func(self.light_manager, p["color"])
                        else:
                            func(self.light_manager)

                    keyboard.add_hotkey(combo, run_action_wrapper, suppress=False)
                except Exception:
                    pass
        
        update_hotkeys()
        self.update_hotkeys_func = update_hotkeys

    def _bind_hotkeys(self):
        self.bind_all('<Control-e>', lambda e: self.light_manager.turn_on())
        self.bind_all('<Control-a>', lambda e: self.light_manager.turn_off())

    def _turn_on(self):
        self.light_manager.turn_on()
        self.lbl_status.configure(text="Estado: Encendido", text_color="#2ecc71")

    def _turn_off(self):
        self.light_manager.turn_off()
        self.lbl_status.configure(text="Estado: Apagado", text_color="#e74c3c")

    def _search_bulb(self):
        threading.Thread(target=self._discover_bulbs_thread, daemon=True).start()

    def _discover_bulbs_thread(self):
        try:
            bulbs = self.light_manager.discover_bulbs()
        except Exception as e:
            logging.error(f"Error: {e}")
            bulbs = []
        self.after(0, lambda: self._show_bulb_list(bulbs))

    def _show_bulb_list(self, bulbs):
        popup = ctk.CTkToplevel(self)
        popup.title("Ampolletas")
        popup.geometry("300x400")
        
        ctk.CTkLabel(popup, text="Dispositivos encontrados:", font=("Arial", 14, "bold")).pack(pady=10)
        
        if not bulbs:
            ctk.CTkLabel(popup, text="No se encontraron dispositivos.").pack(pady=10)
            
        for bulb in bulbs:
            ctk.CTkButton(
                popup, 
                text=f"{bulb.get('ip')} \n {bulb.get('mac')}", 
                command=lambda b=bulb: self._select_bulb(b, popup)
            ).pack(pady=5, padx=20, fill="x")

    def _select_bulb(self, bulb, popup):
        self.selected_bulb = bulb
        self.light_manager.set_selected_bulb(bulb)
        if bulb.get("ip"):
            self.light_manager.register_bulb(bulb.get("ip"), bulb.get("ip"))
            from config.bulbs_manager import BulbsManager
            BulbsManager().add_bulb(bulb)
            
        popup.destroy()
        self._show_selected_bulb()

    def _show_selected_bulb(self):
        if self.selected_bulb:
            self.bulb_label.configure(text=f"IP: {self.selected_bulb.get('ip')}\nMAC: {self.selected_bulb.get('mac')}", text_color="white")
            self.lbl_status.configure(text="Estado: Conectado")
        else:
            self.bulb_label.configure(text="No hay ampolleta seleccionada", text_color="gray")

    def _on_color_change(self, rgb):
        self.light_manager.set_color(rgb)

    def _on_brightness_change(self, value):
        self.light_manager.set_brightness(int(value))

    def _on_temperature_change(self, value):
        self.light_manager.set_temperature(int(value))

    def open_hotkeys_settings(self):
        if self.update_hotkeys_func:
            HotkeysSettings(self, HotkeysManager(), self.update_hotkeys_func)

    def _build_menu(self):
        menubar = tk.Menu(self)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Galería de Luz", command=self.open_scenes_ui)
        settings_menu.add_command(label="Hotkeys", command=self.open_hotkeys_settings)
        settings_menu.add_command(label="Voz", command=self.open_voice_commands_ui)
        menubar.add_cascade(label="Menú", menu=settings_menu)
        self.config(menu=menubar)

    def open_voice_commands_ui(self):
        from ui.voice_commands_ui import VoiceCommandsUI
        manager = getattr(self, '_voice_manager', None)
        VoiceCommandsUI(self, manager)

    def open_scenes_ui(self):
        from ui.scenes_ui import ScenesUI
        ScenesUI(self, self.light_manager)