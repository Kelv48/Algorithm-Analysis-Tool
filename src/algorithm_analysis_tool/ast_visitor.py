import ast

# ----- AST Visiter --------
class ASTVisitor(ast.NodeTransformer):
    """
    NodeTransformer will auto call any visit_* methods we create. \n
    When we call visit(node) the transformer checks the node type and looks for a matching method
    """  
    def __init__(self, session):
        self.session = session
        self.temp_counter = 0
        super().__init__()

    def _session_attr(self, name: str):
        return ast.Attribute(
            value=ast.Name(id="SESSION", ctx=ast.Load()),
            attr=name,
            ctx=ast.Load()
        )

    def _new_temp(self):
        """
            Generates a new temporary variable for use in multiple assignments.
        """
        name = f"_assign_tmp_{self.temp_counter}"
        self.temp_counter += 1
        return name
      
    # ---------------- assignments ----------------

    def visit_Assign(self, node):
        node = self.generic_visit(node)

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
                    func=self._session_attr("count_assign"),
                    args=[
                        ast.Name(id=temp_name, ctx=ast.Load()),
                        ast.Name(id="arrays", ctx=ast.Load()),
                        ast.Constant(value=getattr(node, "lineno", None)),
                    ],
                    keywords=[]
                )
            )

            ast.copy_location(new_assign, node)
            new_nodes.append(new_assign)

        return new_nodes

    # ---------------- indexing ----------------

    def visit_Subscript(self, node):
        node = self.generic_visit(node)

        if isinstance(node.ctx, ast.Store):
            return node

        return ast.Call(
            func=self._session_attr("count_index"),
            args=[
                node.value,
                node.slice,
                ast.Name(id="arrays", ctx=ast.Load()),
                ast.Constant(value=getattr(node, "lineno", None)),
            ],
            keywords=[]
        )

    # ---------------- function calls ----------------

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

        return ast.Call(
            func=self._session_attr("count_call"),
            args=[
                node.func,
                *node.args
            ],
            keywords=[
                ast.keyword(arg="arrays", value=ast.Name(id="arrays", ctx=ast.Load())),
                ast.keyword(arg="line_no", value=ast.Constant(value=getattr(node, "lineno", None))),
                *node.keywords
            ]
        )
    
    # ---------------- comparisons ----------------

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
                op_node = ast.Attribute(
                    value=ast.Name(id="operator", ctx=ast.Load()),
                    attr=op_name,
                    ctx=ast.Load()
                )

            call = ast.Call(
                func=self._session_attr("count_compare"),
                args=[
                    left,
                    op_node,
                    right,
                    ast.Name(id="arrays", ctx=ast.Load()),
                    ast.Constant(value=getattr(node, "lineno", None)),
                ],
                keywords=[]
            )

            new_expr = call if new_expr is None else ast.BoolOp(
                op=ast.And(),
                values=[new_expr, call]
            )

            left = right

        return new_expr

    # ---------------- arithmetic ----------------

    def visit_BinOp(self, node):
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
            func=self._session_attr("count_arith"),
            args=[
                node.left,
                ast.Attribute(
                    value=ast.Name(id="operator", ctx=ast.Load()),
                    attr=op_name,
                    ctx=ast.Load()
                ),
                node.right,
                ast.Name(id="arrays", ctx=ast.Load()),
                ast.Constant(value=getattr(node, "lineno", None)),
            ],
            keywords=[]
        )
    
    # ---------------- loops ----------------

    def visit_For(self, node):
        self.session.counters["loop_nodes"] += 1
        node = self.generic_visit(node)

        counter_call = ast.Expr(
            value=ast.Call(
                func=self._session_attr("count_loop_iteration"),
                args=[
                    ast.Name(id="arrays", ctx=ast.Load()),
                    ast.Constant(value=getattr(node, "lineno", None)),
                ],
                keywords=[]
            )
        )

        node.body.insert(0, counter_call)
        return node

    def visit_While(self, node):
        self.session.counters["loop_nodes"] += 1
        node = self.generic_visit(node)

        counter_call = ast.Expr(
            value=ast.Call(
                func=self._session_attr("count_loop_iteration"),
                args=[
                    ast.Name(id="arrays", ctx=ast.Load()),
                    ast.Constant(value=getattr(node, "lineno", None)),
                ],
                keywords=[]
            )
        )

        node.body.insert(0, counter_call)
        return node