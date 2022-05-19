from dijkstar import Graph, find_path

graph = Graph()
graph.add_edge('s0', 's3', ('s0', 'a2', 's3'))
graph.add_edge('s0', 's1', ('s0', 'a1', 's1'))
graph.add_edge('s1', 's3', ('s1', 'a2', 's3'))
graph.add_edge('s3', 's0', ('s3', 'a1', 's0'))
graph.add_edge('s1', 's4', ('s1', 'a1', 's4'))

shortest_path_edges = find_path(graph, 's0', 's4', cost_func=lambda a, b, c, d: 1).edges
print('edges', shortest_path_edges)
print(list(map(lambda t: t[1], shortest_path_edges)))