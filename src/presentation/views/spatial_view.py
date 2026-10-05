import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
import streamlit as st


def render_spatial_map(scenery):
    """Draw scenario zones and active event epicenters in the scenario X/Y plane."""
    zones = scenery.zones
    events = scenery.active_events.values()

    if not zones and not scenery.active_events:
        st.info("No hay zonas ni eventos para mostrar en el plano.")
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    bounds = []

    for index, zone in enumerate(zones):
        x_min, x_max = zone.getXMin(), zone.getXMax()
        y_min, y_max = zone.getYMin(), zone.getYMax()
        populated = zone.getPopulated()
        color = "#f4a261" if populated else "#457b9d"
        ax.add_patch(
            Rectangle(
                (x_min, y_min),
                x_max - x_min,
                y_max - y_min,
                facecolor=color,
                edgecolor=color,
                alpha=0.2,
                linewidth=1.8,
            )
        )
        ax.text(
            x_min,
            y_max,
            f"Zona {index + 1}",
            color=color,
            fontsize=8,
            va="bottom",
        )
        bounds.extend(((x_min, y_min), (x_max, y_max)))

    event_points = []
    for event in events:
        epicenter = event.getEpicenter()
        x, y = epicenter.getX(), epicenter.getY()
        event_points.append((event.getEventId(), x, y))
        bounds.append((x, y))

    if event_points:
        xs = [x for _, x, _ in event_points]
        ys = [y for _, _, y in event_points]
        ax.scatter(xs, ys, color="#d62828", marker=".", s=110, zorder=3)
        for event_id, x, y in event_points:
            ax.annotate(str(event_id), (x, y), xytext=(5, 5), textcoords="offset points", fontsize=8)

    x_values, y_values = zip(*bounds)
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    x_padding = max((x_max - x_min) * 0.05, 1.0)
    y_padding = max((y_max - y_min) * 0.05, 1.0)
    ax.set_xlim(x_min - x_padding, x_max + x_padding)
    ax.set_ylim(y_min - y_padding, y_max + y_padding)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle=":", alpha=0.45)
    ax.legend(
        handles=[
            Patch(facecolor="#f4a261", edgecolor="#f4a261", alpha=0.35, label="Zona poblada"),
            Patch(facecolor="#457b9d", edgecolor="#457b9d", alpha=0.35, label="Zona no poblada"),
            Line2D([], [], color="#d62828", marker=".", linestyle="None", markersize=10, label="Epicentro"),
        ],
        loc="best",
    )
    ax.set_title("Zonas y epicentros del escenario")
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)
    st.caption("Se muestran los eventos activos. Las coordenadas X/Y son las del escenario; no son latitud/longitud.")
