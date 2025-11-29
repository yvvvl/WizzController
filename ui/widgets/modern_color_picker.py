import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import math
import colorsys
from config.presets_manager import PresetsManager

class SmoothSlider(tk.Canvas):
    """
    Slider de alto rendimiento en Canvas. Soporta degradados o imágenes de fondo.
    """
    def __init__(self, master, width=250, height=20, color_start="#000000", color_end="#ffffff", gradient_img=None, command=None, initial=0.0):
        # Fix para fondo transparente en CTk
        bg_color = master._apply_appearance_mode(master._fg_color)
        if bg_color == "transparent" or not bg_color:
            try: bg_color = master.master._apply_appearance_mode(master.master._fg_color)
            except: pass
        if bg_color == "transparent" or not bg_color:
            bg_color = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#dbdbdb"

        super().__init__(master, width=width, height=height, bg=bg_color, highlightthickness=0)
        self.command = command
        self.width = width
        self.height = height
        self.value = max(0.0, min(1.0, initial))
        
        if gradient_img:
            self.bg_image = gradient_img
        else:
            self.bg_image = self._create_gradient(width, height, color_start, color_end)
            
        self.create_image(0, 0, image=self.bg_image, anchor="nw")
        
        self.r = 8
        self.thumb = self.create_oval(0, 0, 0, 0, fill="white", outline="#dddddd", width=1)
        
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self._update_thumb_pos()

    def _create_gradient(self, w, h, c1, c2):
        # Asegura que los colores sean hex válidos
        def fix_hex(col, default):
            if not col or not isinstance(col, str) or len(col) != 7 or not col.startswith('#'):
                return default
            try:
                int(col[1:], 16)
                return col
            except ValueError:
                return default
        c1 = fix_hex(c1, "#000000")
        c2 = fix_hex(c2, "#ffffff")
        base = Image.new("RGB", (2, 1))
        rgb1 = tuple(int(c1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        rgb2 = tuple(int(c2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        base.putpixel((0, 0), rgb1)
        base.putpixel((1, 0), rgb2)
        resized = base.resize((w, h), Image.Resampling.BILINEAR)
        return ImageTk.PhotoImage(resized)

    def _update_thumb_pos(self):
        x = int(self.value * self.width)
        cy = self.height // 2
        self.coords(self.thumb, x - self.r, cy - self.r, x + self.r, cy + self.r)

    def _update_from_event(self, event):
        x = max(0, min(self.width, event.x))
        self.value = x / self.width
        self._update_thumb_pos()
        if self.command: self.command(self.value)

    def _on_click(self, event): self._update_from_event(event)
    def _on_drag(self, event): self._update_from_event(event)
    def set_value(self, val):
        self.value = max(0.0, min(1.0, val))
        self._update_thumb_pos()

class ModernColorPicker(ctk.CTkFrame):
    def __init__(self, master, width=350, height=600, on_color_change=None, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)
        self.on_color_change = on_color_change
        self.presets_manager = PresetsManager()
        
        # Estado HSV Inicial
        self.h = 0.0 
        self.s = 1.0 
        self.v = 1.0
        self.current_rgb = (255, 0, 0)
        
        # Configuración Visual Rueda
        self.wheel_size = 240
        self.ring_width = 30
        self.center = self.wheel_size // 2
        self.inner_radius = (self.wheel_size // 2) - self.ring_width - 8
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Pestañas
        self.tab_view = ctk.CTkTabview(self, width=width-20, height=520)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_wheel = self.tab_view.add("Rueda")
        self.tab_sliders = self.tab_view.add("Mezclador Pro")
        
        self._pre_render_graphics()
        self._build_wheel_tab()
        self._build_sliders_tab()
        self._build_favorites()
        
        self._update_ui(notify=False)

    def _pre_render_graphics(self):
        ss = 4
        size_ss = self.wheel_size * ss
        center_ss = size_ss // 2
        ring_w_ss = self.ring_width * ss
        inner_r_ss = self.inner_radius * ss
        
        # A. ANILLO HUE
        img_ring = Image.new("RGBA", (size_ss, size_ss), (0,0,0,0))
        pix = img_ring.load()
        for x in range(size_ss):
            for y in range(size_ss):
                dx, dy = x - center_ss, y - center_ss
                dist = math.sqrt(dx*dx + dy*dy)
                if (center_ss - ring_w_ss) <= dist <= center_ss:
                    angle = math.atan2(dy, dx)
                    hue = (angle + math.pi) / (2 * math.pi)
                    r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
                    alpha = 255
                    if dist > center_ss - 4: alpha = int(255 * (center_ss - dist) / 4)
                    if dist < center_ss - ring_w_ss + 4: alpha = int(255 * (dist - (center_ss - ring_w_ss)) / 4)
                    pix[x,y] = (int(r*255), int(g*255), int(b*255), max(0, min(255, alpha)))
        self.img_ring = ImageTk.PhotoImage(img_ring.resize((self.wheel_size, self.wheel_size), Image.Resampling.LANCZOS))
        
        # B. MÁSCARA DISCO (Saturación Radial)
        img_disc = Image.new("RGBA", (inner_r_ss*2, inner_r_ss*2), (0,0,0,0))
        pix_d = img_disc.load()
        rad = inner_r_ss
        for x in range(rad*2):
            for y in range(rad*2):
                dx, dy = x - rad, y - rad
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= rad:
                    alpha = int(255 * (1 - (dist / rad)))
                    pix_d[x,y] = (255, 255, 255, alpha)
        self.img_disc_overlay = ImageTk.PhotoImage(img_disc.resize((self.inner_radius*2, self.inner_radius*2), Image.Resampling.LANCZOS))

        # C. GRADIENTE ARCOÍRIS (Para Slider H)
        img_rainbow = Image.new("RGB", (256, 1))
        pix_r = img_rainbow.load()
        for x in range(256):
            r, g, b = colorsys.hsv_to_rgb(x/255.0, 1.0, 1.0)
            pix_r[x, 0] = (int(r*255), int(g*255), int(b*255))
        # Ancho del slider en el mezclador (aprox 220)
        self.img_rainbow = ImageTk.PhotoImage(img_rainbow.resize((220, 18), Image.Resampling.BILINEAR))

    def _build_wheel_tab(self):
        self.canvas = tk.Canvas(self.tab_wheel, width=self.wheel_size, height=self.wheel_size, bg=self._apply_appearance_mode(self._fg_color), highlightthickness=0)
        self.canvas.pack(pady=20)
        c = self.center
        self.canvas.create_image(c, c, image=self.img_ring)
        r = self.inner_radius
        self.disc_bg_id = self.canvas.create_oval(c-r, c-r, c+r, c+r, fill="red", outline="")
        self.canvas.create_image(c, c, image=self.img_disc_overlay)
        self.cur_ring = self.canvas.create_oval(0,0,0,0, outline="white", width=3)
        self.canvas.create_oval(0,0,0,0, outline="black", width=1, tags="sh_r")
        self.cur_disc = self.canvas.create_oval(0,0,0,0, outline="black", width=2)
        self.canvas.bind("<Button-1>", self._on_touch)
        self.canvas.bind("<B1-Motion>", self._on_touch)

        ctk.CTkLabel(self.tab_wheel, text="Brillo (Value)", font=("Arial", 12, "bold")).pack(pady=(15,5))
        self.val_slider = SmoothSlider(self.tab_wheel, width=240, height=18, color_start="#000000", color_end="#ffffff", command=self._on_val_change)
        self.val_slider.pack(pady=5)
        self.val_slider.set_value(1.0)

    def _build_slider_row(self, parent, label, tag, row, cmd_slider, cmd_entry, c1=None, c2=None, img=None, suffix=""):
        ctk.CTkLabel(parent, text=label, font=("Arial", 12, "bold"), width=25, anchor="w").grid(row=row, column=0, padx=(5,0))
        s = SmoothSlider(parent, width=220, height=18, color_start=c1, color_end=c2, gradient_img=img, command=cmd_slider)
        s.grid(row=row, column=1, sticky="ew", padx=10, pady=6)
        f_e = ctk.CTkFrame(parent, fg_color="transparent")
        f_e.grid(row=row, column=2)
        e = ctk.CTkEntry(f_e, width=45, justify="center")
        e.pack(side="left")
        e.bind("<Return>", cmd_entry)
        e.bind("<FocusOut>", cmd_entry)
        if suffix: ctk.CTkLabel(f_e, text=suffix, width=15).pack(side="left")
        self.sliders[tag] = s
        self.entries[tag] = e

    def _build_sliders_tab(self):
        f = ctk.CTkFrame(self.tab_sliders, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=10, pady=10)
        f.grid_columnconfigure(1, weight=1)
        
        self.preview = ctk.CTkLabel(f, text="", height=40, fg_color="red", corner_radius=6)
        self.preview.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        self.sliders = {}
        self.entries = {}
        row = 1
        
        # RGB
        for char, c1, c2 in [("R", "#000", "#f00"), ("G", "#000", "#0f0"), ("B", "#000", "#00f")]:
            self._build_slider_row(f, char, char, row, lambda v, c=char: self._on_rgb_slider(c, v), lambda ev, c=char: self._on_rgb_entry(c), c1=c1, c2=c2)
            row += 1
            
        tk.Frame(f, height=1, bg="#555").grid(row=row, column=0, columnspan=3, sticky="ew", pady=12)
        row += 1
        
        # HSV
        self._build_slider_row(f, "H", "H", row, lambda v: self._on_hsv_slider("H", v), lambda ev: self._on_hsv_entry("H"), img=self.img_rainbow, suffix="°")
        self._build_slider_row(f, "S", "S", row+1, lambda v: self._on_hsv_slider("S", v), lambda ev: self._on_hsv_entry("S"), c1="#fff", c2="#f00", suffix="%")
        self._build_slider_row(f, "V", "V", row+2, lambda v: self._on_hsv_slider("V", v), lambda ev: self._on_hsv_entry("V"), c1="#000", c2="#fff", suffix="%")
        row += 3

        ctk.CTkLabel(f, text="HEX", font=("Arial", 12, "bold")).grid(row=row, column=0, padx=5, pady=15)
        self.hex_entry = ctk.CTkEntry(f, justify="center", font=("Consolas", 12))
        self.hex_entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=10, pady=15)
        self.hex_entry.bind("<Return>", self._on_hex)

    def _build_favorites(self):
        frame = ctk.CTkFrame(self, height=110)
        frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        h = ctk.CTkFrame(frame, fg_color="transparent")
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text="Favoritos", font=("Arial", 12, "bold")).pack(side="left")
        ctk.CTkButton(h, text="+", width=30, height=20, command=self._save_fav).pack(side="right")
        self.fav_grid = ctk.CTkFrame(frame, fg_color="transparent")
        self.fav_grid.pack(fill="x", pady=5)
        self.refresh_favs()

    # --- LÓGICA ---
    def _on_touch(self, event):
        cx, cy = self.center, self.center
        dx, dy = event.x - cx, event.y - cy
        dist = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        ring_inner = self.inner_radius
        if dist > ring_inner + 2:
            self.h = (angle + math.pi) / (2 * math.pi)
        else:
            self.s = min(1.0, max(0.0, dist / ring_inner))
        self._update_ui(mouse=True)
        if self.on_color_change: self.on_color_change(self.current_rgb)

    def _on_val_change(self, val):
        self.v = val
        self._update_ui(skip_wheel_bg=True)
        if self.on_color_change: self.on_color_change(self.current_rgb)

    def _on_rgb_slider(self, char, val):
        rgb = list(self.current_rgb)
        rgb[{"R":0,"G":1,"B":2}[char]] = int(val * 255)
        self.current_rgb = tuple(rgb)
        self.h, self.s, self.v = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        self._update_ui(upd_sliders=False)
        if self.on_color_change: self.on_color_change(self.current_rgb)

    def _on_rgb_entry(self, char):
        try:
            val = max(0, min(255, int(self.entries[char].get())))
            self.entries[char].delete(0, tk.END); self.entries[char].insert(0, str(val))
            rgb = list(self.current_rgb)
            rgb[{"R":0,"G":1,"B":2}[char]] = val
            self.current_rgb = tuple(rgb)
            self.h, self.s, self.v = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
            self._update_ui()
            if self.on_color_change: self.on_color_change(self.current_rgb)
        except: pass

    def _on_hsv_slider(self, char, val):
        if char=="H": self.h = val
        elif char=="S": self.s = val
        elif char=="V": self.v = val
        self._update_ui(upd_sliders=False)
        if self.on_color_change: self.on_color_change(self.current_rgb)

    def _on_hsv_entry(self, char):
        try:
            s_val = self.entries[char].get()
            val = float(s_val) / (360.0 if char=="H" else 100.0)
            val = max(0.0, min(1.0, val))
            if char=="H": self.h = val
            elif char=="S": self.s = val
            elif char=="V": self.v = val
            self._update_ui()
            if self.on_color_change: self.on_color_change(self.current_rgb)
        except: pass

    def _on_hex(self, event):
        try:
            h = self.hex_entry.get().lstrip('#')
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            self.current_rgb = rgb
            self.h, self.s, self.v = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
            self._update_ui()
            if self.on_color_change: self.on_color_change(self.current_rgb)
        except: pass

    def _update_ui(self, mouse=False, upd_sliders=True, skip_wheel_bg=False, notify=True):
        if not mouse:
            r, g, b = colorsys.hsv_to_rgb(self.h, self.s, self.v)
            self.current_rgb = (int(r*255), int(g*255), int(b*255))
        
        hex_f = f"#{self.current_rgb[0]:02x}{self.current_rgb[1]:02x}{self.current_rgb[2]:02x}"
        self.preview.configure(fg_color=hex_f)
        
        if not skip_wheel_bg:
            rp, gp, bp = colorsys.hsv_to_rgb(self.h, 1, 1)
            self.canvas.itemconfig(self.disc_bg_id, fill=f"#{int(rp*255):02x}{int(gp*255):02x}{int(bp*255):02x}")

        cx, cy = self.center, self.center
        ang = (self.h * 2 * math.pi) - math.pi
        rr = (self.wheel_size - self.ring_width) / 2
        ax, ay = cx + math.cos(ang)*rr, cy + math.sin(ang)*rr
        self.canvas.coords(self.cur_ring, ax-6, ay-6, ax+6, ay+6)
        
        dist_d = self.s * self.inner_radius
        dx, dy = cx + math.cos(ang)*dist_d, cy + math.sin(ang)*dist_d
        self.canvas.coords(self.cur_disc, dx-5, dy-5, dx+5, dy+5)
        self.canvas.itemconfig(self.cur_disc, outline="white" if self.s > 0.5 else "black")

        if upd_sliders:
            self.val_slider.set_value(self.v)
            for c, v in zip("RGB", self.current_rgb):
                self.sliders[c].set_value(v/255)
                if self.focus_get()!=self.entries[c]: self.entries[c].delete(0, tk.END); self.entries[c].insert(0, str(v))
            
            self.sliders["H"].set_value(self.h); self.sliders["S"].set_value(self.s); self.sliders["V"].set_value(self.v)
            if self.focus_get()!=self.entries["H"]: self.entries["H"].delete(0, tk.END); self.entries["H"].insert(0, f"{int(self.h*360)}")
            if self.focus_get()!=self.entries["S"]: self.entries["S"].delete(0, tk.END); self.entries["S"].insert(0, f"{int(self.s*100)}")
            if self.focus_get()!=self.entries["V"]: self.entries["V"].delete(0, tk.END); self.entries["V"].insert(0, f"{int(self.v*100)}")
        
        if self.focus_get()!=self.hex_entry: self.hex_entry.delete(0, tk.END); self.hex_entry.insert(0, hex_f)

    def refresh_favs(self):
        for w in self.fav_grid.winfo_children(): w.destroy()
        presets = self.presets_manager.get_presets()
        keys = list(presets.keys())[:10]
        for i, k in enumerate(keys):
            rgb = presets[k]
            hc = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            b = ctk.CTkButton(self.fav_grid, text="", width=30, height=30, fg_color=hc, command=lambda r=rgb: self._load_fav(r))
            b.grid(row=i//5, column=i%5, padx=3, pady=3)
            
    def _save_fav(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("Guardar", "Nombre:")
        if name: self.presets_manager.add_preset(name, list(self.current_rgb)); self.refresh_favs()
        
    def _load_fav(self, rgb):
        self.current_rgb = rgb
        self.h, self.s, self.v = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        self._update_ui()
        if self.on_color_change: self.on_color_change(rgb)