import ast

with open("bubble_sort.py", "r", encoding="utf-8") as ast_tree_walker:
    tree = ast.parse(ast_tree_walker.read())

arr = []
counter = 0

for node in ast.walk(tree):
    print(node)
    if isinstance(node, ast.FunctionDef) and counter == 0:
        # ast.Assign
        # ast.Compare
        # ast.Index
        # ast.alias
        arr.append(node.__dict__["name"])
        counter = 1
    print(node.__dict__)