import sys
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))
from algorithm_analysis_tool.execution_session import ExecutionSession

def test_simple_assignment():
    session = ExecutionSession()
    counters, history = session.run("x = 5")
    assert counters["assignments"] == 1

def test_simple_arithmetic():
    session = ExecutionSession()
    counters, history = session.run("x = 1 + 2")
    assert counters["arithmetic"] == 1
    assert counters["assignments"] == 1

def test_nested_arithmetic():
    session = ExecutionSession()
    code = "x = (1 + 2) * (3 + 4)"
    counters, history = session.run(code)
    assert counters["arithmetic"] == 3
    assert counters["assignments"] == 1

def test_indexing():
    session = ExecutionSession()
    code = """
arr = [10,20,30]
x = arr[1]
"""
    counters, history = session.run(code)
    assert counters["indexing"] == 1
    assert counters["assignments"] == 2

def test_function_call():
    session = ExecutionSession()
    code = """
def f(x):
    return x + 1

y = f(3)
"""
    counters, history = session.run(code)
    assert counters["function_calls"] == 1
    assert counters["arithmetic"] == 1
    assert counters["assignments"] == 1

def test_tuple_indexing():
    session = ExecutionSession()
    code = """
t = (5, 10, 15)
x = t[2]
"""
    counters, history = session.run(code)
    assert counters["indexing"] == 1

def test_simple_comparison():
    session = ExecutionSession()
    counters, history = session.run("x = 3 < 5")
    assert counters["comparisons"] == 1
    assert counters["assignments"] == 1

def test_chained_comparison():
    session = ExecutionSession()
    counters, history = session.run("x = 1 < 2 < 3")
    assert counters["comparisons"] == 2
    assert counters["assignments"] == 1

def test_combined_expression():
    session = ExecutionSession()
    code = """
arr = [1,2,3]
x = arr[0] + arr[1]
if x > 2:
    y = x * 2
"""
    counters, history = session.run(code)
    assert counters["assignments"] == 3
    assert counters["indexing"] == 2
    assert counters["arithmetic"] == 2
    assert counters["comparisons"] == 1

def test_no_false_positive():
    session = ExecutionSession()
    counters, history = session.run("x = 42")
    assert counters["arithmetic"] == 0
    assert counters["indexing"] == 0
    assert counters["function_calls"] == 0
    assert counters["comparisons"] == 0

def test_nested_functions():
    session = ExecutionSession()
    code = """
def f(x):
    def g(y):
        return y * 2
    return g(x) + 1
z = f(3)
"""
    counters, history = session.run(code)
    assert counters["function_calls"] == 2
    assert counters["arithmetic"] == 2
    assert counters["assignments"] == 1

def test_multiple_operations():
    session = ExecutionSession()
    counters1, _ = session.run("x = 5 + 3")
    assert counters1["arithmetic"] == 1
    assert counters1["assignments"] == 1

    counters2, _ = session.run("y = 2 * 4")
    assert counters2["arithmetic"] == 2  # cumulative
    assert counters2["assignments"] == 2

def test_loop_count():
    session = ExecutionSession()
    code = """
for i in range(5):
    x = i * 2
"""
    counters, history = session.run(code)
    assert counters["loop_iterations"] == 5
    assert counters["loop_nodes"] == 1
    assert counters["arithmetic"] == 5
    assert counters["assignments"] == 5

def test_while_loop_count():
    session = ExecutionSession()
    code = """
i = 0
while i < 5:
    i += 1
"""
    counters, history = session.run(code)
    assert counters["loop_iterations"] == 5
    assert counters["loop_nodes"] == 1
    assert counters["assignments"] == 1

def test_power_operation():
    session = ExecutionSession()
    counters, history = session.run("x = 2 ** 3 ** 2")
    assert counters["arithmetic"] == 2

def test_method_call():
    session = ExecutionSession()
    code = """
arr = [1,2,3]
arr.append(4)
"""
    counters, history = session.run(code)
    assert counters["function_calls"] == 0

def test_builtin_call():
    session = ExecutionSession()
    counters, history = session.run("x = len([1,2,3])")
    assert counters["function_calls"] == 0

def test_call_inside_expression():
    session = ExecutionSession()
    code = """
def f(x): return x + 1
x = f(2) * f(3)
"""
    counters, history = session.run(code)
    assert counters["function_calls"] == 2
    assert counters["arithmetic"] == 3

def test_mixed_comparisons():
    session = ExecutionSession()
    counters, history = session.run("x = 1 < 2 <= 3 != 4")
    assert counters["comparisons"] == 3

def test_comparison_in_loop():
    session = ExecutionSession()
    code = """
for i in range(5):
    if i > 2:
        pass
"""
    counters, history = session.run(code)
    assert counters["comparisons"] == 5
    assert counters["loop_iterations"] == 5
    assert counters["loop_nodes"] == 1