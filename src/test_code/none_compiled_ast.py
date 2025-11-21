import ast
import operator

class Instrumentor(ast.NodeTransformer):
    def visit_Call(self, node):
        node = self.generic_visit(node)
        return ast.Call(
            func=ast.Name(id="count_call", ctx=ast.Load()),
            args=[node.func] + node.args,
            keywords=[]
        )

with open("hello_world.py", "r") as f:
    tree = ast.parse(f.read())

for child in ast.walk(tree):
    for sub in ast.iter_child_nodes(child):
        sub.parent = child

instrumented_tree = Instrumentor().visit(tree)
ast.fix_missing_locations(instrumented_tree)

code = compile(instrumented_tree, filename="<ast>", mode="exec")