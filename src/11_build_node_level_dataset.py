"""Stage 11: assemble the keyed node-level analytical dataset."""
from pipeline_lib import step11_node_dataset


def main() -> None:
    """Join analytical measures and write the data dictionary."""
    print("[11] Building node-level dataset", flush=True)
    step11_node_dataset()

if __name__ == "__main__":
    main()
