from enum import Enum


class Split(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
