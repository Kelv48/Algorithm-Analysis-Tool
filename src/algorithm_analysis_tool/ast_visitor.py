import ast
import operator
import copy


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

MAX_ANIMATION_ARRAY_LENGTH = 6
MAX_HISTORY_ARRAY_LENGTH = 100

def not_in(a, b):
    return a not in b

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


def track_op(op_type, counters, arrays=None, line_no=None, history=None):
    """
    Record a snapshot of counters and array state.
    Only stores arrays if they are smaller than MAX_HISTORY_ARRAY_LENGTH.
    Deepcopy ensures arrays are frozen at this moment.
    """ 
    if arrays and len(arrays) > 0:
        first_array = arrays[0]
        if isinstance(first_array, list) and len(first_array) > MAX_HISTORY_ARRAY_LENGTH:
            return

    arrays_snapshot = None
    line_snapshot = line_no
    if arrays and len(arrays) > 0:
        first_array = arrays[0]
        if isinstance(first_array, list) and len(first_array) <= MAX_ANIMATION_ARRAY_LENGTH:
            arrays_snapshot = [copy.deepcopy(a) for a in arrays]
        else:
            arrays_snapshot = None
            line_snapshot = None

    snapshot = {
        "line_no": line_snapshot,
        "operation": op_type,
        "counters": counters.copy(),
        "arrays": arrays_snapshot
    }

    if history is not None:
        history.append(snapshot)


def count_assign(counters, value, arrays=None, line_no=None):
    """
        Counts the assignment operations being performed \n.
        Increments the global assignment counter by 1.

        Parameters:
            value: The value being assigned.

        Returns:
            The value being assigned.
    """
    counters["assignments"] += 1
    track_op("assignment", counters, arrays, line_no)
    return value

def count_index(counters, obj, key, arrays=None, line_no=None):
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
    track_op("indexing", counters, arrays, line_no)
    return obj[key]

def count_call(counters, fn, *args, arrays=None, line_no=None, **kwargs):
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
    track_op(f"call_{fn.__name__}", counters, arrays, line_no)
    return fn(*args, **kwargs)

def count_compare(counters, a, op, b, arrays=None, line_no=None):
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
    track_op("comparison", counters, arrays, line_no)
    return op(a, b)

def count_arith(counters, a, op, b, arrays=None, line_no=None):
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
    track_op("arithmetic", counters, arrays, line_no)
    return op(a, b)

