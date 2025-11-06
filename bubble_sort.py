import random

a_i = 0  # global counter
c = 0 # Comparisons
a = 0  # Assignments

def count(x, ai_inc=2, c_inc=1):
    global a_i
    global c
    c += c_inc
    a_i += ai_inc
    return x

def bubble_sort(arr):
    n = len(arr)
    global a_i  # Array Indexing
    global a
    global c
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if count(arr[j] > arr[j + 1]):
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                a += 3
                a_i += 4  # for index ops
                swapped = True
        if not swapped:
            break
    return arr, a, c, a_i

n = 50
arr = [random.randint(1, 100) for _ in range(n)]

sorted_arr, a, c, a_i = bubble_sort(arr)
print(a, "Assignments and", c, "Comparisons", a_i, "Array Indexes")
