import sys
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))
from algorithm_analysis_tool.execution_session import ExecutionSession


def test_simple_execution_pipeline():
    code = """
def test_func(arr):
    total = 0
    for x in arr:
        total = total + x
    return total

result = test_func([1, 2, 3])
"""
    session = ExecutionSession()
    counters, history = session.run(code)

    assert counters["assignments"] > 0
    assert counters["arithmetic"] > 0
    assert counters["loop_iterations"] == 3


def test_semantic_preservation():
    code = """
def add(a, b):
    return a + b

result = add(2, 3)
"""

    local_env = {}
    exec(code, local_env)
    expected = local_env["result"]

    session = ExecutionSession()
    result, counters, history = session.run_function("add", [2, 3], src=code)

    assert result == expected


def test_sorting_algorithm():
    code = """
def bubble(arr):
    for i in range(len(arr)):
        for j in range(len(arr) - 1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

result = bubble([3, 1, 2])
"""

    session = ExecutionSession()
    counters, history = session.run(code)

    assert counters["comparisons"] > 0
    assert counters["assignments"] > 0
    assert counters["loop_iterations"] > 0


def test_function_call_tracking():
    code = """
def square(x):
    return x * x

def run():
    return square(5)

result = run()
"""

    session = ExecutionSession()
    counters, history = session.run(code)

    assert counters["function_calls"] > 0



def test_empty_input():
    code = """
def test(arr):
    for x in arr:
        pass
    return arr

result = test([])
"""

    session = ExecutionSession()
    counters, history = session.run(code)

    assert counters["loop_iterations"] == 0



def test_history_tracking():
    code = """
def test(arr):
    for i in range(len(arr)):
        arr[i] = arr[i] + 1
    return arr

result = test([1,2,3])
"""

    session = ExecutionSession(enable_history=True)
    counters, history = session.run(code)

    assert len(history) > 0
    assert "operation" in history[0]



def test_large_input_history_limit():
    code = """
def test(arr):
    for i in range(len(arr)):
        arr[i] += 1
    return arr

result = test(list(range(100)))
"""

    session = ExecutionSession(enable_history=True)
    counters, history = session.run(code)



def test_consistent_results():
    code = """
def test(arr):
    total = 0
    for x in arr:
        total += x
    return total
"""

    session1 = ExecutionSession()
    result1, counters1, _ = session1.run_function("test", [[1,2,3]], src=code)

    session2 = ExecutionSession()
    result2, counters2, _ = session2.run_function("test", [[1,2,3]], src=code)

    assert result1 == result2
    assert counters1 == counters2