# ── ITEM 2.1 — Graph structure (adjacency list + vertex map) + matplotlib visualization ──

import math
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


class Graph:
    # Directed weighted graph built from scratch

    def __init__(self):
        self.vertices = []          # List of all Vertex objects
        self._map = {}              # Fast lookup: IATA code -> Vertex
        self.aircraft_config = {}   # Aircraft speed/cost configuration
        self.global_config = {}     # Global configuration from JSON

    def add_vertex(self, vertex):
        # Add an airport node to the graph
        self.vertices.append(vertex)
        self._map[vertex.id] = vertex

    def get_vertex(self, id):
        # Look up an airport by its IATA code
        return self._map.get(id)

    def print_graph(self):
        # Print the full network: airports and their outgoing routes
        hubs = sum(1 for v in self.vertices if v.is_hub)
        print(f"=== SkyRoute Network - {len(self.vertices)} airports ({hubs} hubs) ===\n")
        for v in self.vertices:
            type_str = "HUB" if v.is_hub else "sec"
            print(f"[{type_str}] {v.id} - {v.city}, {v.country}")
            for a in v.adjacencies:
                aircraft_str = ", ".join(a.aircraft)
                print(f"       -> {a.destination_vertex.id:4s}  {a.distance_km:>6.0f} km  [{aircraft_str}]")
        print()

    # ── ITEM 2.2.c — Dijkstra's algorithm (weighted shortest path, custom weight_fn + edge_filter) ──

    def dijkstra(self, origin_id, destination_id, weight_func=None, edge_filter=None, criterion="distance"):
        # Dijkstra's algorithm: finds min-weight path in a directed graph
        # with non-negative edges
        if weight_func is None:
            weight_func = lambda e: e.getPeso()
        if edge_filter is None:
            edge_filter = lambda e: True

        # Get all vertex identifiers
        all_ids = [v.id for v in self.vertices]

        # Distance and predecessor tables
        dist = {v: math.inf for v in all_ids}
        pred = {v: None for v in all_ids}
        dist[origin_id] = 0

        unvisited = set(all_ids)

        # Quick lookup: id -> Vertex object
        vertex_map = {v.id: v for v in self.vertices}

        print("=== Initial iteration ===")
        for v in all_ids:
            print(f"{v}: ({'∞' if dist[v] == math.inf else dist[v]}, {pred[v]})")
        print()

        while unvisited:
            # Select the unvisited vertex with the smallest distance
            u = min(unvisited, key=lambda v: dist[v])
            if dist[u] == math.inf:
                break

            print(f"Processing vertex {u} with distance {dist[u]}")
            unvisited.remove(u)

            if u == destination_id:
                print(f"\nDestination {destination_id} reached. Search complete.\n")
                break

            # Relax edges using the Edge structure
            current_vertex = vertex_map[u]
            for edge in current_vertex.adjacencies:
                if not edge_filter(edge):
                    continue
                v = edge.destination_vertex.id
                if v in unvisited:
                    new_dist = dist[u] + weight_func(edge)
                    if new_dist < dist[v]:
                        dist[v] = new_dist
                        pred[v] = u
                        print(f"  Updated {v}: comes from {u}, new cost = {new_dist}")

            print("\nCurrent labels:")
            for v in all_ids:
                cost = "∞" if dist[v] == math.inf else dist[v]
                print(f"{v}: ({cost}, {pred[v]})")
            print()

        # Reconstruct the shortest path
        path = []
        current = destination_id
        while current is not None:
            path.insert(0, current)
            current = pred[current]

        print(f"Shortest path from {origin_id} to {destination_id}: {' → '.join(str(n) for n in path)}")
        print(f"Total {criterion}: {dist[destination_id]}")
        return dist, pred, path

    # ── END ITEM 2.2.c ──

    # ── ITEM 2.1 — matplotlib visualization: node layout, hub/secondary colors, click-to-info ──

    def visualize(self):
        # Render the network with matplotlib and NetworkX
        G = nx.DiGraph()

        for v in self.vertices:
            G.add_node(v.id)

        edge_labels = {}
        for v in self.vertices:
            for a in v.adjacencies:
                G.add_edge(v.id, a.destination_vertex.id)

                # Short aircraft codes: C=Commercial, R=Regional, H=Propeller
                abbrevs = []
                for aircraft in a.aircraft:
                    if "Comercial" in aircraft or "Commercial" in aircraft:
                        abbrevs.append("C")
                    elif "Regional" in aircraft:
                        abbrevs.append("R")
                    else:
                        abbrevs.append("H")

                label = f"{int(a.distance_km)} km\n[{','.join(abbrevs)}]"
                edge_labels[(v.id, a.destination_vertex.id)] = label

        pos = nx.spring_layout(G, seed=42, k=1.8)

        # Node styling: hub = orange, secondary = blue
        node_list = [v.id for v in self.vertices]
        node_colors = ["#FF8C00" if v.is_hub else "#87CEEB" for v in self.vertices]
        node_sizes  = [1300 if v.is_hub else 700 for v in self.vertices]

        fig, ax = plt.subplots(figsize=(20, 14))
        ax.set_title("SkyRoute Planner - Latin American Air Network", fontsize=14, fontweight="bold")

        nx.draw_networkx_edges(
            G, pos, ax=ax,
            arrows=True, arrowsize=12,
            edge_color="#aaaaaa",
            connectionstyle="arc3,rad=0.1",
            width=0.8
        )

        nodes_coll = nx.draw_networkx_nodes(
            G, pos, ax=ax,
            nodelist=node_list,
            node_color=node_colors,
            node_size=node_sizes
        )
        nodes_coll.set_picker(10)

        nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_weight="bold")

        nx.draw_networkx_edge_labels(
            G, pos, ax=ax,
            edge_labels=edge_labels,
            font_size=5,
            label_pos=0.35,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", alpha=0.6)
        )

        # Legend
        hub_patch = mpatches.Patch(color="#FF8C00", label="Hub airport")
        sec_patch = mpatches.Patch(color="#87CEEB", label="Secondary airport")
        ax.legend(handles=[hub_patch, sec_patch], loc="upper left", fontsize=9)

        ax.text(0.01, 0.01, "Aircraft codes: C = Commercial   R = Regional   H = Propeller",
                transform=ax.transAxes, fontsize=8)

        # Click annotation
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

        def on_click(event):
            # Show airport info when clicking a node on the matplotlib plot
            if event.inaxes != ax:
                return
            min_dist = float("inf")
            closest_id = None
            for node_id, (x, y) in pos.items():
                dist = (event.xdata - x) ** 2 + (event.ydata - y) ** 2
                if dist < min_dist:
                    min_dist = dist
                    closest_id = node_id
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
                annotation.set_visible(False)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("button_press_event", on_click)

        plt.tight_layout()
        plt.show()

    # ── END ITEM 2.1 (visualization) ──

    def __repr__(self):
        total_routes = sum(len(v.adjacencies) for v in self.vertices)
        return f"Graph({len(self.vertices)} airports, {total_routes} routes)"
