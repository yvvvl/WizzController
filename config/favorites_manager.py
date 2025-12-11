import uuid
from .base_manager import JsonManager

class FavoritesManager(JsonManager):
    """
    Gestor CRUD reimaginado para Favoritos.
    Simple, directo y sin lógica de estado. Solo guarda datos.
    """
    def __init__(self):
        # Estructura: id, name, type (rgb/white/scene), value, icon
        super().__init__("favorites.json", default_data=[])

    def get_favorites(self):
        return self.data if isinstance(self.data, list) else []

    def add_favorite(self, name, ftype, value, icon="STAR"):
        """
        Agrega un favorito y retorna el objeto creado.
        """
        new_fav = {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": ftype,   # 'rgb', 'white', 'scene'
            "value": value,  # Hex string o int Kelvin
            "icon": icon
        }
        
        if not isinstance(self.data, list): self.data = []
        self.data.append(new_fav)
        self.save()
        print(f"[Favorites] Agregado: {name} ({value})")
        return new_fav

    def remove_favorite(self, uid):
        initial_len = len(self.data)
        self.data = [f for f in self.data if f.get("id") != uid]
        if len(self.data) < initial_len:
            self.save()
            return True
        return False