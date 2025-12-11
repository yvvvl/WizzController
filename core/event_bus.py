from __future__ import annotations
from collections import defaultdict
from threading import Lock
from typing import Callable, Dict, List, Any

EventCallback = Callable[[str, Any], None]


class EventBus:
    """
    Pub/Sub súper simple y thread-safe.

    - UI, hotkeys y voz publican y escuchan eventos.
    - Nada se conoce directamente, sólo se comunican por event_type + payload.
    """

    def __init__(self) -> None:
        self._subs: Dict[str, List[EventCallback]] = defaultdict(list)
        self._lock = Lock()

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        """Registra un callback para un tipo de evento."""
        with self._lock:
            self._subs[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        """Elimina un callback para un tipo de evento."""
        with self._lock:
            if event_type in self._subs and callback in self._subs[event_type]:
                self._subs[event_type].remove(callback)

    def emit(self, event_type: str, payload: Any = None) -> None:
        """
        Lanza un evento a todos los suscriptores de ese tipo.
        Se hace copia local de la lista para no bloquear.
        """
        with self._lock:
            callbacks = list(self._subs.get(event_type, []))

        for cb in callbacks:
            try:
                cb(event_type, payload)
            except Exception as e:
                print(f"[EventBus] Error en '{event_type}': {e}")
