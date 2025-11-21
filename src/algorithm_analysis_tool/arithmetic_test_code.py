import ast
import operator

COUNTERS = {
    "arithmetic" : 0
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

class Arithmetic_Visiter(ast.NodeTransformer):
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

# Where we read in the python program we want to test on
# with open("bubble_sort.py", "r") as f:
#     tree = ast.parse(f.read())

# for child in ast.walk(tree):
#     for sub in ast.iter_child_nodes(child):
#         sub.parent = child # Keep track of the parent nodes for use by the methods

# visited_tree = Arithmetic_Visiter().visit(tree)
# ast.fix_missing_locations(visited_tree)

# code = compile(visited_tree, filename="<ast>", mode="exec")

# exec_globals = {
#     "COUNTERS": COUNTERS,
#     "count_arith": count_arith,
#     "operator": operator
# }

# exec(code, exec_globals)

# # import random
# # n = 10
# # arr = [random.randint(1, 100) for _ in range(n)]
# arr = [2, 5, 3, 1, 4]
# # print(arr)
# exec_globals["bubble_sort"](arr) # Executing bubble sort with the input of arr

# # Output of the counters at the end of the program
# print(COUNTERS)