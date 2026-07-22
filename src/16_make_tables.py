"""Stage 16: export publication tables in three interoperable formats."""
from pipeline_lib import step16_tables


def main() -> None:
    """Write CSV, Markdown, and LaTeX versions of each table."""
    print("[16] Exporting tables", flush=True)
    step16_tables()

if __name__ == "__main__":
    main()
