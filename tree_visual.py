import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.widgets import Button
import time
import threading
from collections import deque

# -----------------------
# Node and tree builder
# -----------------------
class Node:
    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None

def build_tree(values):
    """Build binary tree from level-order list of strings.
       Use 'None' (case-sensitive) to represent missing nodes."""
    if not values or values[0] == "None":
        return None
    root = Node(values[0])
    q = deque([root])
    i = 1
    while q and i < len(values):
        node = q.popleft()
        # left
        if i < len(values) and values[i] != "None":
            node.left = Node(values[i])
            q.append(node.left)
        i += 1
        # right
        if i < len(values) and values[i] != "None":
            node.right = Node(values[i])
            q.append(node.right)
        i += 1
    return root

# -----------------------
# Generate inorder steps
# -----------------------
# Each step: (action_str, node_obj, stack_snapshot_keys, result_snapshot_keys)
steps = []

def generate_inorder_steps(root):
    steps.clear()
    stack_nodes = []
    result_nodes = []
    def inorder(node):
        if node:
            # push
            steps.append(("push", node, [n.key for n in stack_nodes], [r.key for r in result_nodes]))
            stack_nodes.append(node)
            inorder(node.left)
            # visit
            steps.append(("visit", node, [n.key for n in stack_nodes], [r.key for r in result_nodes]))
            result_nodes.append(node)
            inorder(node.right)
            # pop
            steps.append(("pop", node, [n.key for n in stack_nodes], [r.key for r in result_nodes]))
            stack_nodes.pop()
    inorder(root)

# -----------------------
# User input
# -----------------------
values = input("Enter nodes in level order (use 'None' for empty): ").split()
root = build_tree(values)
if root is None:
    print("Empty tree. Exiting.")
    exit()

generate_inorder_steps(root)

# -----------------------
# Build networkx graph with Node objects
# -----------------------
edges = []
def add_edges(node):
    if node:
        if node.left:
            edges.append((node, node.left))
            add_edges(node.left)
        if node.right:
            edges.append((node, node.right))
            add_edges(node.right)
add_edges(root)

G = nx.DiGraph()
G.add_edges_from(edges)

# -----------------------
# Compute positions (inorder-based x, depth-based y)
# -----------------------
pos = {}
_counter = [0]
def set_positions_by_inorder(node, depth=0):
    if node is None:
        return
    set_positions_by_inorder(node.left, depth+1)
    pos[node] = (_counter[0], -depth)
    _counter[0] += 1
    set_positions_by_inorder(node.right, depth+1)

set_positions_by_inorder(root)

# center horizontally so tree sits near center
xs = [xy[0] for xy in pos.values()] if pos else [0]
min_x, max_x = min(xs), max(xs)
mid = (min_x + max_x) / 2.0
for n in list(pos.keys()):
    x, y = pos[n]
    pos[n] = (x - mid, y)

labels = {n: str(n.key) for n in G.nodes()}

# -----------------------
# Figure & UI setup
# -----------------------
fig, ax = plt.subplots(figsize=(10, 6))
plt.subplots_adjust(bottom=0.28)
ax.set_axis_off()

# Text content variables (will be drawn in axes coords, so always visible)
stack_text_val = "Stack: []"
result_text_val = "Result: []"
status_text_val = "Ready"
inorder_text_val = "Inorder: []"
final_text_val = ""

# Control and runtime variables
current_step = [0]        # index into steps
is_playing = [False]
play_speed = [1.0]        # toggle between 1.0 and 0.5
visited_nodes = set()     # Node objects that have been visited (for green color)
live_result = []          # list of keys in order visited (strings)

# -----------------------
# Drawing helpers
# -----------------------
def draw_tree(current_node_obj=None):
    """Redraw tree and top-left texts. Uses ax.transAxes so texts are always inside view."""
    ax.clear()
    ax.set_axis_off()

    # Choose colors: current -> orange, visited -> lightgreen, else skyblue
    node_colors = []
    for n in G.nodes():
        if current_node_obj is not None and n is current_node_obj:
            node_colors.append("orange")
        elif n in visited_nodes:
            node_colors.append("lightgreen")
        else:
            node_colors.append("skyblue")

    nx.draw(G, pos, labels=labels, with_labels=True, node_size=1000,
            node_color=node_colors, font_weight="bold", ax=ax)

    # Draw status texts in top-left using axes coordinates (0..1)
    # x ~ 0.01 left margin, y descending from 0.95
    ax.text(0.01, 0.95, stack_text_val, transform=ax.transAxes, fontsize=10, va="top", ha="left")
    ax.text(0.01, 0.88, result_text_val, transform=ax.transAxes, fontsize=10, va="top", ha="left")
    ax.text(0.01, 0.81, status_text_val, transform=ax.transAxes, fontsize=11, va="top", ha="left")
    ax.text(0.01, 0.74, inorder_text_val, transform=ax.transAxes, fontsize=11, va="top", ha="left")
    ax.text(0.01, 0.67, final_text_val, transform=ax.transAxes, fontsize=11, va="top", ha="left", color="green")

    fig.canvas.draw_idle()

