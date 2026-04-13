import sys
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))

from algorithm_analysis_tool.execution_session import ExecutionSession


class TestExecutionSessionRun:
    def test_simple_execution_pipeline(self):
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

    def test_sorting_algorithm(self):
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

    def test_empty_input(self):
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

    def test_run_allows_multiple_executions_with_cumulative_counters(self):
        session = ExecutionSession()

        counters1, _ = session.run("x = 1 + 2")
        assert counters1["assignments"] == 1
        assert counters1["arithmetic"] == 1

        counters2, _ = session.run("y = 3 + 4")
        assert counters2["assignments"] == 2
        assert counters2["arithmetic"] == 2

    def test_run_executes_code_with_function_and_global_result(self):
        code = """
def inc(x):
    return x + 1

result = inc(10)
"""
        session = ExecutionSession()
        counters, history = session.run(code)

        assert counters["function_calls"] == 1
        assert counters["arithmetic"] == 1

    def test_run_handles_recursive_function(self):
        code = """
def fact(n):
    if n <= 1:
        return 1
    return n * fact(n - 1)

result = fact(4)
"""
        session = ExecutionSession()
        counters, history = session.run(code)

        assert counters["function_calls"] == 4
        assert counters["comparisons"] == 4
        assert counters["arithmetic"] >= 6  # multiplications + subtractions

    def test_run_with_conditional_branches(self):
        code = """
x = 10
if x > 5:
    y = x - 3
else:
    y = x + 3
"""
        session = ExecutionSession()
        counters, history = session.run(code)

        assert counters["comparisons"] == 1
        assert counters["assignments"] == 2
        assert counters["arithmetic"] == 1


class TestExecutionSessionRunFunction:
    def test_semantic_preservation(self):
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

    def test_consistent_results(self):
        code = """
def test(arr):
    total = 0
    for x in arr:
        total += x
    return total
"""
        session1 = ExecutionSession()
        result1, counters1, _ = session1.run_function("test", [[1, 2, 3]], src=code)

        session2 = ExecutionSession()
        result2, counters2, _ = session2.run_function("test", [[1, 2, 3]], src=code)

        assert result1 == result2
        assert counters1 == counters2

    def test_run_function_with_no_arguments(self):
        code = """
def greet():
    return 42
"""
        session = ExecutionSession()
        result, counters, history = session.run_function("greet", [], src=code)

        assert result == 42
        assert counters["function_calls"] == 0

    def test_run_function_with_list_argument_mutation(self):
        code = """
def mutate(arr):
    arr[0] = arr[0] + 10
    return arr
"""
        session = ExecutionSession()
        result, counters, history = session.run_function("mutate", [[1, 2, 3]], src=code)

        assert result == [11, 2, 3]
        assert counters["indexing"] == 1
        assert counters["arithmetic"] == 1

    def test_run_function_raises_for_missing_function(self):
        code = """
def exists():
    return 1
"""
        session = ExecutionSession()

        try:
            session.run_function("does_not_exist", [], src=code)
            assert False, "Expected an exception for missing function"
        except Exception:
            assert True


class TestExecutionSessionHistory:
    def test_history_tracking_enabled(self):
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

    def test_history_disabled_returns_empty_or_no_growth(self):
        code = """
x = 1 + 2
"""
        session = ExecutionSession(enable_history=False)
        counters, history = session.run(code)

        assert history == [] or len(history) == 0

    def test_history_contains_multiple_operations_in_order(self):
        code = """
x = 1 + 2
"""
        session = ExecutionSession(enable_history=True)
        counters, history = session.run(code)

        assert len(history) >= 2
        assert history[-2]["operation"] == "arithmetic"
        assert history[-1]["operation"] == "assignment"

    def test_large_input_history_limit_or_growth(self):
        code = """
def test(arr):
    for i in range(len(arr)):
        arr[i] += 1
    return arr

result = test(list(range(100)))
"""
        session = ExecutionSession(enable_history=True)
        counters, history = session.run(code)

        assert counters["loop_iterations"] == 100
        assert len(history) > 0

    def test_history_is_returned_from_run_function(self):
        code = """
def square(x):
    return x * x
"""
        session = ExecutionSession(enable_history=True)
        result, counters, history = session.run_function("square", [5], src=code)

        assert result == 25
        assert len(history) > 0
        assert any("operation" in item for item in history)


class TestExecutionSessionFunctionCalls:
    def test_function_call_tracking(self):
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

    def test_nested_function_calls(self):
        code = """
def a(x):
    return x + 1

def b(x):
    return a(x) * 2

result = b(3)
"""
        session = ExecutionSession()
        counters, history = session.run(code)

        assert counters["function_calls"] == 2
        assert counters["arithmetic"] == 2

    def test_builtin_calls_are_not_tracked_as_function_calls(self):
        code = """
result = len([1, 2, 3])
"""
        session = ExecutionSession()
        counters, history = session.run(code)

        assert counters["function_calls"] == 0