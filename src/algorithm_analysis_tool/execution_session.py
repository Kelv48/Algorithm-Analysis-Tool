import ast
import operator
import copy


MAX_ANIMATION_ARRAY_LENGTH = 5
MAX_HISTORY_ARRAY_LENGTH = 50
MAX_TRACKABLE_ARRAY_LENGTH = 50


def not_in(a, b):
    return a not in b


def reset_counters():
    return {
        "assignments": 0,
        "indexing": 0,
        "function_calls": 0,
        "returns": 0,
        "comparisons": 0,
        "arithmetic": 0,
        "loop_nodes": 0,
        "loop_iterations": 0
    }


class ExecutionSession:
    def __init__(self):
        self.counters = reset_counters()
        self.history = []
        self.final_state = None

    def track_op(self, op_type, arrays=None, line_no=None, nodes=None, edges=None):
        """
        Track an operation step.
        - For arrays: existing behavior.
        - For small graphs: store visited nodes/edges.
        """
        if arrays and len(arrays) > 0 and isinstance(arrays[0], list):
            main_array = arrays[0]
            length = len(main_array)

            if length > MAX_TRACKABLE_ARRAY_LENGTH:
                self.final_state = main_array
                return

            if length <= MAX_ANIMATION_ARRAY_LENGTH:
                arrays_snapshot = [copy.deepcopy(a) for a in arrays]
                self.history.append({
                    "line_no": line_no,
                    "operation": op_type,
                    "counters": self.counters.copy(),
                    "arrays": arrays_snapshot
                })
            return

        if nodes is not None and edges is not None:
            if len(nodes) <= 6 and len(edges) <= 8:
                self.history.append({
                    "line_no": line_no,
                    "operation": op_type,
                    "counters": self.counters.copy(),
                    "nodes": copy.deepcopy(nodes),
                    "visited_edges": copy.deepcopy(edges),
                    "arrays": None
                })
            return

        # --- Fallback for operations with no arrays or graph ---
        self.history.append({
            "line_no": line_no,
            "operation": op_type,
            "counters": self.counters.copy(),
            "arrays": None
        })

    # ---------------- counting functions ----------------

    def count_assign(self, value, arrays=None, line_no=None):
        self.counters["assignments"] += 1
        self.track_op("assignment", arrays, line_no)
        return value

    def count_index(self, obj, key, arrays=None, line_no=None):
        self.counters["indexing"] += 1
        self.track_op("indexing", arrays, line_no)
        return obj[key]

    def count_call(self, fn, *args, arrays=None, line_no=None, **kwargs):
        self.counters["function_calls"] += 1
        self.counters["returns"] += 1
        self.track_op(f"call_{fn.__name__}", arrays, line_no)
        return fn(*args, **kwargs)

    def count_compare(self, a, op, b, arrays=None, line_no=None):
        self.counters["comparisons"] += 1
        self.track_op("comparison", arrays, line_no)
        return op(a, b)

    def count_arith(self, a, op, b, arrays=None, line_no=None):
        self.counters["arithmetic"] += 1
        self.track_op("arithmetic", arrays, line_no)
        return op(a, b)

    def count_loop_iteration(self, arrays=None, line_no=None):
        self.counters["loop_iterations"] += 1
        self.track_op("loop_iteration", arrays, line_no)

    # ---------------- execution ----------------

    def run(self, src: str):
        from ast_visitor import ASTVisitor

        tree = ast.parse(src)
        transformer = ASTVisitor(self)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)

        env = {
            "SESSION": self,
            "operator": operator,
            "not_in": not_in,
            "arrays": []
        }

        exec(compile(tree, "<instrumented>", "exec"), env)

        # Append final snapshot for large arrays if skipped
        if self.final_state:
            self.history.append({
                "line_no": None,
                "operation": "final_state",
                "counters": self.counters.copy(),
                "arrays": [self.final_state]
            })

        return self.counters, self.history