class UndoStack:
    """Placeholder mÃ­nimo mientras el equipo define la representaciÃ³n real
    del historial de deshacer (ver decisiones de diseÃ±o abiertas). Solo
    existe para que Scenery pueda instanciarse y probarse â€” no implementa
    undo() todavÃ­a, solo registra quÃ© pasÃ³.

    Nadie mÃ¡s en el dump del proyecto define esta clase, asÃ­ que
    Scenery.create_event no podÃ­a ni ejecutarse en pruebas sin esto.
    """

    def __init__(self):
        self._entries = []

    def push_creation(self, event_id):
        self._entries.append(("CREATION", event_id))

    def is_empty(self):
        return len(self._entries) == 0

    def peek(self):
        return self._entries[-1] if self._entries else None
