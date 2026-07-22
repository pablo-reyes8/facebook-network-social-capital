"""Stage 06: compute structural network descriptions."""
from pipeline_lib import step06_descriptives


def main() -> None:
    """Calculate network and node-level descriptive measures."""
    print("[06] Computing network descriptives", flush=True)
    step06_descriptives()

if __name__ == "__main__":
    main()
