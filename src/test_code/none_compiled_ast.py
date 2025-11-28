import ast

# A interpreter that can evaluate an AST directly
# Requires implementing evaluation logic for different AST node types
# Is incredibly limited compared to using compile and eval
def eval_ast(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        left = eval_ast(node.left)
        right = eval_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
    raise NotImplementedError

tree = ast.parse("1 + 2", mode="eval")
print(eval_ast(tree.body))  # 3


# Using compile and eval to execute an AST
tree = ast.parse("1 + 2", mode="eval")

code_obj = compile(tree, filename="<ast>", mode="eval")

result = eval(code_obj)

print(result)
