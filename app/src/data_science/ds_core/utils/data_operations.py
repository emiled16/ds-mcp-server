def find_common_columns(columns: list[list[str]]) -> list[str]:
    """
    Find common columns between two or more lists of columns.
    Args:
        columns: The lists of columns to find common columns between.
    Returns:
        The common columns between the lists.
    """
    return list(set.intersection(*[set(col) for col in columns]))
