import sys
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))
from algorithm_analysis_tool.ast_visitor import run_code, reset_counters

def test_simple_assignment():
    result = run_code("x = 5")
    assert result["assignments"] == 1

def test_simple_arithmetic():
    result = run_code("x = 1 + 2")

    assert result["arithmetic"] == 1
    assert result["assignments"] == 1

def test_nested_arithmetic():
    code = "x = (1 + 2) * (3 + 4)"
    result = run_code(code)
    assert result["arithmetic"] == 3
    assert result["assignments"] == 1

def test_indexing():
    code = """
arr = [10,20,30]
x = arr[1]
"""
    result = run_code(code)
    assert result["indexing"] == 1
    assert result["assignments"] == 2
    assert result["function_calls"] == 0

def test_function_call():
    code = """
def f(x):
    return x + 1

y = f(3)
"""
    result = run_code(code)
    assert result["function_calls"] == 1
    assert result["arithmetic"] == 1
    assert result["assignments"] == 1

def test_tuple_indexing():
    code = """
t = (5, 10, 15)
x = t[2]
"""
    result = run_code(code)
    assert result["indexing"] == 1

def test_simple_comparison():
    result = run_code("x = 3 < 5")
    assert result["comparisons"] == 1
    assert result["assignments"] == 1

def test_chained_comparison():
    result = run_code("x = 1 < 2 < 3")
    assert result["comparisons"] == 2
    assert result["assignments"] == 1

def test_combined_expression():
    code = """
arr = [1,2,3]
x = arr[0] + arr[1]
if x > 2:
    y = x * 2
"""
    result = run_code(code)
    assert result["assignments"] == 3
    assert result["indexing"] == 2
    assert result["arithmetic"] == 2
    assert result["comparisons"] == 1

def test_no_false_positive():
    result = run_code("x = 42")
    assert result["arithmetic"] == 0
    assert result["indexing"] == 0
    assert result["function_calls"] == 0
    assert result["comparisons"] == 0

def test_nested_functions():
    code = """
def f(x):
    def g(y):
        return y * 2
    return g(x) + 1
z = f(3)
"""
    result = run_code(code)
    assert result["function_calls"] == 2
    assert result["arithmetic"] == 2
    assert result["assignments"] == 1

def test_multiple_operations():
    from collections import Counter
    temp = run_code("x = 5 + 3")
    assert temp["arithmetic"] == 1
    assert temp["assignments"] == 1 # Check that counters were incremented for the 1st run

    temp2 = run_code("y = 2 * 4")
    result = Counter(temp) + Counter(temp2)
    result = dict(result)

    assert result["arithmetic"] == 2
    assert result["assignments"] == 2 # Check that counters were incremented for the 2nd run

def test_reset_counters():
    result = run_code("x = 5 + 3")
    assert result["arithmetic"] == 1
    assert result["assignments"] == 1 # Check that counters were incremented for the 1st run

    result = reset_counters()
    assert result["arithmetic"] == 0
    assert result["assignments"] == 0 # Check that counters were reset

    result = run_code("y = 2 * 4")
    assert result["arithmetic"] == 1
    assert result["assignments"] == 1 # Check that counters were reset before the 2nd run

def test_loop_count():
    code = """
for i in range(5):
    x = i * 2
"""
    result = run_code(code)
    assert result["loop_iterations"] == 5
    assert result["loop_nodes"] == 1
    assert result["arithmetic"] == 5
    assert result["assignments"] == 5

def test_while_loop_count():
    code = """
i = 0
while i < 5:
    i += 1
"""
    result = run_code(code)
    assert result["loop_iterations"] == 5
    assert result["loop_nodes"] == 1
    assert result["assignments"] == 1

def test_multiple_assignment():
    result = run_code("x = y = 5")
    assert result["assignments"] == 2

def test_power_operation():
    result = run_code("x = 2 ** 3 ** 2")
    assert result["arithmetic"] == 2

def test_method_call():
    code = """
arr = [1,2,3]
arr.append(4)
"""
    result = run_code(code)
    assert result["function_calls"] == 1

def test_builtin_call():
    result = run_code("x = len([1,2,3])")
    assert result["function_calls"] == 1

def test_call_inside_expression():
    code = """
def f(x): return x + 1
x = f(2) * f(3)
"""
    result = run_code(code)
    assert result["function_calls"] == 2
    assert result["arithmetic"] == 3

def test_mixed_comparisons():
    result = run_code("x = 1 < 2 <= 3 != 4")
    assert result["comparisons"] == 3

def test_comparison_in_loop():
    code = """
for i in range(5):
    if i > 2:
        pass
"""
    result = run_code(code)
    assert result["comparisons"] == 5
    assert result["loop_iterations"] == 5
    assert result["loop_nodes"] == 1