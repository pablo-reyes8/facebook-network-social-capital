"""Orquestador: ejecuta, registra y audita las 17 etapas."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("config",ROOT/"src"/"00_config.py")
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)

STEPS=[
 "01_extract_and_inventory.py","02_validate_raw_data.py","03_build_ego_graphs.py","04_parse_features.py",
 "05_construct_sample.py","06_descriptive_networks.py","07_detect_communities.py","08_compute_social_similarity.py",
 "09_compute_cohesion.py","10_compute_brokerage.py","11_build_node_level_dataset.py","12_statistical_analysis.py",
 "13_permutation_tests.py","14_robustness_checks.py","15_make_figures.py","16_make_tables.py","17_generate_sample_text.py"]

REQUIRED=[
 "outputs/1_data_inventory/file_inventory.csv","outputs/1_data_inventory/ego_file_matrix.csv","outputs/1_data_inventory/archive_summary.json","outputs/1_data_inventory/missing_files.csv",
 "outputs/1_data_inventory/data_quality_summary.csv","outputs/1_data_inventory/data_quality_by_ego.csv","outputs/1_data_inventory/invalid_edges.csv","outputs/1_data_inventory/invalid_feature_rows.csv","outputs/1_data_inventory/feature_dimension_check.csv","outputs/1_data_inventory/circle_validation.csv",
 "outputs/2_sample_definition/sample_flow.csv","outputs/2_sample_definition/sample_flow_by_ego.csv","outputs/2_sample_definition/exclusion_reasons.csv","outputs/2_sample_definition/feature_coverage_by_ego.csv","outputs/2_sample_definition/final_sample_summary.json","outputs/2_sample_definition/sample_definition.md","outputs/2_sample_definition/sample_definition.tex",
 "outputs/3_network_descriptives/graph_build_summary.csv","outputs/3_network_descriptives/network_summary_by_ego.csv","outputs/3_network_descriptives/network_summary_pooled.csv","outputs/3_network_descriptives/node_degree_distribution.csv","outputs/3_network_descriptives/components_by_ego.csv","outputs/3_network_descriptives/bridges_and_articulation.csv",
 "outputs/4_feature_descriptives/feature_categories_by_ego.csv","outputs/4_feature_descriptives/feature_prevalence.csv","outputs/4_feature_descriptives/feature_missingness.csv","outputs/4_feature_descriptives/feature_variation.csv","outputs/4_feature_descriptives/comparability_report.md",
 "outputs/5_communities/community_summary_by_ego.csv","outputs/5_communities/community_sizes.csv","outputs/5_communities/louvain_stability.csv","outputs/5_communities/community_circle_overlap.csv","outputs/5_communities/modularity_comparison.csv",
 "outputs/6_social_similarity/similarity_summary.csv","outputs/6_social_similarity/similarity_by_category.csv","outputs/6_social_similarity/diversity_summary.csv","outputs/6_social_similarity/within_vs_between_similarity.csv",
 "outputs/7_cohesion/cohesion_summary.csv","outputs/7_cohesion/cohesion_by_ego.csv","outputs/7_cohesion/cohesion_by_degree_bin.csv","outputs/7_cohesion/embeddedness_summary.csv",
 "outputs/8_brokerage/brokerage_summary.csv","outputs/8_brokerage/brokerage_by_ego.csv","outputs/8_brokerage/top_broker_nodes.csv","outputs/8_brokerage/top_degree_vs_top_betweenness.csv","outputs/8_brokerage/community_connector_roles.csv",
 "outputs/9_main_results/correlations.csv","outputs/9_main_results/regression_main.csv","outputs/9_main_results/regression_diagnostics.csv","outputs/9_main_results/model_fit_summary.csv","outputs/9_main_results/standardized_effects.csv","outputs/9_main_results/results_by_ego.csv",
 "outputs/10_null_models/permutation_statistics.csv","outputs/10_null_models/permutation_distributions.parquet","outputs/10_null_models/empirical_pvalues.csv","outputs/10_null_models/configuration_model_summary.csv","outputs/10_null_models/observed_vs_null.csv",
 "outputs/11_robustness/robustness_summary.csv","outputs/11_robustness/alternative_similarity.csv","outputs/11_robustness/alternative_diversity.csv","outputs/11_robustness/alternative_community_methods.csv","outputs/11_robustness/sample_restrictions.csv","outputs/11_robustness/bootstrap_results.csv",
 *[f"outputs/12_figures/fig_{n}.{ext}" for n in ["01_network_overview","02_similarity_clustering","03_diversity_betweenness","04_diversity_participation","05_degree_vs_brokerage","06_node_archetypes","07_community_structure","08a_null_similarity_clustering","08b_null_diversity_betweenness","08c_null_diversity_participation","09_heterogeneity_by_ego","10_robustness_specification_curve"] for ext in ["png","pdf"]],
 *[f"outputs/13_tables/tab_{n}.{ext}" for n in ["01_sample_flow","02_network_descriptives","03_node_descriptives","04_correlations","05_main_regressions","06_permutation_tests","07_results_by_ego","08_robustness","09_top_nodes"] for ext in ["csv","tex","md"]],
 "outputs/14_report_inputs/node_level_dictionary.csv","outputs/14_report_inputs/data_section_facts.md","outputs/14_report_inputs/data_section_facts.tex","outputs/14_report_inputs/methodology_facts.md","outputs/14_report_inputs/results_key_numbers.md","outputs/14_report_inputs/results_key_numbers.tex","outputs/14_report_inputs/result_interpretation_flags.json",
 "data_processed/node_features/node_features_long.csv","data_processed/node_features/node_features_wide.parquet","data_processed/node_features/feature_dictionary.csv","data_processed/communities/community_assignments.parquet","data_processed/analytic/edge_similarity.parquet","data_processed/analytic/node_similarity_diversity.parquet","data_processed/analytic/node_cohesion.parquet","data_processed/analytic/node_brokerage.parquet","data_processed/analytic/node_level_analysis.parquet","data_processed/analytic/node_level_analysis.csv"]


def write_config():
    values={k:v for k,v in vars(C).items() if k.isupper() and k not in ["OUTPUT_DIRS"]}
    values={k:(str(v.relative_to(ROOT)) if isinstance(v,Path) and ROOT in [v,*v.parents] else str(v) if isinstance(v,Path) else v) for k,v in values.items()}
    values["OUTPUT_DIRS"]={k:str(v.relative_to(ROOT)) for k,v in C.OUTPUT_DIRS.items()}
    (C.OUTPUT_DIRS["logs"]/"config_used.json").write_text(json.dumps(values,indent=2),encoding="utf-8")


def audit():
    checks=[]
    for rel in REQUIRED:
        p=ROOT/rel; ok=p.exists() and p.stat().st_size>0
        checks.append({"check_type":"required_output","target":rel,"status":"PASS" if ok else "FAIL","detail":f"{p.stat().st_size} bytes" if p.exists() else "missing"})
    try:
        df=pd.read_parquet(C.ANALYTIC/"node_level_analysis.parquet")
        for col in ["clustering","participation_coefficient","similarity_jaccard_mean","betweenness"]:
            s=df[col].dropna(); ok=((s>=-1e-12)&(s<=1+1e-12)).all()
            checks.append({"check_type":"range","target":col,"status":"PASS" if ok else "FAIL","detail":f"min={s.min():.6g}, max={s.max():.6g}"})
        ok=not df.duplicated(["ego_id","node_id"]).any();checks.append({"check_type":"uniqueness","target":"ego_id,node_id","status":"PASS" if ok else "FAIL","detail":f"duplicates={df.duplicated(['ego_id','node_id']).sum()}"})
        ok=(df.degree.dropna()>=0).all() and np.allclose(df.degree.dropna()%1,0);checks.append({"check_type":"range","target":"degree","status":"PASS" if ok else "FAIL","detail":f"min={df.degree.min()}, max={df.degree.max()}"})
        sf=pd.read_csv(C.OUTPUT_DIRS["sample"]/"sample_flow.csv").set_index("Stage"); counts=sf["Number of nodes"]
        structural=int(counts["A: structural"]); similarity=int(counts["B: social similarity"]); cohesion=int(counts["C: cohesion"]); brokerage=int(counts["D: brokerage"]); final=int(counts["E: main regressions"])
        ok=(similarity<=structural and cohesion<=similarity and brokerage<=similarity and final<=min(cohesion,brokerage))
        checks.append({"check_type":"sample_consistency","target":"sample_flow","status":"PASS" if ok else "FAIL",
                       "detail":"B within A; C and D within B; E within intersection(C,D)"})
    except Exception as e: checks.append({"check_type":"analytic_dataset","target":"node_level_analysis","status":"FAIL","detail":repr(e)})
    out=pd.DataFrame(checks);out.to_csv(C.OUTPUT_DIRS["logs"]/"final_audit.csv",index=False)
    failures=out.query("status=='FAIL'");text=f"# Final audit\n\n- Checks: {len(out)}\n- Passed: {(out.status=='PASS').sum()}\n- Failed: {len(failures)}\n- Critical status: {'PASS' if failures.empty else 'FAIL'}\n"
    if len(failures): text+="\n## Failures\n\n"+failures.to_markdown(index=False)+"\n"
    (C.OUTPUT_DIRS["logs"]/"final_audit.md").write_text(text,encoding="utf-8")
    return len(failures)==0


def versions():
    packages=["python","networkx","numpy","pandas","pyarrow","scipy","statsmodels","scikit-learn","matplotlib","seaborn","psutil","tabulate"]
    lines=[f"python=={platform.python_version()}",f"platform={platform.platform()}"]
    for p in packages[1:]:
        try: lines.append(f"{p}=={importlib.metadata.version(p)}")
        except importlib.metadata.PackageNotFoundError: lines.append(f"{p}==NOT_INSTALLED")
    (C.OUTPUT_DIRS["logs"]/"package_versions.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")


def main():
    for p in C.OUTPUT_DIRS.values():p.mkdir(parents=True,exist_ok=True)
    write_config();versions();statuses=[];log=[];warn=[]
    started=time.time()
    for step in STEPS:
        print(f"\n=== {step} ===",flush=True);t=time.time()
        proc=subprocess.run([sys.executable,str(ROOT/"src"/step)],cwd=ROOT,text=True,capture_output=True)
        elapsed=time.time()-t
        if proc.stdout: print(proc.stdout,end="");log.append(proc.stdout)
        if proc.stderr: print(proc.stderr,file=sys.stderr,end="");warn.append(f"[{step}]\n{proc.stderr}")
        statuses.append({"step":step,"status":"success" if proc.returncode==0 else "failed","return_code":proc.returncode,"runtime_seconds":elapsed})
        pd.DataFrame(statuses).to_csv(C.OUTPUT_DIRS["logs"]/"pipeline_status.csv",index=False)
        if proc.returncode:
            (C.OUTPUT_DIRS["logs"]/"pipeline.log").write_text("\n".join(log),encoding="utf-8");(C.OUTPUT_DIRS["logs"]/"warnings.log").write_text("\n".join(warn),encoding="utf-8")
            raise SystemExit(f"Critical failure in {step}")
    pd.DataFrame(statuses).to_csv(C.OUTPUT_DIRS["logs"]/"runtime_summary.csv",index=False)
    ok=audit()
    manifest=[]
    for p in sorted((ROOT/"outputs").rglob("*")):
        if p.is_file():manifest.append({"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"modified":time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime(p.stat().st_mtime))})
    pd.DataFrame(manifest).to_csv(C.OUTPUT_DIRS["logs"]/"output_manifest.csv",index=False)
    log.append(f"Pipeline completed in {time.time()-started:.2f} seconds; audit={'PASS' if ok else 'FAIL'}")
    (C.OUTPUT_DIRS["logs"]/"pipeline.log").write_text("\n".join(log),encoding="utf-8");(C.OUTPUT_DIRS["logs"]/"warnings.log").write_text("\n".join(warn) if warn else "No warnings captured.\n",encoding="utf-8")
    if not ok: raise SystemExit("Pipeline ran, but final audit failed")
    print(log[-1])

if __name__=="__main__":main()
