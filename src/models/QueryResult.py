from dataclasses import dataclass, field


class QueryResult:
    #Section 11.
    
        #events (list): List of matching event objects or summary entries.
        #nodes_examined (int): Total number of BST nodes visited during the query.
        # message (str): Status or summary message for console display.
        

    def __init__(self, events: list, nodes_examined: int, message: str = ""):
        self.events = events
        self.nodes_examined = nodes_examined
        self.message = message


@dataclass
class CostlyAccessEntry:
    #Represents a single query result entry for high-priority events with costly access.

        #event (object): The seismic Event instance.
        #node_depth (int): Zero-based depth of the node within the AVL tree.
        #search_cost (int): Total key comparison lookups needed (node_depth + 1).
    
    event: object
    node_depth: int
    search_cost: int


@dataclass
class AssociationsSummary:
    #Data structure summarizing reference relationships for a given event.

       #event (object): Target event being analyzed.
       # candidates (list): Candidate reference events evaluated by Section 7 rules.
       # chosen_reference (object): Selected primary reference event, or None.
       # referenced_by (list): Reverse index of other events that reference this event.
    
    event: object
    candidates: list = field(default_factory=list)
    chosen_reference: object = None
    referenced_by: list = field(default_factory=list)