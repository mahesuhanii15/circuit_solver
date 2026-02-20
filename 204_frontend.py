import tkinter as tk
from tkinter import simpledialog

GRID_SIZE = 20


def snap(val: int) -> int:
    return (val // GRID_SIZE) * GRID_SIZE


# ---------------- DISJOINT SET ----------------

class DisjointSet:
    def __init__(self):
        self.parent = {}
        self.rank={}

    def add(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x]=0
        
        
    def find(self, x):
        if x not in self.parent:
            self.add(x)

        visited = []
        while self.parent[x] != x:
            if x in visited:
                # cycle detected – break it by making this node a root
                break
            visited.append(x)
            x = self.parent[x]

        root = x
        # Path compression
        for v in visited:
            self.parent[v] = root

        return root


    def union(self, a, b):
        root_a = self.find(a)
        root_b = self.find(b)

        if root_a == root_b:
            return

        # Union by rank (PREVENTS CYCLES)
        if self.rank[root_a] < self.rank[root_b]:
            self.parent[root_a] = root_b
        elif self.rank[root_a] > self.rank[root_b]:
            self.parent[root_b] = root_a
        else:
            self.parent[root_b] = root_a
            self.rank[root_a] += 1


def rename_columns_with_dsu(components, connections):
    dsu = DisjointSet()

    # ADD ALL nodes from components FIRST
    for comp in components:
        dsu.add(comp[1])
        dsu.add(comp[2])

    for a, b in connections:
        dsu.add(a)
        dsu.add(b)
        dsu.union(a, b)

    ground_root = None
    if "Ground" in dsu.parent:
        ground_root = dsu.find("Ground")
    
    if ground_root is not None:
        for node in list(dsu.parent.keys()):
            if dsu.find(node) == ground_root:
                dsu.parent[node] = "Ground"
        dsu.parent["Ground"] = "Ground"
        

    mapping = {}
    counter = 1

    for node in dsu.parent:
        root = dsu.find(node)
        if root not in mapping:
            if root == "Ground":
                mapping[root] = 0
            else:
                mapping[root] = counter
                counter += 1

    final = []
    for comp in components:
        n1 = dsu.find(comp[1])
        n2 = dsu.find(comp[2])

        comp[1] = str(mapping[n1])
        comp[2] = str(mapping[n2])
        final.append(comp)

    return final


# ---------------- CIRCUIT CORE ----------------

class Component:
    def __init__(self, name, ctype, x, y, value=None):
        self.name = name           # e.g. R1
        self.ctype = ctype         # 'resistor', 'capacitor', ..
        self.x = x                 # center x
        self.y = y                 # center y
        self.value = value
        self.rotation = 0          # 0/90/180/270
        self.terminals = {}        # term_name -> (x,y)
        self.items = set()         # canvas IDs
        self.value_item = None     # canvas ID of value text (for editing)


class CircuitGraph:
    def __init__(self):
        self.components = []
        self.connections = []  # list of (terminal_name, terminal_name)

    def add_component(self, comp: Component):
        self.components.append(comp)

    def remove_component(self, comp: Component):
        if comp in self.components:
            self.components.remove(comp)

    def add_connection(self, t1, t2):
        self.connections.append((t1, t2))

    def generate_netlist(self):
        netlist = []
        for comp in self.components:
            if comp.ctype == "ground":
                continue
            terms = list(comp.terminals.keys())
            if len(terms) < 2:
                continue
            n1, n2 = terms[0], terms[1]
            netlist.append([comp.name, n1, n2, comp.value])
        return rename_columns_with_dsu(netlist, self.connections)


# ---------------- GUI ----------------

class CircuitGUI(tk.Tk):

    COMPONENT_CONFIG = {
        "resistor": "R",
        "capacitor": "C",
        "inductor": "L",
        "voltage_source": "V",
        "current_source": "I",
        "ground": "G",
    }

    def __init__(self):
        super().__init__()
        self.title("GSpice – Schematic Editor")
        self.geometry("1100x750")

        # Toolbar
        self.toolbar = tk.Frame(self, bg="#333")
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        for comp in self.COMPONENT_CONFIG:
            tk.Button(
                self.toolbar,
                text=comp.capitalize(),
                command=lambda c=comp: self.select_component(c),
            ).pack(side=tk.LEFT, padx=2)

        tk.Button(self.toolbar, text="Wire", command=self.toggle_wire).pack(side=tk.LEFT, padx=5)
        tk.Button(self.toolbar, text="Delete", command=self.toggle_delete).pack(side=tk.LEFT, padx=5)
        tk.Button(self.toolbar, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=5)
        tk.Button(self.toolbar, text="Simulate", command=self.simulate).pack(side=tk.RIGHT, padx=10)

        self.status_label = tk.Label(
            self.toolbar,
            text="Wiring Mode: OFF",
            fg="white",
            bg="#444",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=3,
        )
        self.status_label.pack(side=tk.LEFT, padx=20)

        # Canvas
        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.focus_set() 

        self.draw_grid()

        # State
        self.graph = CircuitGraph()
        self.component_counter = 1

        self.selected_tool = None      # 'resistor', 'wire', etc.
        self.wire_mode = False
        self.delete_mode = False

        self.nodes = {}                # term_name -> (x,y)
        self.wires = []                # list of dicts {t1,t2,l1,l2}
        self.history = []              # stack: ('add_component', comp) / ('add_wire', wire_dict)

        self.selected_component_obj = None
        self.drag_info = None
        self.pending_terminals = []    # for wiring; 2 entries then connect

        # Bindings
        self.canvas.bind("<Button-1>", self.canvas_left_click)
        self.bind("<r>", self.rotate_selected)

        # Hint
        self.canvas.create_text(
            220,
            15,
            text="Hint: Click component, then press 'R' to rotate",
            fill="gray",
        )

    # ---------------- Basic UI helpers ----------------

    def draw_grid(self):
        for x in range(0, 2000, GRID_SIZE):
            self.canvas.create_line(x, 0, x, 2000, fill="#eee")
        for y in range(0, 2000, GRID_SIZE):
            self.canvas.create_line(0, y, 2000, y, fill="#eee")

    def set_status(self):
        if self.wire_mode:
            self.status_label.config(text="Wiring Mode: ON", bg="green")
        else:
            self.status_label.config(text="Wiring Mode: OFF", bg="#444")

    def select_component(self, comp_type: str):
        self.selected_tool = comp_type
        self.wire_mode = False
        self.delete_mode = False
        self.set_status()

    def toggle_wire(self):
        self.wire_mode = not self.wire_mode
        self.selected_tool = None
        self.delete_mode = False
        self.set_status()

    def toggle_delete(self):
        self.delete_mode = not self.delete_mode
        self.wire_mode = False
        self.selected_tool = None
        self.set_status()

    # ---------------- Mouse handlers ----------------

    def canvas_left_click(self, event):
        if self.delete_mode:
            self.handle_delete_click(event)
            return

        if self.wire_mode:
            # In wire mode, clicking is handled by terminal bindings, not canvas
            return
        item = self.canvas.find_withtag("current")
        if item:
            comp = self.find_component_by_item(item[0])
            if comp:
                return  

        if self.selected_tool is None:
            return

        self.place_component(event)

    # ---------------- Component placement ----------------

    def place_component(self, event):
        x = snap(event.x)
        y = snap(event.y)

        ctype = self.selected_tool
        prefix = self.COMPONENT_CONFIG[ctype]
        comp_name = f"{prefix}{self.component_counter}"
        self.component_counter += 1

        if ctype == "ground":
            value = None
            comp = Component(comp_name, "ground", x, y, value)
        else:
            value = simpledialog.askstring("Value", f"Enter {ctype} value:")
            if value is None:
                return
            comp = Component(comp_name, ctype, x, y, value)

        # compute terminals & draw
        self.build_terminals(comp)
        self.draw_component(comp)

        self.graph.add_component(comp)
        self.history.append(("add_component", comp))

    def build_terminals(self, comp: Component):
        """Compute terminal coordinates based on comp.x, comp.y, comp.rotation."""
        comp.terminals.clear()
        if comp.ctype == "ground":
            comp.terminals["Ground"] = (comp.x, comp.y)
        else:
            if comp.rotation in (0, 180):  # horizontal
                comp.terminals[f"{comp.name}.n1"] = (comp.x - 40, comp.y)
                comp.terminals[f"{comp.name}.n2"] = (comp.x + 40, comp.y)
            else:  # vertical
                comp.terminals[f"{comp.name}.n1"] = (comp.x, comp.y - 40)
                comp.terminals[f"{comp.name}.n2"] = (comp.x, comp.y + 40)

        for tname, pos in comp.terminals.items():
            self.nodes[tname] = pos

    def draw_component(self, comp: Component):
        """Draw component body, name, value, terminals."""
        # Remove any old items (for rotations/redraws)
        for item_id in comp.items:
            self.canvas.delete(item_id)
        comp.items.clear()

        # Body: simple rectangle representing component
        if comp.rotation in (0, 180):
            body = self.canvas.create_rectangle(
                comp.x - 30,
                comp.y - 10,
                comp.x + 30,
                comp.y + 10,
                fill="white",
                outline="black",
                tags=(comp.name,),
            )
        else:
            body = self.canvas.create_rectangle(
                comp.x - 10,
                comp.y - 30,
                comp.x + 10,
                comp.y + 30,
                fill="white",
                outline="black",
                tags=(comp.name,),
            )

        comp.items.add(body)

        # Name above
        name_id = self.canvas.create_text(
            comp.x,
            comp.y - 20,
            text=comp.name,
            tags=(comp.name,),
        )
        comp.items.add(name_id)

        # Value below
        if comp.value is not None:
            val_id = self.canvas.create_text(
                comp.x,
                comp.y + 20,
                text=str(comp.value),
                fill="blue",
                tags=(comp.name,),
            )
            comp.items.add(val_id)
            comp.value_item = val_id
        else:
            comp.value_item = None

        # Terminals
        for tname, (tx, ty) in comp.terminals.items():
            dot = self.canvas.create_oval(
                tx - 3,
                ty - 3,
                tx + 3,
                ty + 3,
                fill="black",
                tags=(tname, comp.name),
            )

            hitbox = self.canvas.create_oval(
                tx-6, ty-6,
                tx+6, ty+6,
                outline="",
                fill="",
                tags=(tname, comp.name)
                )
    
            label = self.canvas.create_text(
                tx,
                ty - 10,
                text=tname,
                fill="gray",
                tags=(comp.name,),
            )
            comp.items.add(dot)
            comp.items.add(label)

            # Clicking a terminal in wire mode
            self.canvas.tag_bind(
                tname,
                "<Button-1>",
                lambda e, term_name=tname: self.terminal_clicked(term_name),
            )

        # Bind dragging & right-click to component tag
        self.canvas.tag_bind(comp.name, "<ButtonPress-1>", self.start_drag)
        self.canvas.tag_bind(comp.name, "<B1-Motion>", self.drag_motion)
        self.canvas.tag_bind(comp.name, "<ButtonRelease-1>", self.stop_drag)
        self.canvas.tag_bind(comp.name, "<Button-3>", self.edit_component_value)

    # ---------------- Wiring ----------------
    def terminal_clicked(self, term_name: str):
        if not self.wire_mode:
            return
        
        # First click → select starting node
        if len(self.pending_terminals) == 0:
            self.pending_terminals = [term_name]
            print("Wire start:", term_name)
            return
        
        # Second click → connect
        t1 = self.pending_terminals[0]
        t2 = term_name

        # Prevent self-loop
        if t1 == t2:
            print("Ignored: same node clicked twice")
            self.pending_terminals.clear()
            return
        
        # Make sure nodes still exist
        if t1 not in self.nodes or t2 not in self.nodes:
            self.pending_terminals.clear()
            return
        
        x1, y1 = self.nodes[t1]
        x2, y2 = self.nodes[t2]
        
        # 90-degree routing
        mid_x, mid_y = x2, y1
        
        l1 = self.canvas.create_line(x1, y1, mid_x, mid_y, width=2)
        l2 = self.canvas.create_line(mid_x, mid_y, x2, y2, width=2)
        
        wire = {"t1": t1, "t2": t2, "l1": l1, "l2": l2}
        self.wires.append(wire)
        self.graph.add_connection(t1, t2)
        self.history.append(("add_wire", wire))

        print(f"Wire connected: {t1} → {t2}")

        self.pending_terminals.clear()


    # ---------------- Dragging ----------------

    def find_component_by_item(self, item_id):
        for comp in self.graph.components:
            if item_id in comp.items:
                return comp
        return None

    def start_drag(self, event):
        if self.wire_mode or self.delete_mode:
            return

        self.drag_info = (event.x, event.y)
        current = self.canvas.find_withtag("current")
        if not current:
            return

        comp = self.find_component_by_item(current[0])
        if comp:
            self.selected_component_obj = comp
            print("Selected:", comp.name)

    def drag_motion(self, event):
        if not self.selected_component_obj or not self.drag_info:
            return

        dx = event.x - self.drag_info[0]
        dy = event.y - self.drag_info[1]
        comp = self.selected_component_obj

        # Move all component items
        for item_id in comp.items:
            self.canvas.move(item_id, dx, dy)

        # Update center
        comp.x += dx
        comp.y += dy

        # Update terminal positions
        for tname in comp.terminals.keys():
            x, y = self.nodes[tname]
            self.nodes[tname] = (x + dx, y + dy)
            comp.terminals[tname] = (x + dx, y + dy)

        # Update wires connected to this component
        self.update_all_wires()

        self.drag_info = (event.x, event.y)

    def stop_drag(self, event):
        self.drag_info = None
        # keep selected_component_obj so R can rotate last clicked

    # ---------------- Rotation ----------------

    def rotate_selected(self, event=None):

        print("Rotate pressed")


        comp = self.selected_component_obj
        if not comp:
            print("No Component selected!")
            return
        
        print("Rotating:", comp.name)

        if comp.ctype == "ground":
            return  # ignore ground rotation

        # 90° step
        comp.rotation = (comp.rotation + 90) % 360

        # Rebuild terminals from center & redraw
        self.build_terminals(comp)
        self.draw_component(comp)
        self.update_all_wires()

    def update_all_wires(self):
        for wire in self.wires:
            t1 = wire["t1"]
            t2 = wire["t2"]
            if t1 not in self.nodes or t2 not in self.nodes:
                continue
            x1, y1 = self.nodes[t1]
            x2, y2 = self.nodes[t2]
            mid_x, mid_y = x2, y1
            self.canvas.coords(wire["l1"], x1, y1, mid_x, mid_y)
            self.canvas.coords(wire["l2"], mid_x, mid_y, x2, y2)

    # ---------------- Delete & Undo ----------------

    def handle_delete_click(self, event):
        current = self.canvas.find_withtag("current")
        if not current:
            return
        comp = self.find_component_by_item(current[0])
        if not comp:
            return

        # Delete its wires too
        terms = set(comp.terminals.keys())
        remaining_wires = []
        for wire in self.wires:
            if wire["t1"] in terms or wire["t2"] in terms:
                self.canvas.delete(wire["l1"])
                self.canvas.delete(wire["l2"])
            else:
                remaining_wires.append(wire)
        self.wires = remaining_wires

        # Delete component items
        for item_id in comp.items:
            self.canvas.delete(item_id)
        comp.items.clear()

        # Remove its terminals from nodes
        for tname in terms:
            if tname in self.nodes:
                del self.nodes[tname]

        self.graph.remove_component(comp)
        self.history.append(("delete_component", comp))

    def undo(self):
        if not self.history:
            return
        action, obj = self.history.pop()

        if action == "add_component":
            comp = obj
            for item_id in comp.items:
                self.canvas.delete(item_id)
            comp.items.clear()
            for tname in list(comp.terminals.keys()):
                if tname in self.nodes:
                    del self.nodes[tname]
            self.graph.remove_component(comp)

        elif action == "add_wire":
            wire = obj
            self.canvas.delete(wire["l1"])
            self.canvas.delete(wire["l2"])
            # remove from list
            self.wires = [w for w in self.wires if w is not wire]

        elif action == "delete_component":
            comp = obj
            # Rebuild terminals + draw component again
            self.build_terminals(comp)
            self.draw_component(comp)
            self.graph.add_component(comp)

    # ---------------- Value editing ----------------

    def edit_component_value(self, event):
        if self.wire_mode:
            return

        current = self.canvas.find_withtag("current")
        if not current:
            return
        comp = self.find_component_by_item(current[0])
        if not comp or comp.value is None:
            return

        new_val = simpledialog.askstring(
            "Edit Value",
            f"Enter new value for {comp.name}:",
            initialvalue=str(comp.value),
        )
        if new_val is None:
            return

        comp.value = new_val
        if comp.value_item:
            self.canvas.itemconfig(comp.value_item, text=str(new_val))

    # ---------------- Simulation ----------------

    def simulate(self):
        netlist = self.graph.generate_netlist()
        with open("output.txt", "w") as f:
            for line in netlist:
                f.write(" ".join(str(x) for x in line) + "\n")
        print("✅ Netlist written to output.txt")


# ---------------- RUN ----------------

if __name__ == "__main__":
    app = CircuitGUI()
    app.mainloop()
