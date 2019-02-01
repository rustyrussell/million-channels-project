from graph_tool.all import *


def graph_tool(network, filename):
    nodes = network.fullConnNodes + network.partConnNodes
    g = Graph(directed=False)
    vs = []
    vDict = dict()
    i = 0
    es = []
    for node in nodes:
        v = g.add_vertex()
        vs += [v]
        vDict[node.nodeid] = v
        i += 1

    for channel in network.channels:
        node1 = channel.node1
        node2 = channel.node2
        es += [g.add_edge(vDict[node1.nodeid], vDict[node2.nodeid])]

    graph_draw(g, vertex_text=g.vertex_index, output=filename + ".png", output_size=(2000,2000))





