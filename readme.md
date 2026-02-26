# Algorithm Analysis Tool | 4th Year Project

## Overview

The **Algorithm Analysis Tool** is a Python-based system designed to analyze and visualize the execution behavior of algorithms in real-time. By instrumenting code at runtime using Python’s `ast` library, this tool tracks key operations such as assignments, indexing, arithmetic, comparisons, function calls, and loop iterations.  

It provides both **single-execution** and **multi-execution dashboards**, allowing users to profile algorithms across multiple input configurations and visualize operational trends.

---

## Motivation

Analyzing algorithm performance is a fundamental skill in computer science, but traditional profiling tools often provide only coarse metrics such as execution time or memory usage.  

This tool goes **deeper**, enabling:

- Operation-level profiling (e.g., assignments vs comparisons)  
- Multi-run analysis across different input sizes and generation modes  
- Visualizations of algorithm behavior for teaching, research, and optimization purposes  

By instrumenting the **AST of the algorithm**, we avoid modifying source code manually while still collecting detailed execution statistics.

---

## Features

### Algorithm Support
The tool currently supports:

| Category   | Algorithms                         |
|------------|-----------------------------------|
| Sorting    | bubble_sort, merge_sort, insertion_sort, quicksort |
| Searching  | linear_search, binary_search       |
| Graph      | DFS, BFS                          |
| Scheduling | activity_selection                 |

- Graph algorithms track **nodes and edges** instead of arrays.  
- Sorting and searching algorithms track arrays and operations on array elements.  

### Input Generation Modes
- **random** — randomly generated arrays  
- **guided** — deterministic, controlled input for testing  
- **evolution** — optimized or edge-case input generation for performance testing  

### Multi-Execution
- Users can define multiple algorithms, input sizes (`n`), array lengths, and modes.  
- The system computes **all combinations** and queues jobs automatically.  
- Jobs can be **submitted, canceled, or dropped from the queue** before execution.  

### Visualization
- Bar charts of operation counts per job: assignments, comparisons, arithmetic operations, function calls, loop iterations  
- Optional graphs for node/edge-based algorithms  
- Dashboard metrics: total jobs, running, finished
- For single runs animations are available showing the line of code executed on small input sizes

---

### Key Components
1. **`execution_session.py`**  
   - Maintains counters for each operation type  
   - Tracks histories of arrays or graph nodes  
   - Provides methods such as `count_assign`, `count_index`, `count_compare`, `count_arith`, `count_loop_iteration`  

2. **`ast_visitor.py`**  
   - Traverses AST using `ast.NodeTransformer`  
   - Injects calls to the execution session counters before running code  

3. **`streamlit_app/single_execution.py`**  
   - Dashboard for single-job configuration and execution  
   - Supports history, job cancellation, and visualization/animating the steps  

4. **`streamlit_app/multi_execution.py`**  
   - Dashboard for multi-job configuration and execution  
   - Supports queueing, batch submission, job cancellation, and visualization  

---

## Example: Instrumented Code

Original code:

```python
x = 5
y = x + 2
```

Instrumented at Runtime
```python
x = SESSION.count_assign(5, arrays=[arr], line_no=1)
y = SESSION.count_arith(SESSION.count_index(x, None), operator.add, 2, arrays=[arr], line_no=2)
```


## Usage

### Instalation
```bash
pip install .
```

### Run on Windows
```sh
streamlit run src/streamlit_app/app.py --client.showSidebarNavigation=False
```

### Run on MacOS/Linux
```sh
./run_streamlit.sh
```
---

## Testing
Unit tests are provided to ensure the correct counting of operations
- Assignments, arithmetic and comparisons
- Indexing
- Function calls
- Loop iterations
- Cumulative counts

```python
def test_simple_arithmetic():
    session = ExecutionSession()
    counters, history = session.run("x = 1 + 2")
    assert counters["arithmetic"] == 1
    assert counters["assignments"] == 1
    assert_last_history(session, "arithmetic", -2)
    assert_last_history(session, "assignment", -1)
```

## Limitations
- Large arrays are truncated for visulaisation (MAX_ANIMATION_ARRAY_LENGTH)
- No GPU acceleration so runs on large input sizes may be slow (depends on the hardware)
- Current code is limited to predefined algorithms, with expected input formats