from src.controllers.TreeSnapshot import flatten_tree, rebuild_tree, copy_event


def take_snapshot(scenery) -> dict:
    return {
        "tree": flatten_tree(scenery.tree.getRoot()),
        "active_events": {eid: copy_event(e) for eid, e in scenery.active_events.items()},
        "archived_events": {eid: copy_event(e) for eid, e in scenery.archived_events.items()},
        "eliminated_ids": set(scenery.eliminated_ids),
        "clock": scenery.simulation_clock.copy(),
        "parameters": scenery.parameters.copy(),
        "associations": scenery.association_manager.to_dict(),
        "metrics": scenery.metrics.copy(),
        "stress_mode": scenery.stress_mode,
        "queue": scenery.queue.copy(),
        # Zones and stations never change while running, but a scenario load
        # replaces them, so an undo of that load must be able to bring them back.
        # They are references on purpose: nothing mutates them in place.
        "zones": scenery.zones,
        "stations": scenery.stations,
    }


def restore_snapshot(scenery, snapshot: dict) -> None:
    scenery.tree.setRoot(rebuild_tree(snapshot["tree"]))
    scenery.active_events = dict(snapshot["active_events"])
    scenery.archived_events = dict(snapshot["archived_events"])
    scenery.eliminated_ids = set(snapshot["eliminated_ids"])
    scenery.simulation_clock.restore(snapshot["clock"])
    scenery.parameters.restore(snapshot["parameters"])
    scenery.association_manager.restore_from(snapshot["associations"])
    scenery.metrics.restore(snapshot["metrics"])
    scenery.stress_mode = snapshot["stress_mode"]
    scenery.queue.restore(snapshot["queue"])
    scenery.zones = snapshot["zones"]
    scenery.stations = snapshot["stations"]



