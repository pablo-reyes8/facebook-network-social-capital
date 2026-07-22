"""Stage 17: generate verified facts for research-report assembly."""
from pipeline_lib import step17_report_inputs


def main() -> None:
    """Write report-ready data, method, result, and interpretation inputs."""
    print("[17] Generating report inputs", flush=True)
    step17_report_inputs()

if __name__ == "__main__":
    main()
