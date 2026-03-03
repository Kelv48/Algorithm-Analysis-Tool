# Algorithm Analysis Tool | Ast Core Logic & CLI
This documentation covers the core logic of the Algorithm Analysis Tool, including AST-based runtime instrumentation and the CLI for executing algorithms with optional custom or random inputs.


# Runtime Counter Functions

These functions are injected into the transformed program and executed during runtime. Each function increments its respective counter and returns the original operation result.

---

## Arithmetic Counter

### `count_arith(a, op, b)`

Tracks binary arithmetic operations.

### Purpose

- Increments the arithmetic operation counter  
- Applies the requested operator to the provided operands  
- Returns the computed result  

### Implementation

```python
def count_arith(a, op, b):
    COUNTERS["arithmetic"] += 1
    return op(a, b)
```

---

## Assignment Counter

### `count_assign(value)`

Tracks variable assignments.

### Purpose

- Increments the assignment counter  
- Returns the assigned value unchanged  

### Implementation

```python
def count_assign(value):
    COUNTERS["assignments"] += 1
    return value
```

---

## Indexing Counter

### `count_index(obj, key)`

Tracks indexing operations such as list and dictionary access.

### Purpose

- Increments the indexing counter  
- Returns the accessed element  

### Implementation

```python
def count_index(obj, key):
    COUNTERS["indexing"] += 1
    return obj[key]
```

---

## Function Call Counter

### `count_call(fn, *args, **kwargs)`

Tracks function invocations.

### Purpose

- Increments the function call counter  
- Executes the original function call  
- Returns the function result  

### Implementation

```python
def count_call(fn, *args, **kwargs):
    COUNTERS["function_calls"] += 1
    return fn(*args, **kwargs)
```

---

## Comparison Counter

### `count_compare(a, op, b)`

Tracks comparison operations.

### Purpose

- Increments the comparison counter  
- Applies the comparison operator  
- Returns the boolean result  

### Implementation

```python
def count_compare(a, op, b):
    COUNTERS["comparisons"] += 1
    return op(a, b)
```

---

# AST Transformer

The `ASTVisitor` class extends `ast.NodeTransformer` and overrides specific visitor methods to replace syntax nodes with instrumented equivalents.

Python automatically calls `visit_*` methods when traversing the AST.

---

## Class Definition

```python
class ASTVisitor(ast.NodeTransformer):
```

---

## Assignment Instrumentation

### Method: `visit_Assign`

Transforms assignment expressions by wrapping the assigned value with `count_assign`.

### Example Transformation

Original:

```python
x = 5
```

Instrumented:

```python
x = count_assign(5)
```

### Implementation

```python
def visit_Assign(self, node):
    node = self.generic_visit(node)
    node.value = ast.Call(
        func=ast.Name(id="count_assign", ctx=ast.Load()),
        args=[node.value],
        keywords=[]
    )
    return node
```

---

## Indexing Instrumentation

### Method: `visit_Subscript`

Wraps indexing operations with `count_index`, excluding assignment targets such as:

```python
arr[i] = x
```

### Example Transformation

Original:

```python
arr[i]
```

Instrumented:

```python
count_index(arr, i)
```

### Implementation

```python
def visit_Subscript(self, node):
    node = self.generic_visit(node)

    if isinstance(node.ctx, ast.Store):
        return node
        
    return ast.Call(
        func=ast.Name(id="count_index", ctx=ast.Load()),
        args=[node.value, node.slice],
        keywords=[]
    )
```

---

## Function Call Instrumentation

### Method: `visit_Call`

Wraps function calls with `count_call`.

### Example Transformation

Original:

```python
foo(x)
```

Instrumented:

```python
count_call(foo, x)
```

### Implementation

```python
def visit_Call(self, node):
    node = self.generic_visit(node)
    return ast.Call(
        func=ast.Name(id="count_call", ctx=ast.Load()),
        args=[node.func] + node.args,
        keywords=[]
    )
```

---

## Comparison Instrumentation

### Method: `visit_Compare`

Maps Python comparison operators to the corresponding functions in the `operator` module and wraps them with `count_compare`.

### Example Transformation

Original:

```python
a < b
```

Instrumented:

```python
count_compare(a, operator.lt, b)
```

### Supported Operators

| Operator | Mapping |
|---------|---------|
| `<` | `lt` |
| `>` | `gt` |
| `==` | `eq` |
| `!=` | `ne` |
| `<=` | `le` |
| `>=` | `ge` |
| `is` | `is` |
| `is not` | `is_not` |
| `in` | `in` |
| `not in` | `not_in` |

### Implementation

