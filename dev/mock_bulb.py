import asyncio
import json
import flet as ft

# Configuración
MOCK_IP = "127.0.0.1"
MOCK_PORT = 38899
MOCK_MAC = "aa:bb:cc:dd:ee:ff"

def interpolate_color(k, k_min, k_max, c_min, c_max):
    """Mezcla dos colores basándose en la temperatura K"""
    factor = (k - k_min) / (k_max - k_min)
    factor = max(0.0, min(1.0, factor))
    
    r = int(c_min[0] + (c_max[0] - c_min[0]) * factor)
    g = int(c_min[1] + (c_max[1] - c_min[1]) * factor)
    b = int(c_min[2] + (c_max[2] - c_min[2]) * factor)
    return (r, g, b)

def kelvin_to_rgb(kelvin):
    """
    Convierte Kelvin a RGB usando colores calibrados manualmente para mejor UI.
    """
    kelvin = max(2200, min(6500, kelvin))

    # Definimos los puntos clave de color
    # 2200K: Naranja profundo
    c_2200 = (255, 147, 41)
    # 2700K: Blanco Cálido estándar
    c_2700 = (255, 197, 143)
    # 4000K: Blanco Neutro (casi puro)
    c_4000 = (255, 255, 255)
    # 6500K: Blanco Frío (Azulado Hielo) - Aumenté el azul aquí para ti
    c_6500 = (200, 230, 255) 

    if kelvin <= 2700:
        return interpolate_color(kelvin, 2200, 2700, c_2200, c_2700)
    elif kelvin <= 4000:
        return interpolate_color(kelvin, 2700, 4000, c_2700, c_4000)
    else:
        return interpolate_color(kelvin, 4000, 6500, c_4000, c_6500)

def get_scene_color(scene_id):
    """Colores visuales para representar escenas"""
    scenes = {
        1: (0, 100, 255),    # Océano
        2: (255, 100, 100),  # Romance
        3: (255, 140, 0),    # Atardecer
        4: (255, 0, 255),    # Fiesta
        5: (255, 69, 0),     # Chimenea
        6: (255, 200, 150),  # Acogedor
        7: (34, 139, 34),    # Bosque
        11: (255, 214, 170), # Warm White
        12: (255, 255, 255), # Daylight
        13: (200, 230, 255), # Cool White
        27: (255, 0, 0),     # Navidad
        28: (255, 100, 0),   # Halloween
    }
    return scenes.get(scene_id, (100, 100, 100)) 

class BulbState:
    def __init__(self, update_ui_callback):
        self.update_ui = update_ui_callback
        self.state = False
        self.dimming = 100
        self.r, self.g, self.b = 255, 255, 255
        self.temp = 2700
        self.sceneId = 0
        self.speed = 100
        self.mode = 'rgb' 

    def update(self, params):
        if "state" in params:
            self.state = params["state"]
        
        if "dimming" in params:
            self.dimming = params["dimming"]
        
        if "speed" in params:
            self.speed = params["speed"]

        if "sceneId" in params:
            self.sceneId = params["sceneId"]
            self.mode = 'scene'
            self.r, self.g, self.b = get_scene_color(self.sceneId)
            
        elif "temp" in params:
            self.temp = params["temp"]
            self.sceneId = 0
            self.mode = 'temp'
            self.r, self.g, self.b = kelvin_to_rgb(self.temp)
            
        elif "r" in params:
            self.r = params["r"]
            self.g = params["g"]
            self.b = params["b"]
            self.sceneId = 0
            self.mode = 'rgb'

        self.update_ui()

    def get_pilot(self):
        return {
            "method": "getPilot",
            "env": "pro",
            "result": {
                "mac": MOCK_MAC,
                "state": self.state,
                "sceneId": self.sceneId,
                "r": self.r,
                "g": self.g,
                "b": self.b,
                "dimming": self.dimming,
                "temp": self.temp,
                "speed": self.speed
            }
        }

class WizUDPServer(asyncio.DatagramProtocol):
    def __init__(self, bulb_state):
        self.bulb = bulb_state

    def connection_made(self, transport):
        self.transport = transport
        print(f"📡 Mock Bulb escuchando en {MOCK_IP}:{MOCK_PORT}")

    def datagram_received(self, data, addr):
        try:
            msg = json.loads(data.decode())
            method = msg.get("method")
            if method == "setPilot":
                self.bulb.update(msg.get("params", {}))
                resp = {"method": "setPilot", "result": {"success": True}}
                self.transport.sendto(json.dumps(resp).encode(), addr)
            elif method == "getPilot":
                self.transport.sendto(json.dumps(self.bulb.get_pilot()).encode(), addr)
            elif method == "registration" or method == "getSystemConfig":
                resp = {"result": {"mac": MOCK_MAC, "success": True}}
                self.transport.sendto(json.dumps(resp).encode(), addr)
        except Exception: pass

async def main(page: ft.Page):
    page.title = "Simulador WiZ - vColor"
    page.window_width = 320
    page.window_height = 550
    page.bgcolor = "#1a1a1a"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    bulb_visual = ft.Container(
        width=180, height=180, border_radius=90,
        bgcolor="black",
        shadow=ft.BoxShadow(blur_radius=30, color="#00000000"),
        animate=ft.Animation(300, "easeOut"),
    )

    status_text = ft.Text("OFF", size=30, weight="bold")
    mode_text = ft.Text("Esperando...", color="white", size=16)
    detail_text = ft.Text("...", size=12, color="grey")

    def update_visuals():
        if not bulb_state.state:
            bulb_visual.bgcolor = "#333333"
            bulb_visual.shadow.color = "transparent"
            status_text.value = "OFF"
            bulb_visual.opacity = 0.5
        else:
            r, g, b = bulb_state.r, bulb_state.g, bulb_state.b
            hex_c = f"#{r:02x}{g:02x}{b:02x}"
            
            bulb_visual.bgcolor = hex_c
            bulb_visual.shadow.color = hex_c
            bulb_visual.opacity = 0.4 + (0.6 * (bulb_state.dimming / 100))
            
            status_text.value = f"ON: {bulb_state.dimming}%"
            
            if bulb_state.mode == 'rgb':
                mode_text.value = "Color RGB"
                detail_text.value = f"R:{r} G:{g} B:{b}"
            elif bulb_state.mode == 'temp':
                mode_text.value = "Blancos (Temp)"
                detail_text.value = f"{bulb_state.temp}K"
            elif bulb_state.mode == 'scene':
                mode_text.value = f"Escena {bulb_state.sceneId}"
                detail_text.value = "Modo Efectos"

        page.update()

    bulb_state = BulbState(update_visuals)
    
    loop = asyncio.get_running_loop()
    try:
        await loop.create_datagram_endpoint(
            lambda: WizUDPServer(bulb_state),
            local_addr=(MOCK_IP, MOCK_PORT)
        )
    except OSError:
        status_text.value = "PUERTO OCUPADO"
        detail_text.value = "Cierra otras ventanas del simulador"
        return

    page.add(
        ft.Column([
            ft.Text("Simulador WiZ", size=24, weight="bold"),
            ft.Divider(height=20, color="transparent"),
            bulb_visual,
            ft.Divider(height=20, color="transparent"),
            status_text,
            mode_text,
            detail_text
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    ft.app(target=main)