def update_display(i):
    """Update variables for step i and redraw."""
    global stack_text_val, result_text_val, status_text_val, inorder_text_val, final_text_val

    if i < 0 or i >= len(steps):
        return

    action, node_obj, stack_snapshot, result_snapshot = steps[i]

    # Clear & set the short, clear status messages
    status_text_val = f"{action.capitalize()} {node_obj.key}"
    stack_text_val = "Stack: " + str(stack_snapshot)
    result_text_val = "Result: " + str(result_snapshot)

    # On visit, mark visited and append live_result
    if action == "visit":
        visited_nodes.add(node_obj)
        live_result.append(node_obj.key)

    inorder_text_val = "Inorder: " + " ".join(map(str, live_result))

    if i == len(steps) - 1:
        final_text_val = "Final Inorder Result: " + " ".join(map(str, live_result))

    # redraw with highlight on current node
    draw_tree(current_node_obj=node_obj)

# -----------------------
# Play loop for automatic stepping
# -----------------------
def play_loop():
    while is_playing[0] and current_step[0] < len(steps):
        update_display(current_step[0])
        current_step[0] += 1
        time.sleep(play_speed[0])
    is_playing[0] = False

# -----------------------
# Button callbacks
# -----------------------
def next_step(event):
    if current_step[0] < len(steps):
        update_display(current_step[0])
        current_step[0] += 1

def play(event):
    if not is_playing[0]:
        is_playing[0] = True
        t = threading.Thread(target=play_loop, daemon=True)
        t.start()

def pause(event):
    is_playing[0] = False

def reset(event):
    is_playing[0] = False
    current_step[0] = 0
    visited_nodes.clear()
    live_result.clear()
    # reset displayed texts
    nonlocal_defaults = {
        'stack_text_val': "Stack: []",
        'result_text_val': "Result: []",
        'status_text_val': "Ready",
        'inorder_text_val': "Inorder: []",
        'final_text_val': ""
    }
    # Assign back to globals
    globals()['stack_text_val'] = nonlocal_defaults['stack_text_val']
    globals()['result_text_val'] = nonlocal_defaults['result_text_val']
    globals()['status_text_val'] = nonlocal_defaults['status_text_val']
    globals()['inorder_text_val'] = nonlocal_defaults['inorder_text_val']
    globals()['final_text_val'] = nonlocal_defaults['final_text_val']
    draw_tree(None)

def toggle_speed(event):
    if play_speed[0] == 1.0:
        play_speed[0] = 0.5
        b_speed.label.set_text("Speed: 0.5x")
    else:
        play_speed[0] = 1.0
        b_speed.label.set_text("Speed: 1x")

# -----------------------
# Create Buttons
# -----------------------
ax_next = plt.axes([0.10, 0.05, 0.12, 0.075])
ax_play = plt.axes([0.26, 0.05, 0.12, 0.075])
ax_pause = plt.axes([0.42, 0.05, 0.12, 0.075])
ax_reset = plt.axes([0.58, 0.05, 0.12, 0.075])
ax_speed = plt.axes([0.75, 0.05, 0.18, 0.075])

b_next = Button(ax_next, "Next")
b_next.on_clicked(next_step)

b_play = Button(ax_play, "Play")
b_play.on_clicked(play)

b_pause = Button(ax_pause, "Pause")
b_pause.on_clicked(pause)

b_reset = Button(ax_reset, "Reset")
b_reset.on_clicked(reset)

b_speed = Button(ax_speed, "Speed: 1x")
b_speed.on_clicked(toggle_speed)

# -----------------------
# Initial draw & show
# -----------------------
draw_tree(None)
plt.show()
