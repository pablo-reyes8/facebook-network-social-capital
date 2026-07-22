"""Stage 01: safely extract and inventory the Facebook source archive."""
from pipeline_lib import step01_inventory


def main() -> None:
    """Run source extraction and inventory generation."""
    print("[01] Extracting and inventorying", flush=True)
    step01_inventory()

if __name__ == "__main__":
    main()
