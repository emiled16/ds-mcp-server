from typing import get_args

from src.data_science.ds_core.definitions.splitters import Splitter


def get_list_of_splitters() -> list[type]:
    if not hasattr(Splitter, "__origin__"):
        raise ValueError("Splitter is not a valid splitter")
    all_splitters = get_args(Splitter.__origin__)
    return list(all_splitters)


def get_list_of_splitter_names() -> list[str]:
    return [splitter.__name__ for splitter in get_list_of_splitters()]


def get_splitter_by_name(splitter_name: str) -> type:
    all_splitters = get_list_of_splitters()
    for splitter in all_splitters:
        if splitter.__name__ == splitter_name:
            return splitter
    raise ValueError(f"Splitter {splitter_name} not found")
