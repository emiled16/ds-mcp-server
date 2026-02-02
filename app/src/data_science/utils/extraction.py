import gzip
import shutil
from pathlib import Path
from zipfile import ZipFile


def extract_zip_file(file_path: Path, output_dir: Path) -> Path:
    with ZipFile(file_path, "r") as zip_file:
        zip_file.extractall(output_dir)
    return output_dir


def extract_gz_file(file_path: Path, output_dir: Path) -> Path:
    with gzip.open(file_path, "rb") as gz_file, output_dir.open("wb") as f:
        shutil.copyfileobj(gz_file, f)
    return output_dir
