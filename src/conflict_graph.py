"""conflict_graph.py - Builds the Distance-2 conflict graph G^2 from the original graph G."""
import networkx as nx


def build_conflict_graph(G):
    """
    G^2 has an edge between two nodes when their hop distance in G is 1 or 2.
      - 1-hop: direct link (direct link interference)
      - 2-hop: a common neighbor (hidden terminal problem)
    Every node of G, including isolated ones, is present in G^2.
    """
    C = nx.Graph()
    C.add_nodes_from(G.nodes())
    for u in G.nodes():
        for v in G.neighbors(u):
            C.add_edge(u, v)              # 1-hop conflict
            for w in G.neighbors(v):
                if w != u:
                    C.add_edge(u, w)      # 2-hop conflict (u and w are both neighbors of v)
    return C
