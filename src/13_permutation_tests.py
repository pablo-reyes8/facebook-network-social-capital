"""Stage 13: run social and structural null models."""
from pipeline_lib import step13_permutations


def main() -> None:
    """Run 1,000 attribute permutations and configuration-model tests."""
    print("[13] Running permutation and configuration-model tests", flush=True)
    step13_permutations()

if __name__ == "__main__":
    main()
