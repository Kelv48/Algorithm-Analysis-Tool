import sys
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))

from algorithm_analysis_tool.execution_session import ExecutionSession


def test_bubble_sort_ast_instrumentation_preserves_result_and_counts():
    function_src = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr
"""

    run_src = function_src + "\nresult = bubble_sort([3, 2, 1])\n"

    plain_env = {}
    exec(run_src, plain_env)
    expected_result = plain_env["result"]

    run_session = ExecutionSession()
    run_counters, _ = run_session.run(run_src)

    fn_session = ExecutionSession()
    instrumented_result, fn_counters, _ = fn_session.run_function(
        "bubble_sort",
        [[3, 2, 1]],
        src=function_src,
    )

    assert expected_result == [1, 2, 3]
    assert instrumented_result == expected_result

    assert run_counters["assignments"] == 11
    assert run_counters["indexing"] == 12
    assert run_counters["function_calls"] == 1
    assert run_counters["returns"] == 1
    assert run_counters["comparisons"] == 3
    assert run_counters["arithmetic"] == 15
    assert run_counters["loop_nodes"] == 2
    assert run_counters["loop_iterations"] == 6

    assert fn_counters["assignments"] == 10
    assert fn_counters["indexing"] == 12
    assert fn_counters["function_calls"] == 0
    assert fn_counters["returns"] == 0
    assert fn_counters["comparisons"] == 3
    assert fn_counters["arithmetic"] == 15
    assert fn_counters["loop_nodes"] == 2
    assert fn_counters["loop_iterations"] == 6


def test_bubble_sort_sorted_input_early_exit_counts():
    function_src = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr
"""

    run_src = function_src + "\nresult = bubble_sort([1, 2, 3])\n"

    plain_env = {}
    exec(run_src, plain_env)
    expected_result = plain_env["result"]

    session = ExecutionSession()
    counters, _ = session.run(run_src)

    assert expected_result == [1, 2, 3]

    assert counters["assignments"] == 3
    assert counters["indexing"] == 4  
    assert counters["function_calls"] == 1
    assert counters["returns"] == 1
    assert counters["comparisons"] == 2
    assert counters["arithmetic"] == 4 
    assert counters["loop_nodes"] == 2
    assert counters["loop_iterations"] == 3


def test_bubble_sort_with_duplicates_preserves_result():
    function_src = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr
"""

    input_arr = [3, 1, 1, 2]

    plain_env = {}
    exec(function_src + f"\nresult = bubble_sort({input_arr})\n", plain_env)
    expected_result = plain_env["result"]

    session = ExecutionSession()
    result, counters, _ = session.run_function("bubble_sort", [input_arr[:]], src=function_src)

    assert result == expected_result
    assert result == [1, 1, 2, 3]

    assert counters["loop_nodes"] == 2
    assert counters["loop_iterations"] > 0
    assert counters["comparisons"] > 0
    assert counters["indexing"] > 0
    assert counters["arithmetic"] > 0
    assert counters["assignments"] > 0


def test_run_and_run_function_differ_only_by_top_level_call_and_result_assignment():
    function_src = """
def add_then_double(x, y):
    z = x + y
    return z * 2
"""

    run_src = function_src + "\nresult = add_then_double(2, 3)\n"

    plain_env = {}
    exec(run_src, plain_env)
    expected_result = plain_env["result"]

    run_session = ExecutionSession()
    run_counters, _ = run_session.run(run_src)

    fn_session = ExecutionSession()
    result, fn_counters, _ = fn_session.run_function("add_then_double", [2, 3], src=function_src)

    assert result == expected_result
    assert result == 10

    assert fn_counters["assignments"] == 1
    assert fn_counters["arithmetic"] == 2
    assert fn_counters["function_calls"] == 0
    assert fn_counters["returns"] == 0

    assert run_counters["assignments"] == 2
    assert run_counters["arithmetic"] == 2
    assert run_counters["function_calls"] == 1
    assert run_counters["returns"] == 1


def test_instrumentation_counts_nested_indexing_arithmetic_and_comparison():
    function_src = """
def step(arr):
    if arr[0] + arr[1] > arr[2]:
        arr[2] = arr[0] + arr[1]
    return arr
"""

    session = ExecutionSession()
    result, counters, _ = session.run_function("step", [[2, 3, 1]], src=function_src)

    assert result == [2, 3, 5]
    assert counters["assignments"] == 1
    assert counters["indexing"] == 5
    assert counters["comparisons"] == 1
    assert counters["arithmetic"] == 2


def test_instrumentation_does_not_count_builtin_calls_as_function_calls():
    function_src = """
def f(arr):
    x = len(arr)
    y = sum(arr)
    return x + y
"""

    session = ExecutionSession()
    result, counters, _ = session.run_function("f", [[1, 2, 3]], src=function_src)

    assert result == 9
    assert counters["function_calls"] == 0
    assert counters["assignments"] == 2
    assert counters["arithmetic"] == 1


def test_instrumentation_does_not_count_method_calls_as_function_calls():
    function_src = """
def f(arr):
    arr.append(4)
    return arr
"""

    session = ExecutionSession()
    result, counters, _ = session.run_function("f", [[1, 2, 3]], src=function_src)

    assert result == [1, 2, 3, 4]
    assert counters["function_calls"] == 0


def test_instrumentation_counts_recursive_calls_when_invoked_from_run():
    run_src = """
def countdown(n):
    if n == 0:
        return 0
    return countdown(n - 1)

result = countdown(3)
"""

    session = ExecutionSession()
    counters, _ = session.run(run_src)

    assert counters["function_calls"] == 4
    assert counters["returns"] == 4
    assert counters["comparisons"] == 4
    assert counters["arithmetic"] == 3
    assert counters["assignments"] == 1


def test_instrumentation_history_records_operations():
    function_src = """
def f(arr):
    arr[0] = arr[0] + 1
    return arr
"""

    session = ExecutionSession(enable_history=True)
    result, counters, history = session.run_function("f", [[1, 2, 3]], src=function_src)

    assert result == [2, 2, 3]
    assert len(history) > 0
    assert any(step["operation"] == "indexing" for step in history)
    assert any(step["operation"] == "arithmetic" for step in history)
    assert any(step["operation"] == "assignment" for step in history)


def test_loop_nodes_are_counted_when_function_is_defined():
    src = """
def f():
    for i in range(3):
        pass
    while False:
        pass
"""
    session = ExecutionSession()
    counters, _ = session.run(src)

    assert counters["loop_nodes"] == 2
    assert counters["loop_iterations"] == 0


def test_loop_iterations_are_counted_when_function_runs():
    src = """
def f():
    for i in range(3):
        pass
    while False:
        pass
"""
    session = ExecutionSession()
    result, counters, _ = session.run_function("f", [], src=src)

    assert counters["loop_nodes"] == 2
    assert counters["loop_iterations"] == 3