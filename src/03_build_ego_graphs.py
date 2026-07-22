"""Stage 03: construct full and largest-component ego graphs."""
from pipeline_lib import step03_graphs


def main() -> None:
    """Build and serialize the ten eligible ego-networks."""
    print("[03] Building ego-networks", flush=True)
    step03_graphs()

if __name__ == "__main__":
    main()
