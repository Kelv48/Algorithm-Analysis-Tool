import sys
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))
from algorithm_analysis_tool.ast_visitor import ASTVisitor

def test_simple_assignment():
    result = ASTVisitor.run_code("x = 5")

    assert result["assignments"] == 1

def test_simple_arithmetic():
    result = ASTVisitor.run_code("x = 1 + 2")

    assert result["arithmetic"] == 1
    assert result["assignments"] == 1

def test_nested_arithmetic():
    code = "x = (1 + 2) * (3 + 4)"
    result = ASTVisitor.run_code(code)
    assert result["arithmetic"] == 3
    assert result["assignments"] == 1

def test_indexing():
    code = """
arr = [10,20,30]
x = arr[1]
"""
    result = ASTVisitor.run_code(code)
    assert result["indexing"] == 1
    assert result["assignments"] == 2

def test_function_call():
    code = """
def f(x):
    return x + 1

y = f(3)
"""
    result = ASTVisitor.run_code(code)
    assert result["function_calls"] == 1
    assert result["arithmetic"] == 1
    assert result["assignments"] == 1


def test_simple_comparison():
    result = ASTVisitor.run_code("x = 3 < 5")
    assert result["comparisons"] == 1
    assert result["assignments"] == 1

def test_chained_comparison():
    result = ASTVisitor.run_code("x = 1 < 2 < 3")
    assert result["comparisons"] == 2
    assert result["assignments"] == 1

def test_combined_expression():
    code = """
arr = [1,2,3]
x = arr[0] + arr[1]
if x > 2:
    y = x * 2
"""
    result = ASTVisitor.run_code(code)
    assert result["assignments"] == 3
    assert result["indexing"] == 2
    assert result["arithmetic"] == 2
    assert result["comparisons"] == 1

def test_no_false_positive():
    result = ASTVisitor.run_code("x = 42")
    assert result["arithmetic"] == 0
    assert result["indexing"] == 0
    assert result["function_calls"] == 0
    assert result["comparisons"] == 0