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
class EventDetail:
    #Full lookup of a single event: current data, where it lives, its
    #position in the AVL (active events only), and its associations.

        #event (object): The event itself (current/vigente data).
        #location_status (str): EventStatus.ACTIVE or EventStatus.ARCHIVED.
        #key (tuple): (priority, magnitude, identifier) - the same tuple used
        #    to order and locate the event in the tree.
        #node_depth / node_height / balance_factor: None for archived events,
        #    since archived events are removed from the active AVL.
        #associations (AssociationsSummary): candidates, chosen reference,
        #    and who references this event back.

    event: object
    location_status: str
    key: tuple
    node_depth: object
    node_height: object
    balance_factor: object
    associations: "AssociationsSummary"


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
