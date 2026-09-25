from dataclasses import dataclass


class IssueCategory:
    # Audit issue categories (Section 14).
    ORDER = "ORDER"  # Global K order property is broken
    UNIQUENESS = "UNIQUENESS"  # Duplicate event or cycle detected
    REFERENCE = "REFERENCE"  # Link points to non-existent or mismatched entity
    HEIGHT = "HEIGHT"  # Stored height does not match actual height
    BALANCE = (
        "BALANCE"  # Stored balance factor mismatch or out of bounds {-1,0,1}
    )
    EXPECTED_IMBALANCE = "EXPECTED_IMBALANCE"  # Expected imbalance in stress mode (not an error)


class Severity:
    ERROR = "ERROR"  # Violates AVL or BST structural properties
    INFO = "INFO"  # Informational warning, not a structural error


@dataclass
class AuditIssue:
    event_id: int
    category: str
    message: str
    severity: str = Severity.ERROR


class AuditReport:

    #Result of 'Verify Structure' operation (Section 14).
    #Generates a report per inconsistent event as required by the specification.
    #Allows querying tree height, nodes examined, and whether AVL property holds.

    def __init__(self, stress_mode: bool):
        self.stress_mode = stress_mode
        self.issues = []
        self.nodes_examined = 0
        self.tree_height = -1  # Height of an empty tree is -1 (Section 14)
        self.imbalanced_count = 0  # Number of nodes with |balance factor| > 1
        self.max_imbalance = 0  # Worst imbalance value found

    def add(self, event_id, category, message, severity=Severity.ERROR):
        self.issues.append(AuditIssue(event_id, category, message, severity))

    def errors(self) -> list:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    def notes(self) -> list:
        return [i for i in self.issues if i.severity == Severity.INFO]

    def errors_by_event(self) -> dict:
        """Groups errors by inconsistent event ID: {event_id: [AuditIssue, ...]}."""
        grouped = {}
        for issue in self.errors():
            grouped.setdefault(issue.event_id, []).append(issue)
        return grouped

    def has_errors(self) -> bool:
        return len(self.errors()) > 0

    @property
    def is_valid_avl(self) -> bool:
        #True only if there are no errors and no node has |balance factor| > 1.
        #This allows transitioning from stress mode back to normal mode (Section 8).
       
        return not self.has_errors() and self.imbalanced_count == 0

    def to_text(self) -> str:
        mode = "STRESS" if self.stress_mode else "NORMAL"
        lines = [
            f"Structure verification ({mode} mode): "
            f"{self.nodes_examined} nodes examined, height {self.tree_height}."
        ]
        if not self.has_errors():
            lines.append("No structural inconsistencies found.")
        for event_id, issues in self.errors_by_event().items():
            lines.append(f"Event {event_id}:")
            for issue in issues:
                lines.append(f"  [{issue.category}] {issue.message}")
        if self.imbalanced_count:
            lines.append(
                f"Imbalanced nodes: {self.imbalanced_count} "
                f"(max imbalance: {self.max_imbalance})."
            )
        lines.append(
            "AVL Property: "
            + ("SATISFIED" if self.is_valid_avl else "VIOLATED")
        )
        return "\n".join(lines)