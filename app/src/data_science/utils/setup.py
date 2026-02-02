import warnings


def setup_environment() -> None:
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.simplefilter(action="ignore", category=FutureWarning)
