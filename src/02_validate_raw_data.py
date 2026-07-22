"""Stage 02: validate structural and attribute source-data contracts."""
from pipeline_lib import step02_validate


def main() -> None:
    """Run all raw-data validation checks."""
    print("[02] Validating raw data", flush=True)
    step02_validate()

if __name__ == "__main__":
    main()
