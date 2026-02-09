import sys
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))
from algorithm_analysis_tool.ast_visitor import run_code, reset_counters

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

def test_simple_assignment():
    counters = reset_counters(COUNTERS)
    result = run_code("x = 5", counters)
    assert result["assignments"] == 1

def test_simple_arithmetic():
    counters = reset_counters(COUNTERS)
    result = run_code("x = 1 + 2", counters)

    assert result["arithmetic"] == 1
    assert result["assignments"] == 1

def test_nested_arithmetic():
    counters = reset_counters(COUNTERS)
    code = "x = (1 + 2) * (3 + 4)"
    result = run_code(code, counters)
    assert result["arithmetic"] == 3
    assert result["assignments"] == 1

def test_indexing():
    counters = reset_counters(COUNTERS)
    code = """
arr = [10,20,30]
x = arr[1]
"""
    result = run_code(code, counters)
    assert result["indexing"] == 1
    assert result["assignments"] == 2
    assert result["function_calls"] == 0

def test_function_call():
    counters = reset_counters(COUNTERS)
    code = """
def f(x):
    return x + 1

y = f(3)
"""
    result = run_code(code, counters)
    assert result["function_calls"] == 1
    assert result["arithmetic"] == 1
    assert result["assignments"] == 1

def test_tuple_indexing():
    counters = reset_counters(COUNTERS)
    code = """
t = (5, 10, 15)
x = t[2]
"""
    result = run_code(code, counters)
    assert result["indexing"] == 1

def test_simple_comparison():
    counters = reset_counters(COUNTERS)
    result = run_code("x = 3 < 5", counters)
    assert result["comparisons"] == 1
    assert result["assignments"] == 1

def test_chained_comparison():
    counters = reset_counters(COUNTERS)
    result = run_code("x = 1 < 2 < 3", counters)
    assert result["comparisons"] == 2
    assert result["assignments"] == 1

def test_combined_expression():
    counters = reset_counters(COUNTERS)
    code = """
arr = [1,2,3]
x = arr[0] + arr[1]
if x > 2:
    y = x * 2
"""
    result = run_code(code, counters)
    assert result["assignments"] == 3
    assert result["indexing"] == 2
    assert result["arithmetic"] == 2
    assert result["comparisons"] == 1

def test_no_false_positive():
    counters = reset_counters(COUNTERS)
    result = run_code("x = 42", counters)
    assert result["arithmetic"] == 0
    assert result["indexing"] == 0
    assert result["function_calls"] == 0
    assert result["comparisons"] == 0

def test_nested_functions():
    counters = reset_counters(COUNTERS)
    code = """
def f(x):
    def g(y):
        return y * 2
    return g(x) + 1
z = f(3)
"""
    result = run_code(code, counters)
    assert result["function_calls"] == 2
    assert result["arithmetic"] == 2
    assert result["assignments"] == 1

def test_multiple_operations():
    counters = reset_counters(COUNTERS)
    temp = run_code("x = 5 + 3", counters)
    assert temp["arithmetic"] == 1
    assert temp["assignments"] == 1

    run_code("y = 2 * 4", counters)
    result = counters

    assert result["arithmetic"] == 2
    assert result["assignments"] == 2

def test_reset_counters():
    counters = reset_counters(COUNTERS)
    result = run_code("x = 5 + 3", counters)
    assert result["arithmetic"] == 1
    assert result["assignments"] == 1

    new_counter = reset_counters(counters)
    assert new_counter["arithmetic"] == 0
    assert new_counter["assignments"] == 0

    result = run_code("y = 2 * 4", new_counter)
    assert result["arithmetic"] == 1
    assert result["assignments"] == 1

def test_loop_count():
    counters = reset_counters(COUNTERS)
    code = """
for i in range(5):
    x = i * 2
"""
    result = run_code(code, counters)
    assert result["loop_iterations"] == 5
    assert result["loop_nodes"] == 1
    assert result["arithmetic"] == 5
    assert result["assignments"] == 5

def test_while_loop_count():
    counters = reset_counters(COUNTERS)
    code = """
i = 0
while i < 5:
    i += 1
"""
    result = run_code(code, counters)
    assert result["loop_iterations"] == 5
    assert result["loop_nodes"] == 1
    assert result["assignments"] == 1

def test_power_operation():
    counters = reset_counters(COUNTERS)
    result = run_code("x = 2 ** 3 ** 2", counters)
    assert result["arithmetic"] == 2

def test_method_call():
    counters = reset_counters(COUNTERS)
    code = """
arr = [1,2,3]
arr.append(4)
"""
    result = run_code(code, counters)
    assert result["function_calls"] == 1

def test_builtin_call():
    counters = reset_counters(COUNTERS)
    result = run_code("x = len([1,2,3])", counters)
    assert result["function_calls"] == 0

def test_call_inside_expression():
    counters = reset_counters(COUNTERS)
    code = """
def f(x): return x + 1
x = f(2) * f(3)
"""
    result = run_code(code, counters)
    assert result["function_calls"] == 2
    assert result["arithmetic"] == 3

def test_mixed_comparisons():
    counters = reset_counters(COUNTERS)
    result = run_code("x = 1 < 2 <= 3 != 4", counters)
    assert result["comparisons"] == 3

def test_comparison_in_loop():
    counters = reset_counters(COUNTERS)
    code = """
for i in range(5):
    if i > 2:
        pass
"""
    result = run_code(code, counters)
    assert result["comparisons"] == 5
    assert result["loop_iterations"] == 5
    assert result["loop_nodes"] == 1