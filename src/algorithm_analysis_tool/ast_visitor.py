import ast
import operator


# Add in for and while loop counting
COUNTERS = {
    "assignments": 0,
    "indexing": 0,
    "function_calls": 0,
    "returns": 0,
    "comparisons": 0,
    "arithmetic": 0,
    "loop_nodes": 0,
    "loop_iterations": 0
}

def reset_counters(counters):
    counters = {
        "assignments": 0,
        "indexing": 0,
        "function_calls": 0,
        "returns": 0,
        "comparisons": 0,
        "arithmetic": 0,
        "loop_nodes": 0,
        "loop_iterations": 0
    }
    return counters

def count_loop_iteration(counters):
    """
        Counts the loop iterations being performed \n.
        Increments the global loop iteration counter by 1.
    """
    counters["loop_iterations"] += 1


def count_arith(counters, a, op, b):
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
    counters["arithmetic"] += 1
    return op(a, b)

def count_assign(counters, value):
    """
        Counts the assignment operations being performed \n.
        Increments the global assignment counter by 1.

        Parameters:
            value: The value being assigned.

        Returns:
            The value being assigned.
    """
    counters["assignments"] += 1
    return value

def count_index(counters, obj, key):
    """
        Counts the indexing operations being performed \n.
        Increments the global indexing counter by 1.

        Parameters:
            obj: The object being indexed.
            key: The index/key being accessed.

        Returns:
            The value at the specified index/key.
    """
    counters["indexing"] += 1
    return obj[key]

def count_call(counters, fn, *args, **kwargs):
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
    counters["function_calls"] += 1
    counters["returns"] += 1
    return fn(*args, **kwargs)

def count_compare(counters, a, op, b):
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
    counters["comparisons"] += 1
    return op(a, b)

