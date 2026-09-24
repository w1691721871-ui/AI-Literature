"""Local file storage for research-paper source PDFs."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAPER_DIRECTORY = PROJECT_ROOT / "work" / "papers"


def save_pdf_file(file_content: bytes, paper_id: str) -> str:
    """Save one validated source PDF under its generated UUID and return its path."""
    PAPER_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = PAPER_DIRECTORY / f"{paper_id}.pdf"
    destination.write_bytes(file_content)
    return str(destination)


def delete_pdf_file(file_path: str) -> None:
    """Remove a stored PDF only when it is inside this application's paper directory."""
    candidate = Path(file_path).resolve()
    storage_root = PAPER_DIRECTORY.resolve()
    if candidate.parent != storage_root:
        raise ValueError("论文文件路径不属于本地论文库。")
    if candidate.exists():
        candidate.unlink()


def read_pdf_file(file_path: str) -> bytes:
    """Read a stored PDF only when its path remains inside the paper library."""
    candidate = Path(file_path).resolve()
    storage_root = PAPER_DIRECTORY.resolve()
    if candidate.parent != storage_root:
        raise ValueError("论文文件路径不属于本地论文库。")
    if not candidate.is_file():
        raise FileNotFoundError("论文原始文件不存在，请重新上传论文。")
    return candidate.read_bytes()
