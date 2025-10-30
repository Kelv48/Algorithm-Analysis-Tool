import random

def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        # If no swaps happened, the list is already sorted
        if not swapped:
            break
    return arr


# Get user input for array size
n = int(input("Enter the number of elements: "))

# Generate an array of n random numbers (range 1–100)
arr = [random.randint(1, 100) for _ in range(n)]

print("\nUnsorted array:", arr)

# Sort the array
sorted_arr = bubble_sort(arr)

print("Sorted array:", sorted_arr)
