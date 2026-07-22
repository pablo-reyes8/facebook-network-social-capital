"""Stage 14: evaluate analytical robustness and bootstrap uncertainty."""
from pipeline_lib import step14_robustness


def main() -> None:
    """Run alternative measures, samples, partitions, and bootstrap checks."""
    print("[14] Running robustness checks", flush=True)
    step14_robustness()

if __name__ == "__main__":
    main()
