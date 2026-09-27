class UndoStack:
    """Placeholder mínimo mientras el equipo define la representación real
    del historial de deshacer (ver decisiones de diseño abiertas). Solo
    existe para que Scenery pueda instanciarse y probarse — no implementa
    undo() todavía, solo registra qué pasó.

    Nadie más en el dump del proyecto define esta clase, así que
    Scenery.create_event no podía ni ejecutarse en pruebas sin esto.
    """

    def __init__(self):
        self._entries = []

    def push_creation(self, event_id):
        self._entries.append(("CREATION", event_id))

    def is_empty(self):
        return len(self._entries) == 0

    def peek(self):
        return self._entries[-1] if self._entries else None
