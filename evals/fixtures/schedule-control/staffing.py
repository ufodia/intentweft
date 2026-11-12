def valid_count(break_number: int, count: int) -> bool:
    """Evaluate an integer count for a documented break number from 1 to 5."""
    if break_number == 4:
        return count in (1, 2)
    return count == 3
