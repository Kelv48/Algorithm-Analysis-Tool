import random

def bubble_sort(arr):
    n = len(arr)
    a = 0 # Assignments
    c = 0 # Comparisons
    a_i = 0 # Array Indexing
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            c+=1
            a_i += 2
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j] ; a+=3 ; a_i+=4
                swapped = True
        # If no swaps happened, the list is already sorted
        if not swapped:
            break
    return arr, a, c, a_i


# Get user input for array size
n = 50

# Generate an array of n random numbers (range 1–100)
arr = [random.randint(1, 100) for _ in range(n)]

# Sort the array
sorted_arr, x,c, a_i = bubble_sort(arr)
print(x, "Assignments and", c, "Comparisons", a_i, "Array Indexs'")