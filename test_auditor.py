from src.controllers.TreeAuditor import TreeAuditor


# --- Clases MOCK para simular los Nodos, Claves y Eventos ---
class MockKey:

    def __init__(self, priority, magnitude, identifier):
        self.priority = priority
        self.magnitude = magnitude
        self.identifier = identifier

    @property
    def as_tuple(self):
        return (self.priority, self.magnitude, self.identifier)


class MockEvent:

    def __init__(self, event_id, priority, magnitude):
        self._id = event_id
        self._priority = priority
        self._magnitude = magnitude

    def getEventId(self):
        return self._id

    def getPriority(self):
        return self._priority

    def getMagnitude(self):
        return self._magnitude


class MockNode:

    def __init__(
        self, event_id, key, parent=None, left=None, right=None, h=0, bf=0
    ):
        self._id = event_id
        self._key = key
        self._parent = parent
        self._left = left
        self._right = right
        self._h = h
        self._bf = bf

    def getEventId(self):
        return self._id

    def getKey(self):
        return self._key

    def getParent(self):
        return self._parent

    def getLeft(self):
        return self._left

    def getRight(self):
        return self._right

    def getHeight(self):
        return self._h

    def getBalanceFactor(self):
        return self._bf


# --- CASOS DE PRUEBA ---
def run_tests():
    auditor = TreeAuditor()

    print("=== TEST 1: Árbol AVL Válido (Modo Normal) ===")
    # Construcción de un árbol válido: Raíz (ID 2), Izquierda (ID 1), Derecha (ID 3)
    k1 = MockKey(1, 5.0, 1)
    k2 = MockKey(2, 6.0, 2)
    k3 = MockKey(3, 7.0, 3)

    e1 = MockEvent(1, 1, 5.0)
    e2 = MockEvent(2, 2, 6.0)
    e3 = MockEvent(3, 3, 7.0)

    root = MockNode(2, k2, parent=None, h=1, bf=0)
    n1 = MockNode(1, k1, parent=root, h=0, bf=0)
    n3 = MockNode(3, k3, parent=root, h=0, bf=0)

    root._left = n1
    root._right = n3

    active_events = {1: e1, 2: e2, 3: e3}

    report = auditor.audit(root, active_events, stress_mode=False)
    print(report.to_text())
    assert (
        report.is_valid_avl
    ), "Error: El árbol válido debería retornar is_valid_avl = True"
    print("✔ TEST 1 PASADO CON ÉXITO\n")

    print("=== TEST 2: Árbol Desbalanceado en Modo Estrés ===")
    # Arbol desbalanceado (Cadena hacia la izquierda: 3 -> 2 -> 1)
    root2 = MockNode(3, k3, parent=None, h=2, bf=2)
    n2 = MockNode(2, k2, parent=root2, h=1, bf=1)
    n1_2 = MockNode(1, k1, parent=n2, h=0, bf=0)

    root2._left = n2
    n2._left = n1_2

    report_stress = auditor.audit(root2, active_events, stress_mode=True)
    print(report_stress.to_text())
    assert (
        not report_stress.has_errors()
    ), "Error: En Modo Estrés los desbalances son NOTAS, no errores fatales."
    assert (
        not report_stress.is_valid_avl
    ), "Error: is_valid_avl debe ser False porque hay desbalance."
    print("✔ TEST 2 PASADO CON ÉXITO\n")

    print("=== TEST 3: Detección de Error de Orden BST ===")
    # Forzar una violación de orden: el nodo izquierdo tiene clave mayor que la raíz
    root_bad = MockNode(1, k1, parent=None, h=1, bf=1)
    n3_bad = MockNode(
        3, k3, parent=root_bad, h=0, bf=0
    )  # Error: 3 a la izquierda de 1
    root_bad._left = n3_bad

    events_bad = {1: e1, 3: e3}

    report_bad = auditor.audit(root_bad, events_bad, stress_mode=False)
    print(report_bad.to_text())
    assert report_bad.has_errors(), "Error: Debería detectar el error de orden."
    assert any(
        issue.category == "ORDER" for issue in report_bad.errors()
    ), "Error: Debería registrar categoría ORDER."
    print("✔ TEST 3 PASADO CON ÉXITO\n")


if __name__ == "__main__":
    run_tests()