"""Stage 08: compute within-ego social similarity and diversity."""
from pipeline_lib import step08_similarity


def main() -> None:
    """Build edge and node-level similarity/diversity artifacts."""
    print("[08] Computing social similarity and diversity", flush=True)
    step08_similarity()

if __name__ == "__main__":
    main()
