"""Stage 05: construct and document analytical samples A through E."""
from pipeline_lib import step05_sample


def main() -> None:
    """Apply predefined eligibility criteria and write sample flow."""
    print("[05] Constructing analytical samples", flush=True)
    step05_sample()

if __name__ == "__main__":
    main()
