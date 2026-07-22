"""Stage 07: detect, stabilize, and compare network communities."""
from pipeline_lib import step07_communities


def main() -> None:
    """Run Louvain stability analysis and alternative comparisons."""
    print("[07] Detecting communities", flush=True)
    step07_communities()

if __name__ == "__main__":
    main()
