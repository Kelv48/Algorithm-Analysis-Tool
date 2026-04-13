import sys
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
ast_visitor_path = root / "src" / "algorithm_analysis_tool"
sys.path.insert(0, str(ast_visitor_path))

from algorithm_analysis_tool.execution_session import ExecutionSession


def assert_last_history(session, op_type, index=None, array_len=None, nodes_len=None, edges_len=None,):
    assert session.history
    last = session.history[index]
    assert last["operation"] == op_type

    if array_len is not None:
        arrays = last.get("arrays")
        assert arrays is not None
        assert len(arrays[0]) == array_len

    if nodes_len is not None:
        nodes = last.get("nodes")
        assert nodes is not None
        assert len(nodes) == nodes_len

    if edges_len is not None:
        edges = last.get("visited_edges")
        assert edges is not None
        assert len(edges) == edges_len


class TestAssignments:
    def test_simple_assignment(self):
        session = ExecutionSession(enable_history=True)
        counters, history = session.run("x = 5")

        assert counters["assignments"] == 1
        assert_last_history(session, "assignment", -1)

    def test_multiple_assignments(self):
        session = ExecutionSession()
        counters, history = session.run("""
x = 1
y = 2
z = 3
""")

        assert counters["assignments"] == 3

    def test_tuple_unpack_assignment(self):
        session = ExecutionSession()
        counters, history = session.run("""
a, b = (1, 2)
""")

        assert counters["assignments"] == 1

    def test_augmented_assignment_counts_once(self):
        session = ExecutionSession()
        counters, history = session.run("""
x = 1
x += 2
""")

        assert counters["assignments"] == 1
        assert counters["arithmetic"] == 0


class TestArithmetic:
    def test_simple_arithmetic(self):
        session = ExecutionSession(enable_history=True)
        counters, history = session.run("x = 1 + 2")

        assert counters["arithmetic"] == 1
        assert counters["assignments"] == 1
        assert_last_history(session, "arithmetic", -2)
        assert_last_history(session, "assignment", -1)

    def test_nested_arithmetic(self):
        session = ExecutionSession()
        counters, history = session.run("x = (1 + 2) * (3 + 4)")

        assert counters["arithmetic"] == 3
        assert counters["assignments"] == 1

    def test_power_operation(self):
        session = ExecutionSession()
        counters, history = session.run("x = 2 ** 3 ** 2")

        assert counters["arithmetic"] == 2

    def test_unary_arithmetic_not_counted_as_binary(self):
        session = ExecutionSession()
        counters, history = session.run("x = -5")

        assert counters["assignments"] == 1

    def test_arithmetic_inside_condition_and_assignment(self):
        session = ExecutionSession()
        counters, history = session.run("""
x = 1 + 2
if x * 2 > 3:
    y = x - 1
""")

        assert counters["arithmetic"] == 3
        assert counters["comparisons"] == 1
        assert counters["assignments"] == 2


class TestIndexing:
    def test_indexing(self):
        session = ExecutionSession()
        counters, history = session.run("""
arr = [10, 20, 30]
x = arr[1]
""")

        assert counters["indexing"] == 1
        assert counters["assignments"] == 2

    def test_tuple_indexing(self):
        session = ExecutionSession()
        counters, history = session.run("""
t = (5, 10, 15)
x = t[2]
""")

        assert counters["indexing"] == 1

    def test_nested_indexing(self):
        session = ExecutionSession()
        counters, history = session.run("""
arr = [[1, 2], [3, 4]]
x = arr[1][0]
""")

        assert counters["indexing"] == 2

    def test_indexing_on_rhs_of_assignment(self):
        session = ExecutionSession()
        counters, history = session.run("""
arr = [1, 2, 3]
arr[1] = arr[0] + arr[2]
""")

        assert counters["indexing"] == 2
        assert counters["arithmetic"] == 1


class TestComparisons:
    def test_simple_comparison(self):
        session = ExecutionSession()
        counters, history = session.run("x = 3 < 5")

        assert counters["comparisons"] == 1
        assert counters["assignments"] == 1

    def test_chained_comparison(self):
        session = ExecutionSession()
        counters, history = session.run("x = 1 < 2 < 3")

        assert counters["comparisons"] == 2
        assert counters["assignments"] == 1

    def test_mixed_comparisons(self):
        session = ExecutionSession()
        counters, history = session.run("x = 1 < 2 <= 3 != 4")

        assert counters["comparisons"] == 3

    def test_comparison_in_loop(self):
        session = ExecutionSession()
        counters, history = session.run("""
for i in range(5):
    if i > 2:
        pass
""")

        assert counters["comparisons"] == 5
        assert counters["loop_iterations"] == 5
        assert counters["loop_nodes"] == 1

    def test_boolean_and_or_comparisons(self):
        session = ExecutionSession()
        counters, history = session.run("""
x = (1 < 2) and (3 > 2)
""")

        assert counters["comparisons"] == 2
        assert counters["assignments"] == 1


