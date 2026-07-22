"""Single source of truth for reproducible pipeline configuration.

Environment variables are intentionally limited to operational switches. All
scientific defaults are committed to source control and copied to the run log.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data_raw"
DATA_PROCESSED = PROJECT_ROOT / "data_processed"
EXTRACTED = DATA_PROCESSED / "extracted_facebook" / "facebook"
GRAPHS = DATA_PROCESSED / "graphs"
NODE_FEATURES = DATA_PROCESSED / "node_features"
COMMUNITIES = DATA_PROCESSED / "communities"
ANALYTIC = DATA_PROCESSED / "analytic"
OUTPUTS = PROJECT_ROOT / "outputs"

RANDOM_SEED = 7745
N_PERMUTATIONS_MAIN = 1000
N_PERMUTATIONS_FAST = 200
USE_FAST_PERMUTATIONS = os.getenv("FACEBOOK_ANALYSIS_FAST", "0") == "1"
MIN_VALID_FEATURES_NODE = 1
MIN_NODES_EGO = 10
MIN_EDGES_EGO = 10
USE_LARGEST_CONNECTED_COMPONENT_FOR_PATHS = True
COMMUNITY_METHOD = "louvain"
COMMUNITY_RESOLUTION = 1.0
COMMUNITY_STABILITY_SEEDS = 20
BETWEENNESS_APPROX_THRESHOLD = 5000
BETWEENNESS_APPROX_K = 500
BOOTSTRAP_REPLICATIONS = 500
CONFIGURATION_MODEL_REPLICATIONS = 20
ALPHA = 0.05

OUTPUT_DIRS = {
    "logs": OUTPUTS / "0_logs",
    "inventory": OUTPUTS / "1_data_inventory",
    "sample": OUTPUTS / "2_sample_definition",
    "network": OUTPUTS / "3_network_descriptives",
    "features": OUTPUTS / "4_feature_descriptives",
    "communities": OUTPUTS / "5_communities",
    "similarity": OUTPUTS / "6_social_similarity",
    "cohesion": OUTPUTS / "7_cohesion",
    "brokerage": OUTPUTS / "8_brokerage",
    "results": OUTPUTS / "9_main_results",
    "null": OUTPUTS / "10_null_models",
    "robustness": OUTPUTS / "11_robustness",
    "figures": OUTPUTS / "12_figures",
    "tables": OUTPUTS / "13_tables",
    "report": OUTPUTS / "14_report_inputs",
}
