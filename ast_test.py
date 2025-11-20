COUNTERS = {
    "assignments": 0,
    "indexing": 0,
    "function_calls": 0,
    "comparisons": 0,
    "arithmetic": 0
}

# ---- Counter Functions ----
def count_assign(value):
    COUNTERS["assignments"] += 1
    return value

def count_index(obj, key):
    COUNTERS["indexing"] += 1
    return obj[key]

def count_call(fn, *args, **kwargs):
    COUNTERS["function_calls"] += 1
    return fn(*args, **kwargs)

def count_compare(a, op, b):
    COUNTERS["comparisons"] += 1
    return op(a, b)

def count_arith(a, op, b):
    COUNTERS["arithmetic"] += 1
    return op(a, b)

import ast
import operator

# Creating a subclass of nodetransformer
class Instrumentor(ast.NodeTransformer):

    def visit_Assign(self, node):
        node = self.generic_visit(node)
        node.value = ast.Call(
            func=ast.Name(id="count_assign", ctx=ast.Load()),
            args=[node.value],
            keywords=[]
        )
        return node

    def visit_Subscript(self, node):
        node = self.generic_visit(node)

        if isinstance(node.ctx, ast.Store):
            # arr[i] = x — cannot transform
            return node
        
        return ast.Call(
            func=ast.Name(id="count_index", ctx=ast.Load()),
            args=[node.value, node.slice],
            keywords=[]
        )

    def visit_Call(self, node):
        node = self.generic_visit(node)
        return ast.Call(
            func=ast.Name(id="count_call", ctx=ast.Load()),
            args=[node.func] + node.args,
            keywords=[]
        )

    def visit_Compare(self, node):
        node = self.generic_visit(node)

        op_map = {
            ast.Lt: "lt",
            ast.Gt: "gt",
            ast.Eq: "eq",
            ast.NotEq: "ne",
            ast.LtE: "le",
            ast.GtE: "ge",
        }
        op = op_map[type(node.ops[0])]

        return ast.Call(
            func=ast.Name(id="count_compare", ctx=ast.Load()),
            args=[
                node.left,
                ast.Attribute(value=ast.Name(id="operator", ctx=ast.Load()), attr=op, ctx=ast.Load()),
                node.comparators[0],
            ],
            keywords=[]
        )

    def visit_BinOp(self, node):
        node = self.generic_visit(node)

        # arithmetic ops appear in Load OR Store context
        # identify context by walking up the tree – easiest safe rule:
        # only instrument if parent is not an Assign target
        if not isinstance(node.parent, ast.Assign):
            op_map = {
                ast.Add: "add",
                ast.Sub: "sub",
                ast.Mult: "mul",
                ast.Div: "truediv",
            }
            op = op_map.get(type(node.op))
            if op:
                return ast.Call(
                    func=ast.Name(id="count_arith", ctx=ast.Load()),
                    args=[
                        node.left,
                        ast.Attribute(value=ast.Name(id="operator", ctx=ast.Load()), attr=op, ctx=ast.Load()),
                        node.right,
                    ],
                    keywords=[]
                )
        return node


with open("bubble_sort.py", "r") as f:
    tree = ast.parse(f.read())

for child in ast.walk(tree):
    for sub in ast.iter_child_nodes(child):
        sub.parent = child

instrumented_tree = Instrumentor().visit(tree)
ast.fix_missing_locations(instrumented_tree)

code = compile(instrumented_tree, filename="<ast>", mode="exec")

# Used as id's to tie the functions to the Instrumentor class's methods
exec_globals = {
    "COUNTERS": COUNTERS,
    "count_assign": count_assign,
    "count_index": count_index,
    "count_call": count_call,
    "count_compare": count_compare,
    "count_arith": count_arith,
    "operator": operator
}

# Runs the compiled code and count the operations carried out during its runtime
exec(code, exec_globals)

# import random
# n = 10
# arr = [random.randint(1, 100) for _ in range(n)]
arr = [2, 5, 3, 1, 4]
# print(arr)
exec_globals["bubble_sort"](arr)

print(COUNTERS)
