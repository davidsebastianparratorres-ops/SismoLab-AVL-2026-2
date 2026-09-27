"""
Prueba de verify_structure() SIN depender de la clase Scenery completa
(porque create_event todavia no inserta en el arbol). Simulamos a mano
un objeto con los mismos atributos que usaria Scenery real, para
confirmar que la logica de conexion con TreeAuditor funciona.
"""
from src.models.Node import Node
from src.models.Key import Key
from src.models.Event import Event
from src.controllers.TreeAuditor import TreeAuditor


class FalsoArbol:
    """Solo para la prueba: simula tree.getRoot()."""
    def __init__(self, root):
        self._root = root
    def getRoot(self):
        return self._root


def verify_structure(scenery_like, stress_mode=False):
    # Esta es la MISMA logica que va dentro de Scenery.verify_structure
    active_by_id = {event.getEventId(): event for event in scenery_like.active_events}
    archived_ids = {event.getEventId() for event in scenery_like.archived_events}
    return TreeAuditor().audit(
        scenery_like.tree.getRoot(),
        active_by_id,
        stress_mode=stress_mode,
        archived_ids=archived_ids,
        eliminated_ids=scenery_like.eliminated_ids,
    )


class FalsoScenery:
    def __init__(self, tree, active_events, archived_events, eliminated_ids):
        self.tree = tree
        self.active_events = active_events
        self.archived_events = archived_events
        self.eliminated_ids = eliminated_ids


# Armamos un arbol de 3 nodos correctamente balanceado
raiz = Node(Key(2, 5.0, 10), 10); raiz.setHeight(1); raiz.setBalanceFactor(0)
izq = Node(Key(1, 3.0, 5), 5); izq.setHeight(0); izq.setBalanceFactor(0)
der = Node(Key(3, 6.5, 20), 20); der.setHeight(0); der.setBalanceFactor(0)
raiz.setLeft(izq); izq.setParent(raiz)
raiz.setRight(der); der.setParent(raiz)

e10 = Event(event_id=10, magnitude=5.0, priority=2)
e5 = Event(event_id=5, magnitude=3.0, priority=1)
e20 = Event(event_id=20, magnitude=6.5, priority=3)

print("=== Caso A: todo bien ===")
falso = FalsoScenery(FalsoArbol(raiz), [e10, e5, e20], [], set())
print(verify_structure(falso).to_text())

print("\n=== Caso B: el evento 20 tambien esta marcado como archivado (inconsistencia) ===")
falso_b = FalsoScenery(FalsoArbol(raiz), [e10, e5, e20], [e20], set())
print(verify_structure(falso_b).to_text())

print("\n=== Caso C: arbol vacio (escenario recien creado) ===")
falso_c = FalsoScenery(FalsoArbol(None), [], [], set())
print(verify_structure(falso_c).to_text())