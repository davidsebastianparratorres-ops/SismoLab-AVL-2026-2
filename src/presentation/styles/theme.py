PAGE_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
}
[data-testid="stHeader"] {
    background: rgba(248, 250, 252, 0.86);
}
[data-testid="stMainBlockContainer"] {
    max-width: 1600px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #dbe4ee;
    border-radius: 14px;
}
button {
    border-radius: 9px !important;
    font-weight: 600 !important;
}
h1, h2, h3 {
    color: #1e293b;
}
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.8rem 1rem;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.35rem;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 9px 9px 0 0;
}
</style>
"""

# Tree drawing palette — kept here, not inside tree_view.py, so changing
# a color never means touching the drawing logic itself.
TREE_NORMAL_NODE_COLOR = "#679df3"
TREE_HIGHLIGHT_NODE_COLOR = "#ef4444"
TREE_UNBALANCED_NODE_COLOR = "#f59e0b"
TREE_EDGE_COLOR = "#94a3b8"
TREE_FONT_COLOR = "white"
TREE_NODE_SIZE = 1600
TREE_FIGURE_SIZE = (10, 6)


