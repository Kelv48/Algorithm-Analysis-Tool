def merge_sort(arr):
    # Base case: a list of 0 or 1 elements is already sorted
    if len(arr) <= 1:
        return arr

    # Split the list into two halves
    mid = len(arr) // 2
    left_half = arr[:mid]
    right_half = arr[mid:]

    # Recursively sort both halves
    left_sorted = merge_sort(left_half)
    right_sorted = merge_sort(right_half)

    # Merge the sorted halves
    return merge(left_sorted, right_sorted)


def merge(left, right):
    merged = []
    i = j = 0

    # Merge elements from left and right in sorted order
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    # Append any remaining elements
    merged.extend(left[i:])
    merged.extend(right[j:])

    return merged