```python
def visit_Compare(self, node):
    node = self.generic_visit(node)

    op_map = {
        ast.Lt: "lt",
        ast.Gt: "gt",
        ast.Eq: "eq",
        ast.NotEq: "ne",
        ast.LtE: "le",
        ast.GtE: "ge",
        ast.Is: "is",
        ast.IsNot: "is_not",
        ast.In: "in",
        ast.NotIn: "not_in"
    }

    op = op_map.get(type(node.ops[0]))
    if not op:
        return node

    return ast.Call(
        func=ast.Name(id="count_compare", ctx=ast.Load()),
        args=[
            node.left,
            ast.Attribute(value=ast.Name(id="operator", ctx=ast.Load()), attr=op, ctx=ast.Load()),
            node.comparators[0],
        ],
        keywords=[]
    )
```

---

## Arithmetic Instrumentation

### Method: `visit_BinOp`

Wraps binary arithmetic operations using `count_arith`.

### Supported Operations

- Addition  
- Subtraction  
- Multiplication  
- Division  
- Floor division  
- Modulo  
- Power  
- Bitwise operations  
- Matrix multiplication  

### Example Transformation

Original:

```python
a + b
```

Instrumented:

```python
count_arith(a, operator.add, b)
```

### Implementation

```python
def visit_BinOp(self, node):
    node = self.generic_visit(node)

    if not isinstance(node.parent, ast.Assign):
        op_map = {
            ast.Add: "add",
            ast.Sub: "sub",
            ast.Mult: "mul",
            ast.Div: "truediv",
            ast.FloorDiv: "floordiv",
            ast.Mod: "mod",
            ast.Pow: "pow",
            ast.LShift: "lshift",
            ast.RShift: "rshift",
            ast.BitOr: "or",
            ast.BitXor: "xor",
            ast.BitAnd: "and_",
            ast.MatMult: "matmul"
        }

        op = op_map.get(type(node.op))
        if op:
            return ast.Call(
                func=ast.Name(id="count_arith", ctx=ast.Load()),
                args=[
                    node.left,
                    ast.Attribute(value=ast.Name(id="operator", ctx=ast.Load()), attr=op, ctx=ast.Load()),
                    node.right
                ],
                keywords=[]
            )
    return node
```

---

# Cli Functionality

The CLI allows you to execute, test, and compare algorithm functions from a Python file, with flexible input options and runtime metrics.

## 1. CLI Features

The CLI supports the following:

1. **Function Selection**
   - List all functions in a Python file.
   - Run all functions or a subset by specifying their numbers (comma-separated).

2. **Input Options**
   - **Default inputs** (predefined for standard algorithms like sorting/searching).
   - **Custom JSON inputs** provided by the user.
   - **Randomly generated inputs** for:
     - Sorting
     - Searching
     - Graph algorithms (DFS/BFS)
     - Scheduling/Activity Selection
     - Matrix operations

3. **Execution Options**
   - Measure execution time (`y/N`)
   - Show full step-by-step execution history (`y/N`)
   - Compare multiple functions side by side (`y/N`)

4. **Results**
   - Function return value
   - Runtime counters (comparisons, assignments, indexing, arithmetic, function calls)
   - Execution time

5. **Error Handling**
   - Missing or invalid arguments show a descriptive error and continue other functions.
   - Invalid JSON input falls back to default input.
   - Invalid file paths terminate the CLI with a clear message.

---

## 2. Running the CLI

```python
algorithm-analysis
```

### Example Session
```python
Available functions:
1. bubble_sort
2. merge_sort
3. insertion_sort
4. quicksort
5. heap_sort
6. radix_sort
7. linear_search
8. binary_search
9. dfs
10. bfs
11. matrix_multiply
12. matrix_add

Enter function numbers to run (comma-separated) or leave blank for all: 1,2
Provide custom input as JSON (leave blank for default): [[5, 2, 9, 1, 5, 6]]
Use random input? (y/N): N
Random input size (default 10): 10
Measure execution time? (y/N): Y
Show full step history? (y/N): N
Compare multiple functions? (y/N): Y
```

### Custom Input Cheat Sheet
1. Sorting
```json
[5, 2, 9, 1, 5, 6]
```

2. Searching
```json
[[1, 3, 5, 7, 9], 5]
```

3. Graph Algos
```json
[{"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}, "A"]
```

4. Activity Selection
```json
[[[1, 4], [3, 5], [0, 6], [5, 7], [8, 9]]]
```

5. Matrix Algos
```json
[
  [[1, 2], [3, 4]],
  [[5, 6], [7, 8]]
]
```

---