def count_loop_iteration(counters, arrays=None, line_no=None):
    """
        Counts the loop iterations being performed \n.
        Increments the global loop iteration counter by 1.
    """
    counters["loop_iterations"] += 1
    track_op("loop_iteration", counters, arrays, line_no)

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
      
    # Assignments
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
                    node.value,
                    ast.Name(id="arrays", ctx=ast.Load()),
                    ast.Constant(value=getattr(node, 'lineno', None))
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
                        ast.Name(id=temp_name, ctx=ast.Load()),
                        ast.Name(id="arrays", ctx=ast.Load()),
                        ast.Constant(value=getattr(node, 'lineno', None))
                    ],
                    keywords=[]
                )
            )
            ast.copy_location(new_assign, node)
            new_nodes.append(new_assign)

        return new_nodes

    # Indexing
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
                node.slice,
                ast.Name(id="arrays", ctx=ast.Load()),
                ast.Constant(value=getattr(node, 'lineno', None))
            ],
            keywords=[]
        )

    # Function Calls
    def visit_Call(self, node):
        node = self.generic_visit(node)

        if isinstance(node.func, ast.Attribute):
            return node

        if not isinstance(node.func, ast.Name):
            return node

        name = node.func.id
        
        if name.startswith("count_"):
            return node
        
        import builtins
        if hasattr(builtins, name):
            return node

        # Inject arrays and line_no as keywords to count_call, not to fn
        return ast.Call(
            func=ast.Name(id="count_call", ctx=ast.Load()),
            args=[
                ast.Name(id="COUNTERS", ctx=ast.Load()),
                node.func,
                *node.args  # only original args
            ],
            keywords=[
                ast.keyword(arg="arrays", value=ast.Name(id="arrays", ctx=ast.Load())),
                ast.keyword(arg="line_no", value=ast.Constant(value=getattr(node, "lineno", None))),
                *node.keywords  # preserve original keywords
            ]
        )
    
    # Comparisons
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
            ast.NotIn: "not_in"
        }

        left = node.left
        new_expr = None

        for op, right in zip(node.ops, node.comparators):
            op_name = op_map.get(type(op))

            if not op_name:
                return node
            if op_name == "not_in":
                op_node = ast.Name(id="not_in", ctx=ast.Load())
            else:
                op_node = ast.Attribute(
                value=ast.Name(id="operator", ctx=ast.Load()),
                attr=op_name,
                ctx=ast.Load()
            )
                
            call = ast.Call(
                func=ast.Name(id="count_compare", ctx=ast.Load()),
                args=[
                    ast.Name(id="COUNTERS", ctx=ast.Load()),
                    left,
                    op_node,
                    right,
                ],
                keywords=[]
            )

            new_expr = call if new_expr is None else ast.BoolOp(
                op=ast.And(),
                values=[new_expr, call]
            )

            left = right

        return new_expr

    # Arithmetic
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
                ast.Attribute(value=ast.Name(id="operator", ctx=ast.Load()), attr=op_name, ctx=ast.Load()),
                node.right,
                ast.Name(id="arrays", ctx=ast.Load()),
                ast.Constant(value=getattr(node, 'lineno', None))
            ],
            keywords=[]
        )
    
    # For Loops
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
                args=[ast.Name(id="COUNTERS", ctx=ast.Load()),
                      ast.Name(id="arrays", ctx=ast.Load()),
                      ast.Constant(value=getattr(node, 'lineno', None))],
                keywords=[]
            )
        )
        node.body.insert(0, counter_call)
        return node


    # While Loops
    def visit_While(self, node):
        """    
            Visits while loop nodes to wrap them with a call to count_loop_iteration and count_loop.
        """
        self.counters["loop_nodes"] += 1
        node = self.generic_visit(node)

        counter_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="count_loop_iteration", ctx=ast.Load()),
                args=[ast.Name(id="COUNTERS", ctx=ast.Load()),
                      ast.Name(id="arrays", ctx=ast.Load()),
                      ast.Constant(value=getattr(node, 'lineno', None))],
                keywords=[]
            )
        )
        node.body.insert(0, counter_call)
        return node



def run_code(src: str, counters):
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


# ---------------- Count functions ----------------

def count_assign(counters, value, arrays=None, line_no=None, history=None):
    counters["assignments"] += 1
    track_op("assignment", counters, arrays, line_no, history)
    return value

def count_index(counters, obj, key, arrays=None, line_no=None, history=None):
    counters["indexing"] += 1
    track_op("indexing", counters, arrays, line_no, history)
    return obj[key]

def count_call(counters, fn, *args, arrays=None, line_no=None, history=None, **kwargs):
    counters["function_calls"] += 1
    counters["returns"] += 1
    track_op(f"call_{fn.__name__}", counters, arrays, line_no, history)
    return fn(*args, **kwargs)

def count_compare(counters, a, op, b, arrays=None, line_no=None, history=None):
    counters["comparisons"] += 1
    track_op("comparison", counters, arrays, line_no, history)
    return op(a, b)

def count_arith(counters, a, op, b, arrays=None, line_no=None, history=None):
    counters["arithmetic"] += 1
    track_op("arithmetic", counters, arrays, line_no, history)
    return op(a, b)

def count_loop_iteration(counters, arrays=None, line_no=None, history=None):
    counters["loop_iterations"] += 1
    track_op("loop_iteration", counters, arrays, line_no, history)

