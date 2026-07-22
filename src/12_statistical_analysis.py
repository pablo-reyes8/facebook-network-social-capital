"""Stage 12: estimate primary correlations and regression models."""
from pipeline_lib import step12_statistics


def main() -> None:
    """Run statistical inference, diagnostics, and ego heterogeneity."""
    print("[12] Running statistical analysis", flush=True)
    step12_statistics()

if __name__ == "__main__":
    main()
