from src.controllers.TreeSnapshot import flatten_tree, rebuild_tree, copy_event


def take_snapshot(scenery) -> dict:
    return {
        "tree": flatten_tree(scenery.tree.getRoot()),
        "active_events": {eid: copy_event(e) for eid, e in scenery.active_events.items()},
        "archived_events": {eid: copy_event(e) for eid, e in scenery.archived_events.items()},
        "eliminated_ids": set(scenery.eliminated_ids),
        "clock": scenery.simulation_clock.copy(),
        "parameters": scenery.parameters.copy(),
    }


def restore_snapshot(scenery, snapshot: dict) -> None:
    scenery.tree.setRoot(rebuild_tree(snapshot["tree"]))
    scenery.active_events = dict(snapshot["active_events"])
    scenery.archived_events = dict(snapshot["archived_events"])
    scenery.eliminated_ids = set(snapshot["eliminated_ids"])
    scenery.simulation_clock.restore(snapshot["clock"])
    scenery.parameters.restore(snapshot["parameters"])