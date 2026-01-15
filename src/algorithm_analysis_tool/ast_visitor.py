import ast
import operator

COUNTERS = {
    "assignments": 0,
    "indexing": 0,
    "function_calls": 0,
    "comparisons": 0,
    "arithmetic": 0
}

def count_arith(a, op, b):
    """
        Counts the arithmetic operations being performed \n.
        Increments the global arithmetic counter by 1.

        Parameters:
            a: The left_hand side of the statement.
            op: The operation being carried out, (add, mul etc..)
            b: The right_hand side of the statement.

        Returns:
            The result of applying the operation to (a, b)
    """
    COUNTERS["arithmetic"] += 1
    return op(a, b)

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

class AST_Visitor(ast.NodeTransformer):
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
    """
        This is a subclass build off of the NodeTransformer Class build into ast. \n
        NodeTransformer visits and allows the modification of nodes. \n
        We are changing its visit method for BinOps to instead of just visiting and executing them \n
        to also count how many we visit
    """
    def visit_BinOp(self, node):
        """
            NodeTransformer will auto call any visit_* methods we create. \n
            When we call visit(node) the transformer checks the node type and looks for a matching method
        """
        node = self.generic_visit(node)

        if not isinstance(node.parent, ast.Assign): # Check that the parent node isn't an assignment so we dont wrap within ourselves repeatedly
            op_map = {
                ast.Add: "add",
                ast.Sub: "sub",
                ast.Mult: "mul",
                ast.Div: "truediv"
            } # Note: Code doesn't currently cover %, ** or // operations
            op = op_map.get(type(node.op))
            if op:
                return ast.Call(
                    func=ast.Name(id="count_arith", ctx=ast.Load()),
                    args=[
                        node.left,
                        ast.Attribute(value=ast.Name(id="operator", ctx=ast.Load()), attr=op, ctx=ast.Load()), # This line maps to op in the count_arith func
                        node.right
                    ],
                    keywords=[]
                )
        return node