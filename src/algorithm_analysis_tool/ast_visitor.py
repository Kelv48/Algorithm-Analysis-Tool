import ast

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
    """
        Counts the assignment operations being performed \n.
        Increments the global assignment counter by 1.

        Parameters:
            value: The value being assigned.

        Returns:
            The value being assigned.
    """
    COUNTERS["assignments"] += 1
    return value

def count_index(obj, key):
    """
        Counts the indexing operations being performed \n.
        Increments the global indexing counter by 1.

        Parameters:
            obj: The object being indexed.
            key: The index/key being accessed.

        Returns:
            The value at the specified index/key.
    """
    COUNTERS["indexing"] += 1
    return obj[key]

def count_call(fn, *args, **kwargs):
    """
        Counts the function call operations being performed \n.
        Increments the global function call counter by 1.

        Parameters:
            fn: The function being called.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function call.
    """
    COUNTERS["function_calls"] += 1
    return fn(*args, **kwargs)

def count_compare(a, op, b):
    """
        Counts the comparison operations being performed \n.
        Increments the global comparison counter by 1.

        Parameters:
            a: The left-hand side of the comparison.
            op: The comparison operation (e.g., lt, gt).
            b: The right-hand side of the comparison.

        Returns:
            The result of the comparison.
    """
    COUNTERS["comparisons"] += 1
    return op(a, b)

class ASTVisitor(ast.NodeTransformer):
    
    """
    NodeTransformer will auto call any visit_* methods we create. \n
    When we call visit(node) the transformer checks the node type and looks for a matching method
    """    
    def visit_Assign(self, node):
        """
            Visit assignment nodes to wrap the assigned value with a call to count_assign."""
        node = self.generic_visit(node)
        node.value = ast.Call(
            func=ast.Name(id="count_assign", ctx=ast.Load()),
            args=[node.value],
            keywords=[]
        )
        return node

    def visit_Subscript(self, node):
        """
            Visits subscript (indexing) nodes to wrap them with a call to count_index.
        """
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
        """
            Visits function call nodes to wrap them with a call to count_call.
        """
        node = self.generic_visit(node)
        return ast.Call(
            func=ast.Name(id="count_call", ctx=ast.Load()),
            args=[node.func] + node.args,
            keywords=[]
        )

    def visit_Compare(self, node):
        """
            Visits comparison nodes to wrap them with a call to count_compare.
        """
        node = self.generic_visit(node)

        op_map = {
            ast.Lt: "lt",
            ast.Gt: "gt",
            ast.Eq: "eq",
            ast.NotEq: "ne",
            ast.LtE: "le",
            ast.GtE: "ge",
        }
        op = op_map.get(type(node.ops[0]))
        if not op:
            # Unsupported comparison operator; leave node unchanged.
            return node

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
        """
            Visits binary operation nodes to wrap them with a call to count_arith.
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