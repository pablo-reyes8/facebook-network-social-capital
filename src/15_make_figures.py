"""Stage 15: render title-free publication figures."""
from pipeline_lib import step15_figures


def main() -> None:
    """Export all figures as 300-dpi PNG and vector PDF."""
    print("[15] Rendering publication figures", flush=True)
    step15_figures()

if __name__ == "__main__":
    main()
