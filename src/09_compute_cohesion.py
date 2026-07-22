"""Stage 09: compute local cohesion and structural redundancy."""
from pipeline_lib import step09_cohesion


def main() -> None:
    """Build node-level closure and structural-hole measures."""
    print("[09] Computing local cohesion", flush=True)
    step09_cohesion()

if __name__ == "__main__":
    main()
