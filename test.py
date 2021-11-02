from bs4 import BeautifulSoup
from difflib import SequenceMatcher

txt1 = '''<!DOCTYPE html>
<html>
<body>

<h1>My First Heading</h1>
<p>My first paragraph.</p>

</body>
</html>'''

txt2 = '''<!DOCTYPE html>
<html>
<body>

<h1>My First Heading</h1>
<table>
<tbody>
<tr>
<th>1st column</th>
<th>2nd column</th>
</tr>
<tr>
<td>Row 1, column 1</td>
<td>Row 1, column 2</td>
</tr>
<td>Row 2, column 1</td>
<td>Row 2, column 2</td>
</tbody>
</table>
</body>
</html>'''
# soup1, soup2 = BeautifulSoup(txt1, "html.parser"), BeautifulSoup(txt2, "html.parser")
# tags1, tags2 = [str(tag) for tag in soup1.find_all()], [str(tag) for tag in soup2.find_all()]
# print(SequenceMatcher(None, tags1, tags2).ratio())
#




from dijkstar import Graph, find_path

graph = Graph()
graph.add_edge('a', 'b', ('a', 'action1', 'b'))
graph.add_edge('b', 'c', ('b', 'action2', 'c'))
print(find_path(graph, 'a', 'c', cost_func=lambda a, b, c, d: 1).edges)
