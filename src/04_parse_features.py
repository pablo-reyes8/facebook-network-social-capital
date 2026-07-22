"""Stage 04: parse ego-specific feature vectors and dictionaries."""
from pipeline_lib import step04_features


def main() -> None:
    """Build long, wide, and dictionary feature artifacts."""
    print("[04] Parsing features", flush=True)
    step04_features()

if __name__ == "__main__":
    main()