class ASTVisitor(ast.NodeTransformer):
    """
    NodeTransformer will auto call any visit_* methods we create. \n
    When we call visit(node) the transformer checks the node type and looks for a matching method
    """  
    def __init__(self, counters):
        """
            Initializes the ASTVisitor with a temporary variable counter.
            and sets up the base class.
        """
        self.counters = counters
        self.temp_counter = 0
        super().__init__()

    def _new_temp(self):
        """
            Generates a new temporary variable for use in multiple assignments.
        """
        name = f"_assign_tmp_{self.temp_counter}"
        self.temp_counter += 1
        return name
      
    def visit_Assign(self, node):
        """
            Visits assignment nodes to wrap them with a call to count_assign.
        """
        node = self.generic_visit(node)

        if len(node.targets) == 1:
            node.value = ast.Call(
                func=ast.Name(id="count_assign", ctx=ast.Load()),
                args=[
                    ast.Name(id="COUNTERS", ctx=ast.Load()),
                    node.value
                ],
                keywords=[]
            )
            return node

        """ 
            Handle multiple assignments by introducing temporary variables 
        """
        temp_name = self._new_temp()
        temp_assign = ast.Assign(
            targets=[ast.Name(id=temp_name, ctx=ast.Store())],
            value=node.value
        )

        new_nodes = [temp_assign]

        for target in node.targets:
            new_assign = ast.Assign(
                targets=[target],
                value=ast.Call(
                    func=ast.Name(id="count_assign", ctx=ast.Load()),
                    args=[
                        ast.Name(id="COUNTERS", ctx=ast.Load()),
                        ast.Name(id=temp_name, ctx=ast.Load())
                    ],
                    keywords=[]
                )
            )

            ast.copy_location(new_assign, node)
            new_nodes.append(new_assign)

        return new_nodes

    def visit_Subscript(self, node):
        """
            Visits subscript (indexing) nodes to wrap them with a call to count_index.
        """
        node = self.generic_visit(node)

        if isinstance(node.ctx, ast.Store):
            return node
        
        return ast.Call(
            func=ast.Name(id="count_index", ctx=ast.Load()),
            args=[
                ast.Name(id="COUNTERS", ctx=ast.Load()),
                node.value,
                node.slice
            ],
            keywords=[]
        )

    def visit_Call(self, node):
        node = self.generic_visit(node)

        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name.startswith("count_"):
                return node
            if name in __builtins__:
                return node

        return ast.Call(
            func=ast.Name(id="count_call", ctx=ast.Load()),
            args=[
                ast.Name(id="COUNTERS", ctx=ast.Load()),
                node.func,
                *node.args
            ],
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
            ast.Is: "is_",
            ast.IsNot: "is_not",
            ast.In: "contains",
            ast.NotIn: "not_"
        }

        left = node.left
        new_expr = None

        for op, right in zip(node.ops, node.comparators):
            op_name = op_map.get(type(op))

            if not op_name:
                return node

            call = ast.Call(
                func=ast.Name(id="count_compare", ctx=ast.Load()),
                args=[
                    ast.Name(id="COUNTERS", ctx=ast.Load()),
                    left,
                    ast.Attribute(
                        value=ast.Name(id="operator", ctx=ast.Load()),
                        attr=op_name,
                        ctx=ast.Load()
                    ),
                    right
                ],
                keywords=[]
            )

            new_expr = call if new_expr is None else ast.BoolOp(
                op=ast.And(),
                values=[new_expr, call]
            )

            left = right

        return new_expr

    def visit_BinOp(self, node):
        """
            Visits binary operation nodes to wrap them with a call to count_arith.
        """
        node = self.generic_visit(node)

        op_map = {
            ast.Add: "add",
            ast.Sub: "sub",
            ast.Mult: "mul",
            ast.Div: "truediv",
            ast.FloorDiv: "floordiv",
            ast.Mod: "mod",
            ast.Pow: "pow",
            ast.LShift: "lshift",
            ast.RShift: "rshift",
            ast.BitOr: "or_",
            ast.BitXor: "xor",
            ast.BitAnd: "and_",
            ast.MatMult: "matmul"
        }

        op_name = op_map.get(type(node.op))

        if not op_name:
            return node

        return ast.Call(
            func=ast.Name(id="count_arith", ctx=ast.Load()),
            args=[
                ast.Name(id="COUNTERS", ctx=ast.Load()),
                node.left,
                ast.Attribute(
                    value=ast.Name(id="operator", ctx=ast.Load()),
                    attr=op_name,
                    ctx=ast.Load()
                ),
                node.right
            ],
            keywords=[]
        )
    
    def visit_For(self, node):
        """
            Visits for loop nodes to wrap them with a call to count_loop_iteration and count_loop.
        """
        self.counters["loop_nodes"] += 1

        # Visit children first (generic_visit)
        node = self.generic_visit(node)

        # Inject iteration counter at the top of the body
        counter_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="count_loop_iteration", ctx=ast.Load()),
                args=[ast.Name(id="COUNTERS", ctx=ast.Load())],
                keywords=[]
            )
        )
        node.body.insert(0, counter_call)
        return node


    def visit_While(self, node):
        """    
            Visits while loop nodes to wrap them with a call to count_loop_iteration and count_loop.
        """
        self.counters["loop_nodes"] += 1
        node = self.generic_visit(node)

        counter_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="count_loop_iteration", ctx=ast.Load()),
                args=[ast.Name(id="COUNTERS", ctx=ast.Load())],
                keywords=[]
            )
        )
        node.body.insert(0, counter_call)
        return node



def run_code(src: str, counters):
    counters = reset_counters(counters)

    tree = ast.parse(src)

    transformer = ASTVisitor(counters)
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)

    env = {
        "count_assign": count_assign,
        "count_index": count_index,
        "count_call": count_call,
        "count_compare": count_compare,
        "count_arith": count_arith,
        "count_loop_iteration": count_loop_iteration,
        "operator": operator,
        "COUNTERS": counters,
    }

    exec(compile(tree, "<instrumented>", "exec"), env)

    return counters