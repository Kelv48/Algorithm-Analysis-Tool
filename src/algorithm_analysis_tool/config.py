ALGO_GROUPS = {
    "Sorting": ["bubble_sort", "merge_sort", "insertion_sort", "quicksort", "radix_sort", "heap_sort"],
    "Searching": ["linear_search", "binary_search"],
    "Graph": ["dfs", "bfs"],
    "Scheduling": ["activity_selection"],
    "Matrix": ["matrix_multiply", "matrix_add"]
}

SORTING_ALGOS = set(ALGO_GROUPS["Sorting"])
SEARCH_ALGOS = set(ALGO_GROUPS["Searching"])
GRAPH_ALGOS = set(ALGO_GROUPS["Graph"])
ACTIVITY_ALGOS = set(ALGO_GROUPS["Scheduling"])
MATRIX_ALGOS = set(ALGO_GROUPS["Matrix"])

ARRAY_GROUPS = {"Sorting", "Searching", "Scheduling"}
GRAPH_GROUPS = {"Graph"}
MATRIX_GROUPS = {"Matrix"}