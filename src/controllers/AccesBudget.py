def is_expensive_access(event, node_depth, depth_limit):
    # Section 9: only priority-3 (high priority) events can carry this mark
    # BUG FIX: was event.priority, which doesn't exist on Event (private
    # attribute, only exposed via getPriority()).
    return event.getPriority() == 3 and node_depth > depth_limit


def find_expensive_access_events(catalog, tree):
    node_depths = tree.get_all_depths()  # dict[event_id, depth]

    result = []
    for event_id, event in catalog.active_events.items():
        depth = node_depths.get(event_id)
        if depth is not None and is_expensive_access(event, depth, catalog.access_depth_limit):
            result.append((event, depth))
    return result