class TestFunctionCalls:
    def test_function_call(self):
        session = ExecutionSession()
        counters, history = session.run("""
def f(x):
    return x + 1

y = f(3)
""")

        assert counters["function_calls"] == 1
        assert counters["arithmetic"] == 1
        assert counters["assignments"] == 1

    def test_nested_functions(self):
        session = ExecutionSession()
        counters, history = session.run("""
def f(x):
    def g(y):
        return y * 2
    return g(x) + 1

z = f(3)
""")

        assert counters["function_calls"] == 2
        assert counters["arithmetic"] == 2
        assert counters["assignments"] == 1

    def test_call_inside_expression(self):
        session = ExecutionSession()
        counters, history = session.run("""
def f(x):
    return x + 1

x = f(2) * f(3)
""")

        assert counters["function_calls"] == 2
        assert counters["arithmetic"] == 3

    def test_method_call(self):
        session = ExecutionSession()
        counters, history = session.run("""
arr = [1, 2, 3]
arr.append(4)
""")

        assert counters["function_calls"] == 0

    def test_builtin_call(self):
        session = ExecutionSession()
        counters, history = session.run("x = len([1,2,3])")

        assert counters["function_calls"] == 0

    def test_recursive_function_calls(self):
        session = ExecutionSession()
        counters, history = session.run("""
def countdown(n):
    if n == 0:
        return 0
    return countdown(n - 1)

result = countdown(3)
""")

        assert counters["function_calls"] == 4
        assert counters["comparisons"] == 4
        assert counters["arithmetic"] == 3


class TestLoops:
    def test_loop_count(self):
        session = ExecutionSession()
        counters, history = session.run("""
for i in range(5):
    x = i * 2
""")

        assert counters["loop_iterations"] == 5
        assert counters["loop_nodes"] == 1
        assert counters["arithmetic"] == 5
        assert counters["assignments"] == 5

    def test_while_loop_count(self):
        session = ExecutionSession()
        counters, history = session.run("""
i = 0
while i < 5:
    i += 1
""")

        assert counters["loop_iterations"] == 5
        assert counters["loop_nodes"] == 1
        assert counters["assignments"] == 1

    def test_nested_loops(self):
        session = ExecutionSession()
        counters, history = session.run("""
for i in range(3):
    for j in range(2):
        x = i + j
""")

        assert counters["loop_nodes"] == 2
        assert counters["loop_iterations"] == 9  # 3 outer + 6 inner
        assert counters["arithmetic"] == 6
        assert counters["assignments"] == 6

    def test_zero_iteration_loop(self):
        session = ExecutionSession()
        counters, history = session.run("""
for i in range(0):
    x = i
""")

        assert counters["loop_nodes"] == 1
        assert counters["loop_iterations"] == 0

    def test_loop_over_collection(self):
        session = ExecutionSession()
        counters, history = session.run("""
for x in [1, 2, 3, 4]:
    y = x + 1
""")

        assert counters["loop_iterations"] == 4
        assert counters["arithmetic"] == 4
        assert counters["assignments"] == 4


class TestCombinedExpressions:
    def test_combined_expression(self):
        session = ExecutionSession()
        counters, history = session.run("""
arr = [1,2,3]
x = arr[0] + arr[1]
if x > 2:
    y = x * 2
""")

        assert counters["assignments"] == 3
        assert counters["indexing"] == 2
        assert counters["arithmetic"] == 2
        assert counters["comparisons"] == 1

    def test_no_false_positive(self):
        session = ExecutionSession()
        counters, history = session.run("x = 42")

        assert counters["arithmetic"] == 0
        assert counters["indexing"] == 0
        assert counters["function_calls"] == 0
        assert counters["comparisons"] == 0

    def test_list_comprehension_counts_inner_expression(self):
        session = ExecutionSession()
        counters, history = session.run("""
x = [i * 2 for i in range(3)]
""")

        assert counters["assignments"] == 1
        assert counters["arithmetic"] == 3

    def test_if_else_both_branches_not_double_counted(self):
        session = ExecutionSession()
        counters, history = session.run("""
x = 1
if x > 0:
    y = x + 1
else:
    y = x + 2
""")

        assert counters["comparisons"] == 1
        assert counters["assignments"] == 2
        assert counters["arithmetic"] == 1


class TestHistoryIntegration:
    def test_assignment_history_shape(self):
        session = ExecutionSession(enable_history=True)
        counters, history = session.run("x = 5")

        assert len(history) >= 1
        assert history[-1]["operation"] == "assignment"

    def test_arithmetic_then_assignment_history_order(self):
        session = ExecutionSession(enable_history=True)
        counters, history = session.run("x = 1 + 2")

        assert len(history) >= 2
        assert history[-2]["operation"] == "arithmetic"
        assert history[-1]["operation"] == "assignment"

    def test_history_persists_across_runs_when_enabled(self):
        session = ExecutionSession(enable_history=True)

        session.run("x = 1")
        first_len = len(session.history)

        session.run("y = 2 + 3")
        second_len = len(session.history)

        assert second_len > first_len