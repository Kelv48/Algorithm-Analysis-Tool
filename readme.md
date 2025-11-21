# 4th Year Project

## Docs for  Arithmetic Test

This test code uses Python's `ast` (Abstract Syntax Tree) module to **instrument** another Python file and count how many **arithmetic operations** it performs during execution.  

It does this by:

1. Parsing a target Python file (e.g., `bubble_sort.py`).
2. Modifying its AST to wrap arithmetic expressions (`+`, `-`, `*`, `/`) in a custom counter function.
3. Executing the transformed program.
4. Reporting the number of arithmetic operations performed.

---

## How It Works

### 1. Arithmetic Counter

The function `count_arith(a, op, b)`:

- Increments a global counter `COUNTERS["arithmetic"]`.
- Executes the given operation using `operator` (e.g., `operator.add`).
- Returns the computed result.

This function is inserted everywhere an arithmetic operation appears.
This is done automatically by the transformer as any visit_* method is used where a matching node is found.

---

### 2. AST Transformation

The class `Arithmetic_Visiter` extends `ast.NodeTransformer` and overrides `visit_BinOp` to replace:

```python
a + b
```
With
```python
count_arith(a, operator.add, b)
```

<b>Note</b> Modulo (%), power (**), and floor division (//) are not supported yet.