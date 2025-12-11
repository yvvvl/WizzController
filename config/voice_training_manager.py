"""
Gestor de entrenamiento de voz.
Almacena frases de entrenamiento y patrones de corrección para mejorar el reconocimiento.
"""
import uuid
from .base_manager import JsonManager


class VoiceTrainingManager(JsonManager):
    """
    Gestiona:
    - Frases de entrenamiento grabadas por el usuario
    - Patrones de corrección (frase reconocida -> frase corregida)
    - Historial de reconocimiento (lo que se reconoce vs lo que se esperaba)
    - Estadísticas de uso
    """
    
    def __init__(self):
        super().__init__("voice_training.json", default_data={
            "training_phrases": [],  # Frases grabadas por el usuario
            "corrections": [],       # Patrones: {"recognized": "...", "corrected": "...", "count": N}
            "recognition_history": [],  # Historial de lo que se reconoce
            "stats": {
                "total_trained": 0,
                "total_corrections": 0,
                "total_recognized": 0
            }
        })

    # ==================== HISTORIAL DE RECONOCIMIENTO ====================
    
    def add_to_history(self, recognized: str, expected: str = None):
        """
        Registra lo que se reconoció. Útil para ver patrones de error.
        
        Args:
            recognized: Lo que el ASR reconoció
            expected: Lo que se esperaba (opcional)
        """
        if not recognized:
            return False
        
        recognized = recognized.strip().lower()
        
        # Buscar si ya existe en el historial
        for item in self.data.get("recognition_history", []):
            if item.get("recognized") == recognized:
                item["count"] = item.get("count", 1) + 1
                self.save()
                return True
        
        # Nuevo item en historial
        history_item = {
            "id": str(uuid.uuid4()),
            "recognized": recognized,
            "expected": expected.lower() if expected else None,
            "count": 1
        }
        
        if "recognition_history" not in self.data:
            self.data["recognition_history"] = []
        
        self.data["recognition_history"].append(history_item)
        self.data["stats"]["total_recognized"] = self.data["stats"].get("total_recognized", 0) + 1
        self.save()
        return True

    def get_recognition_history(self, limit: int = 20):
        """Obtiene el historial de reconocimiento, ordenado por frecuencia."""
        history = self.data.get("recognition_history", [])
        return sorted(history, key=lambda x: x.get("count", 0), reverse=True)[:limit]

    def get_top_misrecognitions(self, limit: int = 10):
        """Obtiene las palabras más frecuentemente reconocidas incorrectamente."""
        history = self.get_recognition_history(limit * 2)
        # Filtrar solo las que tienen "expected" diferente a "recognized"
        misrecognitions = [
            h for h in history 
            if h.get("expected") and h.get("recognized") != h.get("expected")
        ]
        return misrecognitions[:limit]

    def remove_from_history(self, item_id: str):
        """Elimina un item del historial."""
        self.data["recognition_history"] = [
            h for h in self.data.get("recognition_history", []) 
            if h.get("id") != item_id
        ]
        self.save()

    def clear_history(self):
        """Limpia el historial completo."""
        self.data["recognition_history"] = []
        self.save()

    # ==================== FRASES DE ENTRENAMIENTO ====================
    
    def add_training_phrase(self, phrase: str, category: str = "general"):
        """
        Añade una frase para entrenar el reconocedor.
        
        Args:
            phrase: La frase a entrenar (ej: "enciende la luz")
            category: Categoría para agrupar (ej: "general", "acciones", "colores")
        """
        if not phrase or not phrase.strip():
            return False
        
        phrase = phrase.strip().lower()
        
        # Evitar duplicados exactos
        for tp in self.data["training_phrases"]:
            if tp.get("text") == phrase:
                return False
        
        training_item = {
            "id": str(uuid.uuid4()),
            "text": phrase,
            "category": category,
            "count": 1  # Cuántas veces se usó
        }
        
        self.data["training_phrases"].append(training_item)
        self.data["stats"]["total_trained"] += 1
        self.save()
        return True

    def get_training_phrases(self, category: str = None):
        """Obtiene frases de entrenamiento, opcionalmente filtradas por categoría."""
        phrases = self.data.get("training_phrases", [])
        
        if category:
            return [p for p in phrases if p.get("category") == category]
        
        return phrases

    def remove_training_phrase(self, phrase_id: str):
        """Elimina una frase de entrenamiento."""
        self.data["training_phrases"] = [
            p for p in self.data["training_phrases"] if p.get("id") != phrase_id
        ]
        self.save()

    # ==================== CORRECCIONES ====================
    
    def add_correction(self, recognized: str, corrected: str):
        """
        Registra una corrección.
        Si el patrón ya existe, incrementa el contador.
        
        Args:
            recognized: Lo que el reconocedor capturó
            corrected: Lo que debería haber capturado
        """
        if not recognized or not corrected:
            return False
        
        recognized = recognized.strip().lower()
        corrected = corrected.strip().lower()
        
        if recognized == corrected:
            return False  # No es corrección
        
        # Buscar si el patrón ya existe
        for corr in self.data["corrections"]:
            if (corr.get("recognized") == recognized and 
                corr.get("corrected") == corrected):
                corr["count"] = corr.get("count", 1) + 1
                self.save()
                return True
        
        # Nuevo patrón
        new_correction = {
            "id": str(uuid.uuid4()),
            "recognized": recognized,
            "corrected": corrected,
            "count": 1
        }
        
        self.data["corrections"].append(new_correction)
        self.data["stats"]["total_corrections"] += 1
        self.save()
        return True

    def get_corrections(self):
        """Obtiene todas las correcciones."""
        return self.data.get("corrections", [])

    def get_top_corrections(self, limit: int = 10) -> list:
        """Obtiene las correcciones más frecuentes."""
        corrections = sorted(
            self.data.get("corrections", []),
            key=lambda x: x.get("count", 0),
            reverse=True
        )
        return corrections[:limit]

    def apply_correction(self, text: str) -> str:
        """
        Intenta aplicar una corrección si encuentra un patrón conocido.
        
        Args:
            text: El texto reconocido
            
        Returns:
            Texto corregido o el original si no hay patrón
        """
        text_lower = text.lower()
        
        # Buscar coincidencias exactas primero (más frecuentes)
        for corr in sorted(
            self.data.get("corrections", []),
            key=lambda x: x.get("count", 0),
            reverse=True
        ):
            recognized = corr.get("recognized", "").lower()
            corrected = corr.get("corrected", "")
            
            # Coincidencia exacta
            if recognized == text_lower:
                return corrected
            
            # Coincidencia parcial (la frase reconocida contiene el patrón)
            if recognized and recognized in text_lower:
                # Reemplazar el patrón conocido
                corrected_text = text_lower.replace(recognized, corrected)
                return corrected_text
        
        return text

    # ==================== ESTADÍSTICAS ====================
    
    def get_stats(self):
        """Obtiene estadísticas de entrenamiento."""
        return self.data.get("stats", {})

    def get_training_categories(self):
        """Obtiene todas las categorías de entrenamiento."""
        categories = set()
        for phrase in self.data.get("training_phrases", []):
            cat = phrase.get("category", "general")
            if cat:
                categories.add(cat)
        return sorted(list(categories))

    # ==================== FRASES DE ENTRENAMIENTO ====================
    
    def add_training_phrase(self, phrase: str, category: str = "general"):
        """
        Añade una frase para entrenar el reconocedor.
        
        Args:
            phrase: La frase a entrenar (ej: "enciende la luz")
            category: Categoría para agrupar (ej: "general", "acciones", "colores")
        """
        if not phrase or not phrase.strip():
            return False
        
        phrase = phrase.strip().lower()
        
        # Evitar duplicados exactos
        for tp in self.data["training_phrases"]:
            if tp.get("text") == phrase:
                return False
        
        training_item = {
            "id": str(uuid.uuid4()),
            "text": phrase,
            "category": category,
            "count": 1  # Cuántas veces se usó
        }
        
        self.data["training_phrases"].append(training_item)
        self.data["stats"]["total_trained"] += 1
        self.save()
        return True

    def get_training_phrases(self, category: str = None):
        """Obtiene frases de entrenamiento, opcionalmente filtradas por categoría."""
        phrases = self.data.get("training_phrases", [])
        
        if category:
            return [p for p in phrases if p.get("category") == category]
        
        return phrases

    def remove_training_phrase(self, phrase_id: str):
        """Elimina una frase de entrenamiento."""
        self.data["training_phrases"] = [
            p for p in self.data["training_phrases"] if p.get("id") != phrase_id
        ]
        self.save()

    # ==================== CORRECCIONES ====================
    
    def add_correction(self, recognized: str, corrected: str):
        """
        Registra una corrección.
        Si el patrón ya existe, incrementa el contador.
        
        Args:
            recognized: Lo que el reconocedor capturó
            corrected: Lo que debería haber capturado
        """
        if not recognized or not corrected:
            return False
        
        recognized = recognized.strip().lower()
        corrected = corrected.strip().lower()
        
        if recognized == corrected:
            return False  # No es corrección
        
        # Buscar si el patrón ya existe
        for corr in self.data["corrections"]:
            if (corr.get("recognized") == recognized and 
                corr.get("corrected") == corrected):
                corr["count"] = corr.get("count", 1) + 1
                self.save()
                return True
        
        # Nuevo patrón
        new_correction = {
            "id": str(uuid.uuid4()),
            "recognized": recognized,
            "corrected": corrected,
            "count": 1
        }
        
        self.data["corrections"].append(new_correction)
        self.data["stats"]["total_corrections"] += 1
        self.save()
        return True

    def get_corrections(self):
        """Obtiene todas las correcciones."""
        return self.data.get("corrections", [])

    def get_top_corrections(self, limit: int = 10):
        """Obtiene las correcciones más frecuentes."""
        corrections = sorted(
            self.data.get("corrections", []),
            key=lambda x: x.get("count", 0),
            reverse=True
        )
        return corrections[:limit]

    def apply_correction(self, text: str) -> str:
        """
        Intenta aplicar una corrección si encuentra un patrón conocido.
        
        Args:
            text: El texto reconocido
            
        Returns:
            Texto corregido o el original si no hay patrón
        """
        text_lower = text.lower()
        
        # Buscar coincidencias exactas primero (más frecuentes)
        for corr in sorted(
            self.data.get("corrections", []),
            key=lambda x: x.get("count", 0),
            reverse=True
        ):
            recognized = corr.get("recognized", "").lower()
            corrected = corr.get("corrected", "")
            
            # Coincidencia exacta
            if recognized == text_lower:
                return corrected
            
            # Coincidencia parcial (la frase reconocida contiene el patrón)
            if recognized and recognized in text_lower:
                # Reemplazar el patrón conocido
                corrected_text = text_lower.replace(recognized, corrected)
                return corrected_text
        
        return text

    # ==================== ESTADÍSTICAS ====================
    
    def get_stats(self):
        """Obtiene estadísticas de entrenamiento."""
        return self.data.get("stats", {})

    def get_training_categories(self):
        """Obtiene todas las categorías de entrenamiento."""
        categories = set()
        for phrase in self.data.get("training_phrases", []):
            cat = phrase.get("category", "general")
            if cat:
                categories.add(cat)
        return sorted(list(categories))
