# 4th Year Project | Algorithm Analysis Tool

This module uses Python’s `ast` library to instrument source code at runtime and count specific program operations, including:

- Assignments  
- Indexing operations  
- Function calls  
- Comparisons  
- Arithmetic operations  

The system works by transforming the program’s Abstract Syntax Tree (AST) and injecting counter functions before execution.

---

## To Run

- Windows
```python
streamlit run src/streamlit_app/app.py --client.showSidebarNavigation=False
```

- Linux/MacOS
```bash
./run_streamlit.sh
```

---

## Dependencies

This module relies heavily on Python’s built-in `ast` module:

```python
import ast
```

The `ast.NodeTransformer` class is used to traverse and modify the syntax tree.

Also in use are 
- `matplotlib`
- `streamlit`
- `pandas`
- `plotly`
- `pytest`

---

## Global Counters

All operation counts are stored in a shared dictionary:

```python
COUNTERS = {
    "assignments": 0,
    "indexing": 0,
    "function_calls": 0,
    "comparisons": 0,
    "arithmetic": 0
}
```

Each key represents a category of tracked operations, while the corresponding value stores the cumulative count.

---

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