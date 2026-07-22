"""Stage 10: compute shortest-path and inter-community brokerage."""
from pipeline_lib import step10_brokerage


def main() -> None:
    """Build brokerage measures and connector-role outputs."""
    print("[10] Computing brokerage", flush=True)
    step10_brokerage()

if __name__ == "__main__":
    main()
