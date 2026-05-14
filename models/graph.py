import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


class Graph:

    def __init__(self):
        self.vertices = []  # ordered list of all Vertex objects
        self._map = {}      # dict { IATA id -> Vertex } for fast lookup

    # Adds an airport node to the graph
    def add_vertex(self, vertex):
        self.vertices.append(vertex)
        self._map[vertex.id] = vertex

    # Returns the Vertex with the given IATA code, or None if not found
    def get_vertex(self, id):
        return self._map.get(id)

    # Prints all airports and their routes to the console (for debugging)
    def print_graph(self):
        hubs = sum(1 for v in self.vertices if v.is_hub)
        print(f"=== SkyRoute Network - {len(self.vertices)} airports ({hubs} hubs) ===\n")
        for v in self.vertices:
            type_str = "HUB" if v.is_hub else "sec"
            print(f"[{type_str}] {v.id} - {v.city}, {v.country}")
            for a in v.adjacencies:
                aircraft_str = ", ".join(a.aircraft)
                print(f"       -> {a.destination_vertex.id:4s}  {a.distance_km:>6.0f} km  [{aircraft_str}]")
        print()

    # Draws the air route network on screen using networkx and matplotlib
    def visualize(self):

        # Build a networkx directed graph (used only for drawing, not for logic)
        G = nx.DiGraph()

        # Add every airport as a node
        for v in self.vertices:
            G.add_node(v.id)

        # Add every route as an edge and build the label shown on it
        # Label format: "1900 km | C,R"  (C=Comercial  R=Regional  H=Helice)
        edge_labels = {}
        for v in self.vertices:
            for a in v.adjacencies:
                G.add_edge(v.id, a.destination_vertex.id)

                # Shorten each aircraft type to a single letter
                abbrevs = []
                for aircraft in a.aircraft:
                    if "Comercial" in aircraft or "Commercial" in aircraft:
                        abbrevs.append("C")
                    elif "Regional" in aircraft:
                        abbrevs.append("R")
                    else:
                        abbrevs.append("H")  # Helice/Propeller

                label = f"{int(a.distance_km)} km\n[{','.join(abbrevs)}]"
                edge_labels[(v.id, a.destination_vertex.id)] = label

        # Calculate node positions using spring layout
        pos = nx.spring_layout(G, seed=42, k=1.8)

        # Build per-node color and size lists in the same order as self.vertices
        node_list = [v.id for v in self.vertices]
        node_colors = ["#FF8C00" if v.is_hub else "#87CEEB" for v in self.vertices]  # orange=hub, blue=secondary
        node_sizes  = [1300     if v.is_hub else 700        for v in self.vertices]

        fig, ax = plt.subplots(figsize=(20, 14))
        ax.set_title("SkyRoute Planner - Latin American Air Network", fontsize=14, fontweight="bold")

        # Draw directed edges
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            arrows=True, arrowsize=12,
            edge_color="#aaaaaa",
            connectionstyle="arc3,rad=0.1",  # slight curve so bidirectional edges don't overlap
            width=0.8
        )

        # Draw all nodes in one call so that pick indices match node_list order
        nodes_coll = nx.draw_networkx_nodes(
            G, pos, ax=ax,
            nodelist=node_list,
            node_color=node_colors,
            node_size=node_sizes
        )
        nodes_coll.set_picker(10)  # 10-point click tolerance

        # Draw IATA code labels on top of each node
        nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_weight="bold")

        # Draw edge labels (distance + aircraft type)
        nx.draw_networkx_edge_labels(
            G, pos, ax=ax,
            edge_labels=edge_labels,
            font_size=5,
            label_pos=0.35,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", alpha=0.6)
        )

        # Legend: hub vs secondary
        hub_patch = mpatches.Patch(color="#FF8C00", label="Hub airport")
        sec_patch = mpatches.Patch(color="#87CEEB", label="Secondary airport")
        ax.legend(handles=[hub_patch, sec_patch], loc="upper left", fontsize=9)

        # Footer note explaining the aircraft abbreviations
        ax.text(0.01, 0.01, "Aircraft codes: C = Commercial   R = Regional   H = Propeller",
                transform=ax.transAxes, fontsize=8)

        # Hidden annotation box that appears when the user clicks a node
        annotation = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="lightyellow", ec="gray", alpha=0.95),
            arrowprops=dict(arrowstyle="->"),
            fontsize=8,
            visible=False
        )

        # Click handler: shows airport info when the user clicks near a node
        def on_click(event):
            if event.inaxes != ax:
                return

            # Find the nearest node to where the user clicked
            min_dist = float("inf")
            closest_id = None
            for node_id, (x, y) in pos.items():
                dist = (event.xdata - x) ** 2 + (event.ydata - y) ** 2
                if dist < min_dist:
                    min_dist = dist
                    closest_id = node_id

            # Only show the popup if the click was close enough to a node
            if min_dist < 0.03:
                v = self.get_vertex(closest_id)
                airlines_str = ", ".join(v.airlines) if v.airlines else "N/A"
                info = (
                    f"{v.id}  -  {v.name}\n"
                    f"City     : {v.city}, {v.country}\n"
                    f"Timezone : {v.timezone}\n"
                    f"Airlines : {airlines_str}"
                )
                annotation.set_text(info)
                annotation.xy = pos[closest_id]
                annotation.set_visible(True)
            else:
                # Hide the annotation when clicking on empty space
                annotation.set_visible(False)

            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("button_press_event", on_click)

        plt.tight_layout()
        plt.show()

    def __repr__(self):
        total_routes = sum(len(v.adjacencies) for v in self.vertices)
        return f"Graph({len(self.vertices)} airports, {total_routes} routes)"