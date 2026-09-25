from src.models.AuditReport import AuditReport, IssueCategory, Severity


class TreeAuditor:
    #Implements 'Verify Structure' (Section 14).

    #Operates in both normal mode and stress mode. All traversals use explicit
    #stacks rather than recursion because in stress mode the tree can degenerate
    #into a long chain of thousands of nodes, causing a RecursionError right when
    #auditing is needed most.

    #Complexity: O(n) time and O(n) auxiliary space (visited sets, traversal list,
    #height table). Only reads the tree without mutating it.
    

    def audit(
        self,
        root,
        active_events: dict,
        stress_mode: bool = False,
        archived_ids=None,
        eliminated_ids=None,
    ) -> AuditReport:
        
        #root:          root node of active tree (or None if empty).
        #active_events: {event_id: Event} catalog of active events.
        #stress_mode:   if True, |balance factor| > 1 is recorded as info notice, not error.
        #archived_ids / eliminated_ids: sets of IDs that MUST NOT be active.
        
        report = AuditReport(stress_mode)
        archived_ids = archived_ids or set()
        eliminated_ids = eliminated_ids or set()

        traversal, seen_ids = self._traverse_and_check_order(root, report)
        self._check_nodes_against_events(traversal, active_events, report)
        self._check_catalog(
            active_events, seen_ids, archived_ids, eliminated_ids, report
        )
        self._check_heights_and_balance(root, traversal, stress_mode, report)
        return report

    
    # Items 1 & 2: Traversal with explicit stack. Checks global order & uniqueness.
    def _traverse_and_check_order(self, root, report):
        traversal = []  # Nodes in preorder traversal (parent before children)
        visited_nodes = set()  # id(node): detects shared nodes or cycles
        seen_ids = set()

        if root is None:
            return traversal, seen_ids

        # Each stack entry contains: (node, expected_parent, lower_bound, upper_bound).
        # Bounds represent the key (tuple) of the nearest ancestor enforcing
        # "greater than" / "less than", inherited from ALL ancestors, not just immediate parent.
        stack = [(root, None, None, None)]

        while stack:
            node, expected_parent, lower_bound, upper_bound = stack.pop()
            report.nodes_examined += 1
            event_id = node.getEventId()

            if id(node) in visited_nodes:
                report.add(
                    event_id,
                    IssueCategory.UNIQUENESS,
                    "Este nodo es alcanzable desde más de una posición (nodo compartido o ciclo)."
                )
                continue  # Do not traverse deeper: prevents infinite loops in cycles
            visited_nodes.add(id(node))

            if event_id in seen_ids:
                report.add(
                    event_id,
                    IssueCategory.UNIQUENESS,
                    "Este identificador de evento aparece en más de un nodo del árbol."
                )
            seen_ids.add(event_id)
            traversal.append(node)

            if node.getParent() is not expected_parent:
                expected_str = (
                    "None (root)"
                    if expected_parent is None
                    else str(expected_parent.getEventId())
                )
                report.add(
                    event_id,
                    IssueCategory.REFERENCE,
                    f"El enlace al padre está mal: debería apuntar a {expected_str}.",
                )

            key_tuple = node.getKey().as_tuple
            if lower_bound is not None and key_tuple <= lower_bound:
                report.add(
                    event_id,
                    IssueCategory.ORDER,
                    f"La clave {key_tuple} debería ser mayor que{lower_bound}.",
                )
            if upper_bound is not None and key_tuple >= upper_bound:
                report.add(
                    event_id,
                    IssueCategory.ORDER,
                    f"La clave {key_tuple} deberia ser menor que {upper_bound}.",
                )

            right_child, left_child = node.getRight(), node.getLeft()
            if right_child is not None:
                stack.append((right_child, node, key_tuple, upper_bound))
            if left_child is not None:
                stack.append((left_child, node, lower_bound, key_tuple))

        return traversal, seen_ids

   
    # Item 3: Validate each node against the event it represents.
    def _check_nodes_against_events(self, traversal, active_events, report):
        for node in traversal:
            event_id = node.getEventId()
            event = active_events.get(event_id)
            if event is None:
                report.add(
                    event_id,
                    IssueCategory.REFERENCE,
                    "El nodo apunta a un evento que no está en el catálogo activo."
                )
                continue

            key = node.getKey()
            if key.identifier != event_id:
                report.add(
                    event_id,
                    IssueCategory.REFERENCE,
                    f"El identificador de la clave ({key.identifier}) no coincide con el evento del nodo ({event_id})."
                )
            if key.priority != event.getPriority():
                report.add(
                    event_id,
                    IssueCategory.REFERENCE,
                    f"La prioridad de la clave ({key.priority}) no coincide con la del evento ({event.getPriority()})."
                )
            if key.magnitude != event.getMagnitude():
                report.add(
                    event_id,
                    IssueCategory.REFERENCE,
                    f"La magnitud de la clave ({key.magnitude}) no coincide con la del evento ({event.getMagnitude()})."
                )

    
    # Validate Catalog against Tree: identities must match one-to-one.
    def _check_catalog(
        self, active_events, seen_ids, archived_ids, eliminated_ids, report
    ):
        for event_id, event in active_events.items():
            if event.getEventId() != event_id:
                report.add(
                    event_id,
                    IssueCategory.REFERENCE,
                    f"La llave del catálogo ({event_id}) no coincide con el id propio del evento  ({event.getEventId()}).",
                )
            if event_id not in seen_ids:
                report.add(
                    event_id,
                    IssueCategory.REFERENCE,
                    "Evento activo que no tiene ningún nodo en el árbol."
                )
            if event_id in archived_ids:
                report.add(
                    event_id,
                    IssueCategory.UNIQUENESS,
                    "El identificador está activo y archivado a la vez."
                )
            if event_id in eliminated_ids:
                report.add(
                    event_id,
                    IssueCategory.UNIQUENESS,
                    "El identificador está activo y eliminado a la vez."
                )

    
    # Item 4: Recalculate heights and balance factors from bottom to top.
    def _check_heights_and_balance(self, root, traversal, stress_mode, report):
        # Traversal is in preorder (parent before children). By iterating in REVERSE,
        # every child is processed before its parent, allowing bottom-up calculation
        # of heights without recursion.
        heights = {}

        def get_child_height(child):
            return -1 if child is None else heights.get(id(child), -1)

        for node in reversed(traversal):
            event_id = node.getEventId()
            left_h = get_child_height(node.getLeft())
            right_h = get_child_height(node.getRight())
            actual_h = 1 + max(left_h, right_h)
            actual_bf = left_h - right_h
            heights[id(node)] = actual_h

            if node.getHeight() is None:
                report.add(
                    event_id, IssueCategory.HEIGHT, "El nodo no tiene una altura guardada."
                )
            elif node.getHeight() != actual_h:
                report.add(
                    event_id,
                    IssueCategory.HEIGHT,
                    f"Altura guardada ({node.getHeight()}) pero la altura real es ({actual_h}).",
                )

            if node.getBalanceFactor() is None:
                report.add(
                    event_id,
                    IssueCategory.BALANCE,
                    "El nodo no tiene factor de balance guardado"
                )
            elif node.getBalanceFactor() != actual_bf:
                report.add(
                    event_id,
                    IssueCategory.BALANCE,
                    f"Factor de balance guardado ({node.getBalanceFactor()}) pero el real es ({actual_bf}).",
                )

            if abs(actual_bf) > 1:
                report.imbalanced_count += 1
                report.max_imbalance = max(
                    report.max_imbalance, abs(actual_bf)
                )
                if stress_mode:
                    report.add(
                        event_id,
                        IssueCategory.EXPECTED_IMBALANCE,
                        f"El factor de balance {actual_bf} supera los límites de AVL (esperado durante el modo de estrés).",
                        Severity.INFO  
                    )
                else:
                    report.add(
                        event_id,
                        IssueCategory.BALANCE,
                        f"Factor de balance {actual_bf} se sale de {{-1, 0, 1}} en el modo normal.",
                    )

        report.tree_height = -1 if root is None else heights.get(id(root), -1)