from collections import defaultdict

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
import streamlit as st

from src.presentation.styles.theme import (
    SPATIAL_FIGURE_SIZE,
    SPATIAL_POPULATED_ZONE_COLOR,
    SPATIAL_UNPOPULATED_ZONE_COLOR,
    SPATIAL_EVENT_COLOR,
    SPATIAL_EVENT_MARKER_SIZE,
    SPATIAL_LABEL_FONT_SIZE,
)


def render_spatial_map(scenery):
    """Draw scenario zones and active event epicenters in the scenario X/Y plane."""
    zones = scenery.zones
    events = scenery.active_events.values()

    if not zones and not scenery.active_events:
        st.info("No hay zonas ni eventos para mostrar en el plano.")
        return

    fig, ax = plt.subplots(figsize=SPATIAL_FIGURE_SIZE)
    bounds = []

    for index, zone in enumerate(zones):
        x_min, x_max = zone.getXMin(), zone.getXMax()
        y_min, y_max = zone.getYMin(), zone.getYMax()
        populated = zone.getPopulated()
        color = SPATIAL_POPULATED_ZONE_COLOR if populated else SPATIAL_UNPOPULATED_ZONE_COLOR
        ax.add_patch(
            Rectangle(
                (x_min, y_min),
                x_max - x_min,
                y_max - y_min,
                facecolor=color,
                edgecolor=color,
                alpha=0.2,
                linewidth=1.5,
            )
        )
        ax.text(
            x_min + (x_max - x_min) * 0.02,
            y_max - (y_max - y_min) * 0.04,
            f"Zona {index + 1}",
            color=color,
            fontsize=SPATIAL_LABEL_FONT_SIZE,
            va="top",
        )
        bounds.extend(((x_min, y_min), (x_max, y_max)))

    # Group events by exact coordinate first: two events sitting on the
    # exact same point would otherwise draw two overlapping markers and
    # two fully-stacked labels. One merged label ("3, 7") is clearer than
    # two illegible ones, and it doesn't fake the point's true position.
    by_position = defaultdict(list)
    for event in events:
        epicenter = event.getEpicenter()
        by_position[(epicenter.getX(), epicenter.getY())].append(event.getEventId())

    if by_position:
        xs = [x for x, _ in by_position]
        ys = [y for _, y in by_position]
        bounds.extend(zip(xs, ys))
        ax.scatter(xs, ys, color=SPATIAL_EVENT_COLOR, marker=".", s=SPATIAL_EVENT_MARKER_SIZE, zorder=3)
        _place_labels(
            ax, fig,
            [(", ".join(str(i) for i in sorted(ids)), x, y) for (x, y), ids in by_position.items()],
            SPATIAL_LABEL_FONT_SIZE,
        )

    x_values, y_values = zip(*bounds)
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    x_padding = max((x_max - x_min) * 0.08, 1.0)
    y_padding = max((y_max - y_min) * 0.08, 1.0)
    ax.set_xlim(x_min - x_padding, x_max + x_padding)
    ax.set_ylim(y_min - y_padding, y_max + y_padding)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(
        handles=[
            Patch(facecolor=SPATIAL_POPULATED_ZONE_COLOR, edgecolor=SPATIAL_POPULATED_ZONE_COLOR,
                  alpha=0.35, label="Zona poblada"),
            Patch(facecolor=SPATIAL_UNPOPULATED_ZONE_COLOR, edgecolor=SPATIAL_UNPOPULATED_ZONE_COLOR,
                  alpha=0.35, label="Zona no poblada"),
            Line2D([], [], color=SPATIAL_EVENT_COLOR, marker=".", linestyle="None",
                   markersize=8, label="Epicentro"),
        ],
        loc="best",
        fontsize=SPATIAL_LABEL_FONT_SIZE,
    )
    ax.set_title("Zonas y epicentros del escenario", fontsize=10)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Se muestran los eventos activos. Las coordenadas X/Y son las del escenario; no son latitud/longitud. "
               "Los puntos con el mismo id combinado comparten exactamente el mismo epicentro.")


def _place_labels(ax, fig, points, font_size):
    """Dependency-free label decollision: draws every label at a small
    fixed offset, then - in display (pixel) space, where "too close"
    actually means something - nudges any label whose bounding box
    overlaps an earlier one further out until they stop overlapping or a
    small iteration budget runs out. Good enough for the handful of
    clustered points a scenario map typically has; not a general solver
    for dense point clouds.
    """
    if not points:
        return

    fig.canvas.draw()  # a renderer only exists after at least one draw
    renderer = fig.canvas.get_renderer()
    placed_boxes = []

    for label, x, y in points:
        annotation = ax.annotate(
            label, (x, y), xytext=(6, 6), textcoords="offset points",
            fontsize=font_size, zorder=4,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.8),
        )
        fig.canvas.draw()
        box = annotation.get_window_extent(renderer=renderer)

        offset_x, offset_y = 6, 6
        attempts = 0
        while any(box.overlaps(other) for other in placed_boxes) and attempts < 12:
            offset_y += 9
            if attempts % 3 == 2:   # every 3rd miss, also step sideways and reset the climb
                offset_x += 12
                offset_y = 6
            annotation.xyann = (offset_x, offset_y)
            fig.canvas.draw()
            box = annotation.get_window_extent(renderer=renderer)
            attempts += 1

        placed_boxes.append(box)
