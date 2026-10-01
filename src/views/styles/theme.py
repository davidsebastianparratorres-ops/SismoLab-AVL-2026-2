PAGE_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background-color: #f5f7fb;
}
button {
    background-color: #e2e8f0 !important;
    color: black !important;
    border-radius: 8px !important;
    height: 38px;
    font-weight: 500;
}
h1, h2, h3 {
    color: #1e293b;
}
</style>
"""

# Tree drawing palette — kept here, not inside tree_view.py, so changing
# a color never means touching the drawing logic itself.
TREE_NORMAL_NODE_COLOR = "#679df3"
TREE_HIGHLIGHT_NODE_COLOR = "#ef4444"
TREE_EDGE_COLOR = "#94a3b8"
TREE_FONT_COLOR = "white"
TREE_NODE_SIZE = 1600
TREE_FIGURE_SIZE = (10, 6)