import ast

class FunctionDependencyVisitor(ast.NodeVisitor):
    def __init__(self, known_functions):
        self.known_functions = known_functions
        self.called = set()

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.known_functions:
                self.called.add(node.func.id)

        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.known_functions:
                self.called.add(node.func.attr)

        self.generic_visit(node)