# ----- AST Visiter --------
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
      
    # Assignments
    def visit_Assign(self, node):
        node = self.generic_visit(node)

        if len(node.targets) == 1:
            node.value = ast.Call(
                func=ast.Name(id="count_assign", ctx=ast.Load()),
                args=[
                    ast.Name(id="COUNTERS", ctx=ast.Load()),
                    node.value,
                    ast.Name(id="arrays", ctx=ast.Load()),
                    ast.Constant(value=getattr(node, 'lineno', None)),
                    ast.Name(id="HISTORY", ctx=ast.Load())
                ],
                keywords=[]
            )
            return node

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
                        ast.Name(id=temp_name, ctx=ast.Load()),
                        ast.Name(id="arrays", ctx=ast.Load()),
                        ast.Constant(value=getattr(node, 'lineno', None)),
                        ast.Name(id="HISTORY", ctx=ast.Load())
                    ],
                    keywords=[]
                )
            )
            ast.copy_location(new_assign, node)
            new_nodes.append(new_assign)

        return new_nodes

    # Indexing
    def visit_Subscript(self, node):
        node = self.generic_visit(node)
        if isinstance(node.ctx, ast.Store):
            return node

        return ast.Call(
            func=ast.Name(id="count_index", ctx=ast.Load()),
            args=[
                ast.Name(id="COUNTERS", ctx=ast.Load()),
                node.value,
                node.slice,
                ast.Name(id="arrays", ctx=ast.Load()),
                ast.Constant(value=getattr(node, 'lineno', None)),
                ast.Name(id="HISTORY", ctx=ast.Load())
            ],
            keywords=[]
        )
    
    # Comparisons
    def visit_Compare(self, node):
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
            ast.NotIn: "not_in"
        }

        left = node.left
        new_expr = None

        for op, right in zip(node.ops, node.comparators):
            op_name = op_map.get(type(op))
            if not op_name:
                return node

            if op_name == "not_in":
                op_node = ast.Name(id="not_in", ctx=ast.Load())
            else:
                op_node = ast.Attribute(value=ast.Name(id="operator", ctx=ast.Load()),
                                        attr=op_name, ctx=ast.Load())

            call = ast.Call(
                func=ast.Name(id="count_compare", ctx=ast.Load()),
                args=[
                    ast.Name(id="COUNTERS", ctx=ast.Load()),
                    left,
                    op_node,
                    right,
                    ast.Name(id="arrays", ctx=ast.Load()),
                    ast.Constant(value=getattr(node, 'lineno', None)),
                    ast.Name(id="HISTORY", ctx=ast.Load())
                ],
                keywords=[]
            )

            new_expr = call if new_expr is None else ast.BoolOp(op=ast.And(), values=[new_expr, call])
            left = right

        return new_expr

    # Arithmetic
    def visit_BinOp(self, node):
        node = self.generic_visit(node)
        op_map = {
            ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "truediv",
            ast.FloorDiv: "floordiv", ast.Mod: "mod", ast.Pow: "pow",
            ast.LShift: "lshift", ast.RShift: "rshift", ast.BitOr: "or_",
            ast.BitXor: "xor", ast.BitAnd: "and_", ast.MatMult: "matmul"
        }
        op_name = op_map.get(type(node.op))
        if not op_name:
            return node

        return ast.Call(
            func=ast.Name(id="count_arith", ctx=ast.Load()),
            args=[
                ast.Name(id="COUNTERS", ctx=ast.Load()),
                node.left,
                ast.Attribute(value=ast.Name(id="operator", ctx=ast.Load()), attr=op_name, ctx=ast.Load()),
                node.right,
                ast.Name(id="arrays", ctx=ast.Load()),
                ast.Constant(value=getattr(node, 'lineno', None)),
                ast.Name(id="HISTORY", ctx=ast.Load())
            ],
            keywords=[]
        )
    
    # For Loops
    def visit_For(self, node):
        self.counters["loop_nodes"] += 1
        node = self.generic_visit(node)

        counter_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="count_loop_iteration", ctx=ast.Load()),
                args=[
                    ast.Name(id="COUNTERS", ctx=ast.Load()),
                    ast.Name(id="arrays", ctx=ast.Load()),
                    ast.Constant(value=getattr(node, 'lineno', None)),
                    ast.Name(id="HISTORY", ctx=ast.Load())
                ],
                keywords=[]
            )
        )
        node.body.insert(0, counter_call)
        return node

    # While Loops
    def visit_While(self, node):
        self.counters["loop_nodes"] += 1
        node = self.generic_visit(node)

        counter_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="count_loop_iteration", ctx=ast.Load()),
                args=[
                    ast.Name(id="COUNTERS", ctx=ast.Load()),
                    ast.Name(id="arrays", ctx=ast.Load()),
                    ast.Constant(value=getattr(node, 'lineno', None)),
                    ast.Name(id="HISTORY", ctx=ast.Load())
                ],
                keywords=[]
            )
        )
        node.body.insert(0, counter_call)
        return node



def run_code(src: str):
    counters = reset_counters()
    history = []

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
        "HISTORY": history,
        "arrays": []
    }

    exec(compile(tree, "<instrumented>", "exec"), env)

    return counters, history