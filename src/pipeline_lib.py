"""Funciones del pipeline de redes de Facebook.

Cada funcion corresponde a un ejercicio de la especificacion. Los calculos de
atributos se mantienen dentro de ego-red para no mezclar codigos anonimizados.
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import math
import pickle
import re
import shutil
import tarfile
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import scipy.stats as st
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.metrics import adjusted_rand_score
from statsmodels.stats.outliers_influence import variance_inflation_factor

_spec = importlib.util.spec_from_file_location("config", Path(__file__).with_name("00_config.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

pd.options.mode.copy_on_write = True
warnings.filterwarnings("default")


def ensure_dirs():
    for p in [C.DATA_RAW, C.DATA_PROCESSED, C.EXTRACTED.parent, C.GRAPHS,
              C.NODE_FEATURES, C.COMMUNITIES, C.ANALYTIC, *C.OUTPUT_DIRS.values()]:
        p.mkdir(parents=True, exist_ok=True)


def save_json(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def save_graph(g, path):
    with open(path, "wb") as f:
        pickle.dump(g, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_graph(ego, kind="full"):
    with open(C.GRAPHS / f"ego_{ego}_{kind}.gpickle", "rb") as f:
        return pickle.load(f)


def egos_from_extracted():
    return sorted(int(p.stem) for p in C.EXTRACTED.glob("*.edges"))


def read_edges(path):
    edges, invalid, seen, duplicate = [], [], set(), 0
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            parts = line.split()
            if len(parts) != 2 or not all(x.lstrip("-").isdigit() for x in parts):
                invalid.append((line_no, line.strip(), "invalid_format")); continue
            u, v = map(int, parts)
            if u == v:
                invalid.append((line_no, line.strip(), "self_loop")); continue
            edge = tuple(sorted((u, v)))
            if edge in seen:
                duplicate += 1; continue
            seen.add(edge); edges.append(edge)
    return edges, invalid, duplicate


def read_feat(ego):
    path = C.EXTRACTED / f"{ego}.feat"
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            values = [int(x) for x in line.split()]
            rows.append((values[0], values[1:]))
    ego_vec = [int(x) for x in (C.EXTRACTED / f"{ego}.egofeat").read_text().split()]
    rows.append((ego, ego_vec))
    width = max((len(v) for _, v in rows), default=0)
    arr = np.zeros((len(rows), width), dtype=np.uint8)
    nodes = []
    for i, (node, vec) in enumerate(rows):
        nodes.append(node); arr[i, :len(vec)] = vec
    return nodes, arr


def read_featnames(ego):
    rows = []
    pat = re.compile(r"^(\d+)\s+(.+)$")
    for line in (C.EXTRACTED / f"{ego}.featnames").read_text(encoding="utf-8").splitlines():
        m = pat.match(line)
        if not m:
            continue
        idx, label = int(m.group(1)), m.group(2)
        parts = label.split(";")
        rows.append({"ego_id": ego, "feature_index": idx,
                     "category": parts[0].strip().lower(),
                     "feature_label": label,
                     "anonymized_value": parts[-1].strip()})
    return pd.DataFrame(rows)


def read_circles(ego):
    circles = {}
    path = C.EXTRACTED / f"{ego}.circles"
    if not path.exists(): return circles
    for line in path.read_text(encoding="utf-8").splitlines():
        p = line.split()
        if p: circles[p[0]] = [int(x) for x in p[1:] if x.lstrip("-").isdigit()]
    return circles


def step01_inventory():
    """Copy immutable inputs, safely extract the archive, and inventory files."""
    ensure_dirs()
    for name in ["facebook.tar.gz", "facebook_combined.txt.gz", "readme-Ego.txt"]:
        src = C.PROJECT_ROOT / name
        dst = C.DATA_RAW / name
        if src.exists() and not dst.exists(): shutil.copy2(src, dst)
    marker = C.EXTRACTED / "0.edges"
    if not marker.exists():
        with tarfile.open(C.DATA_RAW / "facebook.tar.gz", "r:gz") as tf:
            root = C.EXTRACTED.parent.resolve()
            for member in tf.getmembers():
                target = (root / member.name).resolve()
                if root not in target.parents and target != root:
                    raise RuntimeError("Ruta insegura en archive")
            tf.extractall(C.EXTRACTED.parent, filter="data")
    files = []
    for p in sorted(C.EXTRACTED.glob("*")):
        if p.is_file():
            with open(p, encoding="utf-8") as handle:
                n_rows = sum(1 for _ in handle)
            files.append({"path": str(p.relative_to(C.PROJECT_ROOT)), "name": p.name,
                          "extension": p.suffix, "bytes": p.stat().st_size,
                          "rows": n_rows})
    pd.DataFrame(files).to_csv(C.OUTPUT_DIRS["inventory"] / "file_inventory.csv", index=False)
    ego_ids = sorted({int(p.name.split(".")[0]) for p in C.EXTRACTED.glob("*.*")})
    extensions = ["edges", "feat", "egofeat", "featnames", "circles"]
    matrix = []
    for ego in ego_ids:
        row = {"ego_id": ego}
        for ext in extensions: row[f"has_{ext}"] = (C.EXTRACTED / f"{ego}.{ext}").exists()
        matrix.append(row)
    mdf = pd.DataFrame(matrix)
    mdf.to_csv(C.OUTPUT_DIRS["inventory"] / "ego_file_matrix.csv", index=False)
    missing = mdf.melt("ego_id", var_name="file_type", value_name="present").query("not present")
    missing.to_csv(C.OUTPUT_DIRS["inventory"] / "missing_files.csv", index=False)
    with gzip.open(C.DATA_RAW / "facebook_combined.txt.gz", "rt") as f:
        combined_edges = [tuple(map(int, line.split())) for line in f if line.strip()]
    combined_nodes = set(x for e in combined_edges for x in e)
    save_json({"archive": "facebook.tar.gz", "n_files": len(files), "n_ego_networks": len(ego_ids),
               "ego_ids": ego_ids, "combined_nodes": len(combined_nodes),
               "combined_edges": len(set(tuple(sorted(e)) for e in combined_edges)),
               "extraction_directory": str(C.EXTRACTED.relative_to(C.PROJECT_ROOT))},
              C.OUTPUT_DIRS["inventory"] / "archive_summary.json")


def step02_validate():
    """Validate edge, feature, ego-feature, and circle source contracts."""
    summary, byego, invalid_edges, invalid_feat, dims, circle_rows = [], [], [], [], [], []
    for ego in egos_from_extracted():
        edges, invalid, dup = read_edges(C.EXTRACTED / f"{ego}.edges")
        for ln, raw, reason in invalid: invalid_edges.append({"ego_id": ego, "line": ln, "raw": raw, "reason": reason})
        feat_lines = [[int(x) for x in z.split()] for z in (C.EXTRACTED/f"{ego}.feat").read_text().splitlines() if z.strip()]
        ids = [r[0] for r in feat_lines]; widths = [len(r)-1 for r in feat_lines]
        fname = read_featnames(ego); expected = len(fname)
        vals = [x for r in feat_lines for x in r[1:]]
        bad_binary = sum(x not in (0,1) for x in vals)
        duplicate_nodes = len(ids) - len(set(ids))
        for node, row in zip(ids, feat_lines):
            if len(row)-1 != expected or any(x not in (0,1) for x in row[1:]):
                invalid_feat.append({"ego_id": ego, "node_id": node, "observed_dimension": len(row)-1,
                                     "expected_dimension": expected, "nonbinary": any(x not in (0,1) for x in row[1:])})
        ego_dim = len((C.EXTRACTED/f"{ego}.egofeat").read_text().split())
        edge_nodes = set(x for e in edges for x in e); feat_nodes = set(ids)
        circles = read_circles(ego); circ_nodes = set(x for v in circles.values() for x in v)
        circle_rows.append({"ego_id": ego, "n_circles": len(circles), "empty_circles": sum(not v for v in circles.values()),
                            "unknown_circle_nodes": len(circ_nodes-feat_nodes), "covered_feature_nodes": len(circ_nodes&feat_nodes),
                            "overlap_memberships": sum(map(len,circles.values()))-len(circ_nodes)})
        dims.append({"ego_id": ego, "expected_features": expected, "min_observed": min(widths),
                     "max_observed": max(widths), "ego_feature_dimension": ego_dim,
                     "dimensions_consistent": min(widths)==max(widths)==expected==ego_dim})
        row = {"ego_id": ego, "raw_edges": len(edges), "duplicate_edges": dup,
               "invalid_edges": len(invalid), "feature_nodes": len(feat_nodes),
               "edge_nodes_without_features": len(edge_nodes-feat_nodes),
               "feature_nodes_without_edges": len(feat_nodes-edge_nodes), "duplicate_feature_nodes": duplicate_nodes,
               "nonbinary_values": bad_binary, "feature_dimension": expected,
               "critical_error": not (min(widths)==max(widths)==expected==ego_dim) or duplicate_nodes>0}
        byego.append(row)
    pd.DataFrame(byego).to_csv(C.OUTPUT_DIRS["inventory"] / "data_quality_by_ego.csv", index=False)
    for metric in ["duplicate_edges","invalid_edges","edge_nodes_without_features","feature_nodes_without_edges","duplicate_feature_nodes","nonbinary_values"]:
        summary.append({"check": metric, "count": int(pd.DataFrame(byego)[metric].sum()), "status": "PASS" if pd.DataFrame(byego)[metric].sum()==0 else "WARNING"})
    summary.append({"check":"critical_errors", "count":sum(x["critical_error"] for x in byego),
                    "status":"PASS" if not any(x["critical_error"] for x in byego) else "FAIL"})
    pd.DataFrame(summary).to_csv(C.OUTPUT_DIRS["inventory"] / "data_quality_summary.csv", index=False)
    pd.DataFrame(invalid_edges, columns=["ego_id","line","raw","reason"]).to_csv(C.OUTPUT_DIRS["inventory"] / "invalid_edges.csv", index=False)
    pd.DataFrame(invalid_feat, columns=["ego_id","node_id","observed_dimension","expected_dimension","nonbinary"]).to_csv(C.OUTPUT_DIRS["inventory"] / "invalid_feature_rows.csv", index=False)
    pd.DataFrame(dims).to_csv(C.OUTPUT_DIRS["inventory"] / "feature_dimension_check.csv", index=False)
    pd.DataFrame(circle_rows).to_csv(C.OUTPUT_DIRS["inventory"] / "circle_validation.csv", index=False)


def step03_graphs():
    """Build full and largest-component undirected graphs for every ego."""
    rows=[]
    for ego in egos_from_extracted():
        edges, invalid, dup = read_edges(C.EXTRACTED / f"{ego}.edges")
        nodes, _ = read_feat(ego); alters = [n for n in nodes if n != ego]
        g=nx.Graph(); g.add_nodes_from(nodes); g.add_edges_from(edges); g.add_edges_from((ego,n) for n in alters)
        g.remove_edges_from(nx.selfloop_edges(g))
        components=sorted(nx.connected_components(g), key=len, reverse=True); lcc=g.subgraph(components[0]).copy()
        save_graph(g,C.GRAPHS/f"ego_{ego}_full.gpickle"); save_graph(lcc,C.GRAPHS/f"ego_{ego}_lcc.gpickle")
        deg=np.array([d for _,d in g.degree()])
        rows.append({"ego_id":ego,"n_nodes_full":g.number_of_nodes(),"n_edges_full":g.number_of_edges(),
                     "n_components":len(components),"largest_component_nodes":len(lcc),
                     "largest_component_share":len(lcc)/len(g),"density":nx.density(g),"mean_degree":deg.mean(),
                     "median_degree":np.median(deg),"max_degree":deg.max(),"isolates":nx.number_of_isolates(g),
                     "self_loops_removed":sum(1 for x in invalid if x[2]=="self_loop"),"duplicate_edges_removed":dup})
    pd.DataFrame(rows).to_csv(C.OUTPUT_DIRS["network"] / "graph_build_summary.csv",index=False)


def step04_features():
    """Parse ego-specific binary features and broad comparable categories."""
    long_rows=[]; wide=[]; dictionaries=[]; cats=[]; preval=[]; missing=[]; variations=[]
    for ego in egos_from_extracted():
        nodes, arr=read_feat(ego); d=read_featnames(ego); dictionaries.append(d)
        categories=d.groupby("category")["feature_index"].apply(list).to_dict()
        for cat, idx in categories.items():
            valid=[x for x in idx if x<arr.shape[1]]
            cats.append({"ego_id":ego,"category":cat,"n_features":len(valid),"n_nodes":len(nodes)})
            variations.append({"ego_id":ego,"category":cat,"varying_features":int(np.sum(np.ptp(arr[:,valid],axis=0)>0)),
                               "constant_features":int(np.sum(np.ptp(arr[:,valid],axis=0)==0))})
        for i,node in enumerate(nodes):
            active=np.flatnonzero(arr[i]).tolist()
            wide.append({"ego_id":ego,"node_id":node,"feature_vector":arr[i].tolist(),"n_active_features":len(active),
                         "has_features":len(active)>=C.MIN_VALID_FEATURES_NODE,"feature_dimension":arr.shape[1]})
            for idx in active:
                meta=d.loc[d.feature_index.eq(idx)]
                cat=meta.category.iloc[0] if len(meta) else "unknown"
                long_rows.append({"ego_id":ego,"node_id":node,"feature_index":idx,"category":cat,"value":1})
        for idx in range(arr.shape[1]):
            preval.append({"ego_id":ego,"feature_index":idx,"prevalence":float(arr[:,idx].mean()),"active_nodes":int(arr[:,idx].sum())})
        missing.append({"ego_id":ego,"n_nodes":len(nodes),"nodes_no_active_features":int(np.sum(arr.sum(1)==0)),
                        "share_no_active_features":float(np.mean(arr.sum(1)==0)),"feature_dimension":arr.shape[1]})
    pd.DataFrame(long_rows).to_csv(C.NODE_FEATURES/"node_features_long.csv",index=False)
    pd.DataFrame(wide).to_parquet(C.NODE_FEATURES/"node_features_wide.parquet",index=False)
    pd.concat(dictionaries,ignore_index=True).to_csv(C.NODE_FEATURES/"feature_dictionary.csv",index=False)
    pd.DataFrame(cats).to_csv(C.OUTPUT_DIRS["features"]/"feature_categories_by_ego.csv",index=False)
    pd.DataFrame(preval).to_csv(C.OUTPUT_DIRS["features"]/"feature_prevalence.csv",index=False)
    pd.DataFrame(missing).to_csv(C.OUTPUT_DIRS["features"]/"feature_missingness.csv",index=False)
    pd.DataFrame(variations).to_csv(C.OUTPUT_DIRS["features"]/"feature_variation.csv",index=False)
    common=set.intersection(*(set(x.category) for x in dictionaries))
    text=("# Comparability report\n\nFeature values are anonymized and their column meanings are ego-specific. "
          "Consequently, vectors are compared only within each ego-network; pooled models retain `ego_id` and fixed effects. "
          f"General categories shared by all {len(dictionaries)} networks are: {', '.join(sorted(common))}. "
          "Category labels are comparable at the broad level, but anonymized values are not assumed to match across networks.\n")
    (C.OUTPUT_DIRS["features"]/"comparability_report.md").write_text(text,encoding="utf-8")


def step05_sample():
    """Apply predefined network/node eligibility rules and document samples."""
    quality=pd.read_csv(C.OUTPUT_DIRS["inventory"]/"data_quality_by_ego.csv")
    build=pd.read_csv(C.OUTPUT_DIRS["network"]/"graph_build_summary.csv")
    features=pd.read_parquet(C.NODE_FEATURES/"node_features_wide.parquet")
    eligible=[]; flags=[]; exclusions=[]; coverage=[]
    for ego in egos_from_extracted():
        q=quality.query("ego_id==@ego").iloc[0]; b=build.query("ego_id==@ego").iloc[0]; f=features.query("ego_id==@ego")
        ok=bool(not q.critical_error and b.n_nodes_full>=C.MIN_NODES_EGO and b.n_edges_full>=C.MIN_EDGES_EGO and f.has_features.any())
        reason="included" if ok else "failed_file_alignment_or_minimum_size"
        eligible.append({"ego_id":ego,"eligible":ok,"reason":reason,"n_nodes":int(b.n_nodes_full),"n_edges":int(b.n_edges_full)})
        g=load_graph(ego); lcc=set(max(nx.connected_components(g),key=len)); fmap=f.set_index("node_id").to_dict("index")
        valid_nodes={n for n,r in fmap.items() if r["has_features"]}
        for n in g:
            has=n in valid_nodes; valid_neighbor=any(v in valid_nodes for v in g.neighbors(n)); degree=g.degree(n)
            sim=ok and has and degree>=1 and valid_neighbor
            cl=sim and degree>=2; btw=sim and n in lcc
            main=cl and btw
            why="included" if main else ("ego_network_ineligible" if not ok else "no_active_features" if not has else "no_feature_valid_neighbor" if not valid_neighbor else "degree_below_two" if degree<2 else "outside_lcc")
            flags.append({"ego_id":ego,"node_id":n,"in_full_graph":True,"in_lcc":n in lcc,"has_features":has,
                          "n_active_features":int(fmap.get(n,{}).get("n_active_features",0)),"degree":degree,
                          "eligible_similarity":sim,"eligible_clustering":cl,"eligible_betweenness":btw,
                          "eligible_main_regression":main,"exclusion_reason":why})
            if why!="included": exclusions.append({"ego_id":ego,"node_id":n,"reason":why})
        coverage.append({"ego_id":ego,"nodes_total":len(g),"nodes_with_active_features":len(valid_nodes),
                         "feature_coverage":len(valid_nodes)/len(g),"feature_dimension":int(f.feature_dimension.max()),"eligible_ego":ok})
    ef=pd.DataFrame(eligible); ff=pd.DataFrame(flags)
    ef.to_csv(C.ANALYTIC/"eligible_egos.csv",index=False); ff[["ego_id","node_id"]].to_csv(C.ANALYTIC/"eligible_nodes.csv",index=False)
    ff.to_parquet(C.ANALYTIC/"node_sample_flags.parquet",index=False)
    pd.DataFrame(exclusions,columns=["ego_id","node_id","reason"]).to_csv(C.OUTPUT_DIRS["sample"]/"exclusion_reasons.csv",index=False)
    pd.DataFrame(coverage).to_csv(C.OUTPUT_DIRS["sample"]/"feature_coverage_by_ego.csv",index=False)
    raw_unique_edges=sum(len(read_edges(C.EXTRACTED/f"{e}.edges")[0]) for e in egos_from_extracted())
    raw_edge_lines=0
    for e in egos_from_extracted():
        with open(C.EXTRACTED/f"{e}.edges",encoding="utf-8") as handle:
            raw_edge_lines += sum(1 for _ in handle)
    stages=[("Raw universe",np.ones(len(ff),bool),raw_unique_edges,"None; undirected alter--alter ties deduplicated"),
            ("A: structural",ff.ego_id.isin(ef.query("eligible").ego_id),None,"Ego links added; all structurally valid nodes retained"),
            ("B: social similarity",ff.eligible_similarity,None,"Missing usable attributes or feature-valid neighbor"),
            ("C: cohesion",ff.eligible_clustering,None,"Sample B plus degree >= 2"),
            ("D: brokerage",ff.eligible_betweenness,None,"Sample B plus membership in path-analysis LCC"),
            ("E: main regressions",ff.eligible_main_regression,None,"Intersection of required analytical variables")]
    flow=[]
    for name,mask,edge_override,reason in stages:
        sub=ff[mask]; egos=sub.ego_id.nunique(); edges=edge_override if edge_override is not None else sum(load_graph(e).number_of_edges() for e in sub.ego_id.unique())
        flow.append({"Stage":name,"Number of ego-networks":egos,"Number of nodes":len(sub),"Number of edges":edges,
                     "Nodes excluded":len(ff)-len(sub),"Reason":reason,"Share retained":len(sub)/len(ff)})
    flowdf=pd.DataFrame(flow); flowdf.to_csv(C.OUTPUT_DIRS["sample"]/"sample_flow.csv",index=False)
    by=[]
    for ego,x in ff.groupby("ego_id"):
        by.append({"ego_id":ego,"structural_nodes":len(x),"similarity_nodes":int(x.eligible_similarity.sum()),
                   "cohesion_nodes":int(x.eligible_clustering.sum()),"brokerage_nodes":int(x.eligible_betweenness.sum()),
                   "main_regression_nodes":int(x.eligible_main_regression.sum()),"edges":load_graph(ego).number_of_edges()})
    pd.DataFrame(by).to_csv(C.OUTPUT_DIRS["sample"]/"sample_flow_by_ego.csv",index=False)
    final={"raw_ego_networks":int(ff.ego_id.nunique()),"raw_node_records":len(ff),
           "raw_unique_nodes":int(ff.node_id.nunique()),"raw_edge_lines":int(raw_edge_lines),
           "raw_ego_edge_records":int(raw_unique_edges),"constructed_ego_edge_records":int(flowdf.iloc[1]["Number of edges"]),
           "eligible_ego_networks":int(ef.eligible.sum()),"sample_A_nodes":int(stages[1][1].sum()),
           "sample_B_nodes":int(ff.eligible_similarity.sum()),"sample_C_nodes":int(ff.eligible_clustering.sum()),
           "sample_D_nodes":int(ff.eligible_betweenness.sum()),"sample_E_nodes":int(ff.eligible_main_regression.sum()),
           "unit_of_analysis":"node record within ego-network"}
    save_json(final,C.OUTPUT_DIRS["sample"]/"final_sample_summary.json")
    paragraph=(f"The raw dataset contains {final['raw_ego_networks']} ego-networks, {final['raw_node_records']:,} node--ego records "
               f"({final['raw_unique_nodes']:,} distinct anonymized IDs), and {final['raw_ego_edge_records']:,} unique alter--alter ties counted within ego-network "
               f"({final['raw_edge_lines']:,} raw directed line records). Adding the documented ego--alter links produces {final['constructed_ego_edge_records']:,} ties in the constructed graphs. "
               f"After applying file-alignment, minimum-size, and feature-coverage criteria, {final['eligible_ego_networks']} ego-networks remain. "
               f"The structural sample contains {final['sample_A_nodes']:,} records; the similarity, cohesion, brokerage, and final regression samples contain "
               f"{final['sample_B_nodes']:,}, {final['sample_C_nodes']:,}, {final['sample_D_nodes']:,}, and {final['sample_E_nodes']:,} records, respectively. "
               "Nodes without usable attributes remain in graphs for structural calculations but are excluded from social-similarity measures.\n")
    (C.OUTPUT_DIRS["sample"]/"sample_definition.md").write_text("# Sample definition\n\n"+paragraph,encoding="utf-8")
    tex=paragraph.replace("%",r"\%").replace("--",r"--")
    (C.OUTPUT_DIRS["sample"]/"sample_definition.tex").write_text(tex,encoding="utf-8")


def step06_descriptives():
    """Compute network-level and node-level structural descriptions."""
    summaries=[]; degrees=[]; components=[]; bridge_rows=[]
    for ego in pd.read_csv(C.ANALYTIC/"eligible_egos.csv").query("eligible").ego_id.astype(int):
        g=load_graph(ego); lcc=load_graph(ego,"lcc")
        deg=np.array([d for _,d in g.degree()]); cluster=nx.clustering(g); tri=nx.triangles(g)
        comps=sorted((len(c) for c in nx.connected_components(g)),reverse=True)
        bridges=list(nx.bridges(g)); arts=list(nx.articulation_points(g))
        try: assort=nx.degree_assortativity_coefficient(g)
        except Exception: assort=np.nan
        summaries.append({"ego_id":ego,"nodes":len(g),"edges":g.number_of_edges(),"density":nx.density(g),
                          "components":len(comps),"largest_component_nodes":len(lcc),"largest_component_share":len(lcc)/len(g),
                          "mean_degree":deg.mean(),"median_degree":np.median(deg),"max_degree":deg.max(),"sd_degree":deg.std(ddof=1),
                          "mean_clustering":np.mean(list(cluster.values())),"transitivity":nx.transitivity(g),"degree_assortativity":assort,
                          "diameter_lcc":nx.diameter(lcc),"avg_shortest_path_lcc":nx.average_shortest_path_length(lcc),
                          "triangles":sum(tri.values())//3,"share_nodes_in_triangles":np.mean(np.array(list(tri.values()))>0),
                          "bridges":len(bridges),"articulation_points":len(arts)})
        for n,d in g.degree(): degrees.append({"ego_id":ego,"node_id":n,"degree":d,"clustering":cluster[n],"triangles":tri[n]})
        for rank,size in enumerate(comps,1): components.append({"ego_id":ego,"component_rank":rank,"size":size,"share":size/len(g)})
        for u,v in bridges: bridge_rows.append({"ego_id":ego,"record_type":"bridge","node_u":u,"node_v":v})
        for n in arts: bridge_rows.append({"ego_id":ego,"record_type":"articulation_point","node_u":n,"node_v":np.nan})
    sdf=pd.DataFrame(summaries); sdf.to_csv(C.OUTPUT_DIRS["network"]/"network_summary_by_ego.csv",index=False)
    pooled={"ego_networks":len(sdf),"node_records":int(sdf.nodes.sum()),"edge_records":int(sdf.edges.sum())}
    for col in sdf.select_dtypes("number").columns:
        if col!="ego_id": pooled[f"mean_{col}"]=float(sdf[col].mean())
    pd.DataFrame([pooled]).to_csv(C.OUTPUT_DIRS["network"]/"network_summary_pooled.csv",index=False)
    pd.DataFrame(degrees).to_csv(C.OUTPUT_DIRS["network"]/"node_degree_distribution.csv",index=False)
    pd.DataFrame(components).to_csv(C.OUTPUT_DIRS["network"]/"components_by_ego.csv",index=False)
    pd.DataFrame(bridge_rows,columns=["ego_id","record_type","node_u","node_v"]).to_csv(C.OUTPUT_DIRS["network"]/"bridges_and_articulation.csv",index=False)


def _partition_map(communities):
    return {n:i for i,c in enumerate(communities) for n in c}


def step07_communities():
    """Select stable Louvain partitions and compare alternative groupings."""
    assignments=[]; summaries=[]; sizes=[]; stability=[]; overlaps=[]; comparisons=[]
    for ego in pd.read_csv(C.ANALYTIC/"eligible_egos.csv").query("eligible").ego_id.astype(int):
        g=load_graph(ego); runs=[]
        for j in range(C.COMMUNITY_STABILITY_SEEDS):
            seed=C.RANDOM_SEED+j
            comm=list(nx.community.louvain_communities(g,seed=seed,resolution=C.COMMUNITY_RESOLUTION))
            mod=nx.community.modularity(g,comm,resolution=C.COMMUNITY_RESOLUTION)
            runs.append((mod,seed,comm,_partition_map(comm)))
        runs.sort(key=lambda x:x[0],reverse=True); mod,seed,comm,pmap=runs[0]
        nodes=sorted(g.nodes()); ref=[pmap[n] for n in nodes]
        for m,s,c,pm in runs:
            stability.append({"ego_id":ego,"seed":s,"modularity":m,"n_communities":len(c),
                              "ari_vs_selected":adjusted_rand_score(ref,[pm[n] for n in nodes])})
        greedy=list(nx.community.greedy_modularity_communities(g)); gmod=nx.community.modularity(g,greedy)
        comparisons.extend([{"ego_id":ego,"method":"louvain","modularity":mod,"n_communities":len(comm)},
                            {"ego_id":ego,"method":"greedy_modularity","modularity":gmod,"n_communities":len(greedy)}])
        for cid,cset in enumerate(comm):
            sizes.append({"ego_id":ego,"community_id":cid,"size":len(cset),"share":len(cset)/len(g)})
            for n in cset: assignments.append({"ego_id":ego,"node_id":n,"community_id":cid,"selected_seed":seed})
        cuts=[]
        for cset in comm:
            if len(cset) and len(cset)<len(g): cuts.append(nx.conductance(g,cset))
        summaries.append({"ego_id":ego,"n_communities":len(comm),"modularity":mod,"selected_seed":seed,
                          "mean_conductance":np.mean(cuts) if cuts else np.nan,"mean_ari_stability":np.mean([x["ari_vs_selected"] for x in stability if x["ego_id"]==ego])})
        circles=read_circles(ego)
        for cname,cnodes in circles.items():
            cs=set(cnodes)&set(g)
            if not cs: continue
            best=None
            for cid,cset in enumerate(comm):
                inter=len(cs&set(cset)); union=len(cs|set(cset)); precision=inter/len(cset); recall=inter/len(cs)
                vals={"ego_id":ego,"circle":cname,"community_id":cid,"jaccard":inter/union,"precision":precision,
                      "recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0}
                if best is None or vals["jaccard"]>best["jaccard"]: best=vals
            overlaps.append(best)
    pd.DataFrame(assignments).to_parquet(C.COMMUNITIES/"community_assignments.parquet",index=False)
    pd.DataFrame(summaries).to_csv(C.OUTPUT_DIRS["communities"]/"community_summary_by_ego.csv",index=False)
    pd.DataFrame(sizes).to_csv(C.OUTPUT_DIRS["communities"]/"community_sizes.csv",index=False)
    pd.DataFrame(stability).to_csv(C.OUTPUT_DIRS["communities"]/"louvain_stability.csv",index=False)
    pd.DataFrame(overlaps).to_csv(C.OUTPUT_DIRS["communities"]/"community_circle_overlap.csv",index=False)
    pd.DataFrame(comparisons).to_csv(C.OUTPUT_DIRS["communities"]/"modularity_comparison.csv",index=False)


def _entropy(values):
    if len(values)==0: return np.nan
    counts=np.array(list(Counter(values).values()),float)
    if len(counts)<=1:return 0.0
    p=counts/counts.sum(); return float(-(p*np.log(p)).sum()/np.log(len(counts)))


def step08_similarity():
    """Measure within-ego edge similarity and node neighborhood diversity."""
    fwide=pd.read_parquet(C.NODE_FEATURES/"node_features_wide.parquet")
    fdict=pd.read_csv(C.NODE_FEATURES/"feature_dictionary.csv")
    edge_rows=[]; node_rows=[]
    for ego in pd.read_csv(C.ANALYTIC/"eligible_egos.csv").query("eligible").ego_id.astype(int):
        g=load_graph(ego); f=fwide.query("ego_id==@ego"); nodes=f.node_id.astype(int).tolist()
        arr=np.asarray(f.feature_vector.tolist(),dtype=np.uint8); ix={n:i for i,n in enumerate(nodes)}
        valid={n for n,a in zip(nodes,arr) if a.sum()>=C.MIN_VALID_FEATURES_NODE}
        cats=fdict.query("ego_id==@ego").groupby("category").feature_index.apply(list).to_dict()
        node_vals=defaultdict(lambda:{"j":[],"cos":[],"cat":defaultdict(list)})
        for u,v in g.edges():
            if u not in valid or v not in valid: continue
            a,b=arr[ix[u]],arr[ix[v]]; inter=int(np.logical_and(a,b).sum()); union=int(np.logical_or(a,b).sum())
            jac=inter/union if union else np.nan; cos=inter/math.sqrt(int(a.sum())*int(b.sum()))
            er={"ego_id":ego,"node_u":u,"node_v":v,"jaccard":jac,"cosine":cos,"active_intersection":inter,"active_union":union}
            for cat,idxs in cats.items():
                idx=[z for z in idxs if z<arr.shape[1]]
                if not idx: continue
                aa,bb=a[idx],b[idx]; un=np.logical_or(aa,bb).sum(); val=np.logical_and(aa,bb).sum()/un if un else np.nan
                er[f"similarity_{cat}"]=val
                if np.isfinite(val): node_vals[u]["cat"][cat].append(val); node_vals[v]["cat"][cat].append(val)
            edge_rows.append(er); node_vals[u]["j"].append(jac);node_vals[v]["j"].append(jac);node_vals[u]["cos"].append(cos);node_vals[v]["cos"].append(cos)
        circles=read_circles(ego); membership=defaultdict(list)
        for c,ns in circles.items():
            for n in ns: membership[n].append(c)
        for n in g:
            vals=np.array(node_vals[n]["j"],float); cv=np.array(node_vals[n]["cos"],float)
            neigh=[v for v in g.neighbors(n) if v in valid]
            entropies=[]
            for cat,idxs in cats.items():
                idx=[z for z in idxs if z<arr.shape[1]]
                if not idx or not neigh: continue
                signatures=[tuple(np.flatnonzero(arr[ix[v],idx]).tolist()) for v in neigh]
                entropies.append(_entropy(signatures))
            circlabels=[membership[v][0] if membership[v] else "unassigned" for v in neigh]
            ncirc=set(x for v in neigh for x in membership[v])
            row={"ego_id":ego,"node_id":n,"valid_neighbor_count":len(vals),
                 "similarity_jaccard_mean":np.nanmean(vals) if len(vals) else np.nan,
                 "similarity_jaccard_median":np.nanmedian(vals) if len(vals) else np.nan,
                 "similarity_jaccard_min":np.nanmin(vals) if len(vals) else np.nan,"similarity_jaccard_max":np.nanmax(vals) if len(vals) else np.nan,
                 "similarity_jaccard_sd":np.nanstd(vals,ddof=1) if len(vals)>1 else 0 if len(vals)==1 else np.nan,
                 "similarity_cosine_mean":np.nanmean(cv) if len(cv) else np.nan,
                 "share_positive_similarity":np.mean(vals>0) if len(vals) else np.nan,
                 "diversity_complement":1-np.nanmean(vals) if len(vals) else np.nan,
                 "diversity_category_entropy":np.nanmean(entropies) if entropies else np.nan,
                 "circles_reached":len(ncirc),"circle_entropy":_entropy(circlabels),
                 "outside_dominant_circle_share":1-max(Counter(circlabels).values())/len(circlabels) if circlabels else np.nan}
            for cat,v in node_vals[n]["cat"].items(): row[f"similarity_{cat}_mean"]=np.mean(v)
            node_rows.append(row)
    edf=pd.DataFrame(edge_rows); ndf=pd.DataFrame(node_rows)
    edf.to_parquet(C.ANALYTIC/"edge_similarity.parquet",index=False); ndf.to_parquet(C.ANALYTIC/"node_similarity_diversity.parquet",index=False)
    def describe_frame(df,cols):
        out=[]
        for col in cols:
            if col in df:
                s=df[col].dropna(); out.append({"variable":col,"n":len(s),"mean":s.mean(),"sd":s.std(),"min":s.min(),"median":s.median(),"max":s.max()})
        return pd.DataFrame(out)
    describe_frame(ndf,["similarity_jaccard_mean","similarity_cosine_mean","share_positive_similarity"]).to_csv(C.OUTPUT_DIRS["similarity"]/"similarity_summary.csv",index=False)
    catcols=[x for x in ndf if x.startswith("similarity_") and x.endswith("_mean") and x not in ("similarity_jaccard_mean","similarity_cosine_mean")]
    describe_frame(ndf,catcols).to_csv(C.OUTPUT_DIRS["similarity"]/"similarity_by_category.csv",index=False)
    describe_frame(ndf,["diversity_complement","diversity_category_entropy","circles_reached","circle_entropy","outside_dominant_circle_share"]).to_csv(C.OUTPUT_DIRS["similarity"]/"diversity_summary.csv",index=False)
    comm=pd.read_parquet(C.COMMUNITIES/"community_assignments.parquet"); em=edf.merge(comm.rename(columns={"node_id":"node_u","community_id":"cu"})[["ego_id","node_u","cu"]],on=["ego_id","node_u"]).merge(comm.rename(columns={"node_id":"node_v","community_id":"cv"})[["ego_id","node_v","cv"]],on=["ego_id","node_v"])
    em["edge_type"]=np.where(em.cu==em.cv,"within_community","between_community")
    em.groupby(["ego_id","edge_type"]).jaccard.agg(["count","mean","std","median"]).reset_index().to_csv(C.OUTPUT_DIRS["similarity"]/"within_vs_between_similarity.csv",index=False)


def step09_cohesion():
    """Measure local closure, embeddedness, and structural redundancy."""
    rows=[]
    for ego in pd.read_csv(C.ANALYTIC/"eligible_egos.csv").query("eligible").ego_id.astype(int):
        g=load_graph(ego); cl=nx.clustering(g); tri=nx.triangles(g); constraint=nx.constraint(g); eff=nx.effective_size(g)
        for n in g:
            neigh=list(g.neighbors(n)); embedded=[len(set(g.neighbors(n))&set(g.neighbors(v))) for v in neigh]
            d=len(neigh); es=eff.get(n,np.nan)
            rows.append({"ego_id":ego,"node_id":n,"degree":d,"clustering":cl[n],"ego_density":cl[n],"triangles":tri[n],
                         "avg_edge_embeddedness":np.mean(embedded) if embedded else np.nan,"constraint":constraint.get(n,np.nan),
                         "effective_size":es,"efficiency":es/d if d else np.nan})
    df=pd.DataFrame(rows); df.to_parquet(C.ANALYTIC/"node_cohesion.parquet",index=False)
    metrics=["clustering","ego_density","triangles","avg_edge_embeddedness","constraint","effective_size","efficiency"]
    desc=df[metrics].describe().T.reset_index(names="variable"); desc.to_csv(C.OUTPUT_DIRS["cohesion"]/"cohesion_summary.csv",index=False)
    df.groupby("ego_id")[metrics].agg(["count","mean","std","median"]).reset_index().to_csv(C.OUTPUT_DIRS["cohesion"]/"cohesion_by_ego.csv",index=False)
    df["degree_bin"]=pd.qcut(df.degree.rank(method="first"),5,labels=["Q1","Q2","Q3","Q4","Q5"])
    df.groupby("degree_bin",observed=True)[metrics].mean().reset_index().to_csv(C.OUTPUT_DIRS["cohesion"]/"cohesion_by_degree_bin.csv",index=False)
    df.groupby("ego_id").avg_edge_embeddedness.agg(["count","mean","std","median","min","max"]).reset_index().to_csv(C.OUTPUT_DIRS["cohesion"]/"embeddedness_summary.csv",index=False)


def step10_brokerage():
    """Measure shortest-path, inter-community, and structural-hole brokerage."""
    comm=pd.read_parquet(C.COMMUNITIES/"community_assignments.parquet"); rows=[]
    for ego in pd.read_csv(C.ANALYTIC/"eligible_egos.csv").query("eligible").ego_id.astype(int):
        g=load_graph(ego); lcc=load_graph(ego,"lcc"); pmap=comm.query("ego_id==@ego").set_index("node_id").community_id.to_dict()
        if len(lcc)>C.BETWEENNESS_APPROX_THRESHOLD:
            btw=nx.betweenness_centrality(lcc,k=min(C.BETWEENNESS_APPROX_K,len(lcc)),normalized=True,seed=C.RANDOM_SEED); method="approximate"
        else: btw=nx.betweenness_centrality(lcc,normalized=True); method="exact"
        arts=set(nx.articulation_points(g)); bridge_nodes=set(x for e in nx.bridges(g) for x in e)
        within=defaultdict(dict)
        for cid,nodes in comm.query("ego_id==@ego").groupby("community_id").node_id:
            vals={n:sum(pmap.get(v)==cid for v in g.neighbors(n)) for n in nodes}
            mu=np.mean(list(vals.values())); sd=np.std(list(vals.values()))
            for n,val in vals.items(): within[cid][n]=(val-mu)/sd if sd else 0.0
        constraint=nx.constraint(g); eff=nx.effective_size(g)
        for n in g:
            d=g.degree(n); counts=Counter(pmap.get(v) for v in g.neighbors(n)); part=1-sum((x/d)**2 for x in counts.values()) if d else 0
            bc=(1/d)/sum(1/g.degree(v) for v in g.neighbors(n)) if d and all(g.degree(v)>0 for v in g.neighbors(n)) else 0
            rows.append({"ego_id":ego,"node_id":n,"betweenness":btw.get(n,np.nan),"betweenness_method":method,
                         "participation_coefficient":part,"communities_reached":len(counts),"within_module_degree_z":within[pmap[n]].get(n,0),
                         "incident_bridge":n in bridge_nodes,"articulation_point":n in arts,"multi_community_connector":len(counts)>=2,
                         "bridging_coefficient":bc,"constraint_brokerage":constraint.get(n,np.nan),"effective_size_brokerage":eff.get(n,np.nan),
                         "efficiency_brokerage":eff.get(n,np.nan)/d if d else np.nan})
    df=pd.DataFrame(rows); df.to_parquet(C.ANALYTIC/"node_brokerage.parquet",index=False)
    metrics=["betweenness","participation_coefficient","communities_reached","within_module_degree_z","bridging_coefficient","constraint_brokerage","effective_size_brokerage","efficiency_brokerage"]
    df[metrics].describe().T.reset_index(names="variable").to_csv(C.OUTPUT_DIRS["brokerage"]/"brokerage_summary.csv",index=False)
    df.groupby("ego_id")[metrics].agg(["count","mean","std","median","max"]).reset_index().to_csv(C.OUTPUT_DIRS["brokerage"]/"brokerage_by_ego.csv",index=False)
    deg=pd.read_csv(C.OUTPUT_DIRS["network"]/"node_degree_distribution.csv")[["ego_id","node_id","degree"]]
    merged=df.merge(deg,on=["ego_id","node_id"])
    merged.sort_values("betweenness",ascending=False).head(100).to_csv(C.OUTPUT_DIRS["brokerage"]/"top_broker_nodes.csv",index=False)
    merged["degree_rank"]=merged.groupby("ego_id").degree.rank(ascending=False,method="min"); merged["betweenness_rank"]=merged.groupby("ego_id").betweenness.rank(ascending=False,method="min")
    merged.sort_values(["ego_id","betweenness_rank"]).groupby("ego_id").head(20).to_csv(C.OUTPUT_DIRS["brokerage"]/"top_degree_vs_top_betweenness.csv",index=False)
    roles=np.select([merged.within_module_degree_z>=2.5,merged.participation_coefficient>=.62,merged.participation_coefficient>=.3],
                    ["provincial_hub","connector","peripheral_connector"],default="peripheral")
    merged.assign(connector_role=roles).to_csv(C.OUTPUT_DIRS["brokerage"]/"community_connector_roles.csv",index=False)


def step11_node_dataset():
    """Assemble the keyed analytical dataset and its variable dictionary."""
    flags=pd.read_parquet(C.ANALYTIC/"node_sample_flags.parquet")
    sim=pd.read_parquet(C.ANALYTIC/"node_similarity_diversity.parquet")
    coh=pd.read_parquet(C.ANALYTIC/"node_cohesion.parquet")
    bro=pd.read_parquet(C.ANALYTIC/"node_brokerage.parquet")
    com=pd.read_parquet(C.COMMUNITIES/"community_assignments.parquet")
    df=flags.merge(sim,on=["ego_id","node_id"],how="left").merge(coh,on=["ego_id","node_id","degree"],how="left").merge(bro,on=["ego_id","node_id"],how="left").merge(com[["ego_id","node_id","community_id"]],on=["ego_id","node_id"],how="left")
    csum=pd.read_csv(C.OUTPUT_DIRS["communities"]/"community_summary_by_ego.csv")[["ego_id","n_communities","modularity"]]
    nsum=pd.read_csv(C.OUTPUT_DIRS["network"]/"network_summary_by_ego.csv")[["ego_id","nodes","edges","density"]]
    df=df.merge(csum,on="ego_id",how="left").merge(nsum,on="ego_id",how="left",suffixes=("","_ego"))
    required=["similarity_jaccard_mean","diversity_complement","clustering","betweenness","participation_coefficient"]
    df["eligible_main_regression"] = df[required].notna().all(axis=1) & (df.degree>=2) & df.in_lcc
    df["log_degree"] = np.log1p(df.degree); df["log_betweenness"] = np.log1p(df.betweenness)
    df["record_id"]=df.ego_id.astype(str)+":"+df.node_id.astype(str)
    if df.duplicated(["ego_id","node_id"]).any(): raise RuntimeError("Duplicados en llave ego_id-node_id")
    df.to_parquet(C.ANALYTIC/"node_level_analysis.parquet",index=False); df.to_csv(C.ANALYTIC/"node_level_analysis.csv",index=False)
    definitions={
      "ego_id":("Ego-network identifier","identifier","raw graph"),"node_id":("Anonymized node identifier","identifier","raw graph"),
      "degree":("Number of adjacent nodes","count","network"),"similarity_jaccard_mean":("Mean Jaccard similarity to feature-valid neighbors","[0,1]","features and network"),
      "diversity_complement":("One minus mean Jaccard similarity","[0,1]","derived"),"diversity_category_entropy":("Mean normalized entropy of neighbor category signatures","[0,1]","derived"),
      "clustering":("Fraction of possible ties among neighbors observed","[0,1]","network"),"ego_density":("Density among focal node's neighbors; equals local clustering in an undirected graph","[0,1]","network"),
      "betweenness":("Normalized share of geodesics crossing node","[0,1]","network"),"participation_coefficient":("Dispersion of edges across detected communities","[0,1]","network and communities"),
      "communities_reached":("Distinct detected communities among neighbors","count","network and communities"),"constraint":("Burt network constraint","[0,1+]","network"),
      "effective_size":("Burt effective size","nonnegative","network"),"community_id":("Selected Louvain community within ego-network","identifier","communities")}
    dictionary=[]
    for col in df.columns:
        desc,rng,source=definitions.get(col,(col.replace("_"," ").capitalize(),"variable-dependent","pipeline"))
        dictionary.append({"variable":col,"definition":desc,"formula":"See methodology specification","range":rng,"type":str(df[col].dtype),"source":source,"notes":"Computed within ego-network where applicable"})
    pd.DataFrame(dictionary).to_csv(C.OUTPUT_DIRS["report"]/"node_level_dictionary.csv",index=False)


def _bootstrap_corr(x,y,method="spearman",reps=None,seed=C.RANDOM_SEED):
    z=pd.DataFrame({"x":x,"y":y}).dropna(); n=len(z)
    if n<4:return (np.nan,np.nan)
    rng=np.random.default_rng(seed); vals=[]
    reps=reps or C.BOOTSTRAP_REPLICATIONS
    a=z.x.to_numpy(); b=z.y.to_numpy()
    for _ in range(reps):
        ix=rng.integers(0,n,n)
        vals.append(st.spearmanr(a[ix],b[ix]).statistic if method=="spearman" else st.pearsonr(a[ix],b[ix]).statistic)
    return tuple(np.quantile(vals,[.025,.975]))


def _fit_ols(df, outcome, predictor, controls=False, fixed_effects=False, model_id=""):
    cols=[outcome,predictor]+(["log_degree"] if controls else [])+(["ego_id"] if fixed_effects else [])
    d=df[cols].dropna().copy()
    if fixed_effects: d["ego_fe"]=d["ego_id"].astype("category")
    formula=f"{outcome} ~ {predictor}" + (" + log_degree" if controls else "") + (" + ego_fe" if fixed_effects else "")
    fit=smf.ols(formula,d).fit(cov_type="HC3")
    rows=[]
    for term in [predictor]+(["log_degree"] if controls else []):
        rows.append({"model":model_id,"outcome":outcome,"term":term,"coefficient":fit.params.get(term,np.nan),
                     "std_error":fit.bse.get(term,np.nan),"p_value":fit.pvalues.get(term,np.nan),
                     "ci_low":fit.conf_int().loc[term,0] if term in fit.params else np.nan,
                     "ci_high":fit.conf_int().loc[term,1] if term in fit.params else np.nan,"n":int(fit.nobs),
                     "r_squared":fit.rsquared,"adjusted_r_squared":fit.rsquared_adj,"hc_type":"HC3","ego_fixed_effects":fixed_effects})
    return fit,rows,d


def step12_statistics():
    """Estimate correlations, robust regressions, diagnostics, and heterogeneity."""
    df=pd.read_parquet(C.ANALYTIC/"node_level_analysis.parquet").query("eligible_main_regression").copy()
    pairs=[("similarity_jaccard_mean","clustering"),("similarity_jaccard_mean","ego_density"),("diversity_complement","betweenness"),
           ("diversity_complement","participation_coefficient"),("diversity_complement","communities_reached"),("degree","betweenness"),
           ("degree","clustering"),("similarity_jaccard_mean","degree"),("diversity_complement","degree")]
    correlations=[]
    for x,y in pairs:
        z=df[[x,y]].dropna()
        for method in ["pearson","spearman"]:
            res=st.pearsonr(z[x],z[y]) if method=="pearson" else st.spearmanr(z[x],z[y])
            lo,hi=_bootstrap_corr(z[x],z[y],method)
            correlations.append({"x":x,"y":y,"method":method,"coefficient":res.statistic,"p_value":res.pvalue,"n":len(z),"ci_low":lo,"ci_high":hi})
    pd.DataFrame(correlations).to_csv(C.OUTPUT_DIRS["results"]/"correlations.csv",index=False)
    specs=[("M1","clustering","similarity_jaccard_mean",False,False),("M2","clustering","similarity_jaccard_mean",True,True),
           ("M3","log_betweenness","diversity_complement",False,False),("M4","log_betweenness","diversity_complement",True,True),
           ("M5","participation_coefficient","diversity_complement",True,True)]
    reg=[]; diagnostics=[]; fits=[]; standardized=[]
    for mid,y,x,ctrl,fe in specs:
        fit,rows,d=_fit_ols(df,y,x,ctrl,fe,mid); reg.extend(rows)
        X=fit.model.exog; names=fit.model.exog_names
        vif=max([variance_inflation_factor(X,i) for i,n in enumerate(names) if n in [x,"log_degree"]],default=np.nan)
        bp=sm.stats.diagnostic.het_breuschpagan(fit.resid,fit.model.exog)
        infl=fit.get_influence(); cooks=infl.cooks_distance[0]
        diagnostics.append({"model":mid,"breusch_pagan_stat":bp[0],"breusch_pagan_p":bp[1],"max_vif_focal_controls":vif,
                            "max_cooks_distance":np.max(cooks),"influential_cook_gt_4n":int(np.sum(cooks>4/len(d))),
                            "max_leverage":float(np.max(infl.hat_matrix_diag)),"residual_skew":st.skew(fit.resid)})
        fits.append({"model":mid,"outcome":y,"n":int(fit.nobs),"r_squared":fit.rsquared,"adjusted_r_squared":fit.rsquared_adj,"aic":fit.aic,"bic":fit.bic})
        focal=next(r for r in rows if r["term"]==x)
        standardized.append({"model":mid,"term":x,"standardized_coefficient":focal["coefficient"]*d[x].std()/d[y].std(),"n":len(d)})
    # Count outcome: Poisson with HC3 and ego fixed effects.
    d=df[["communities_reached","diversity_complement","log_degree","ego_id"]].dropna()
    d["ego_fe"]=d["ego_id"].astype("category")
    pfit=smf.glm("communities_reached ~ diversity_complement + log_degree + ego_fe",d,family=sm.families.Poisson()).fit(cov_type="HC3")
    for term in ["diversity_complement","log_degree"]:
        reg.append({"model":"M6","outcome":"communities_reached","term":term,"coefficient":pfit.params[term],"std_error":pfit.bse[term],
                    "p_value":pfit.pvalues[term],"ci_low":pfit.conf_int().loc[term,0],"ci_high":pfit.conf_int().loc[term,1],"n":int(pfit.nobs),
                    "r_squared":np.nan,"adjusted_r_squared":np.nan,"hc_type":"HC3","ego_fixed_effects":True})
    fits.append({"model":"M6","outcome":"communities_reached","n":int(pfit.nobs),"r_squared":np.nan,"adjusted_r_squared":np.nan,"aic":pfit.aic,"bic":np.nan})
    pd.DataFrame(reg).to_csv(C.OUTPUT_DIRS["results"]/"regression_main.csv",index=False)
    pd.DataFrame(diagnostics).to_csv(C.OUTPUT_DIRS["results"]/"regression_diagnostics.csv",index=False)
    pd.DataFrame(fits).to_csv(C.OUTPUT_DIRS["results"]/"model_fit_summary.csv",index=False)
    pd.DataFrame(standardized).to_csv(C.OUTPUT_DIRS["results"]/"standardized_effects.csv",index=False)
    by=[]
    for ego,z in df.groupby("ego_id"):
        for x,y,label in [("similarity_jaccard_mean","clustering","similarity_clustering"),("diversity_complement","log_betweenness","diversity_betweenness"),("diversity_complement","participation_coefficient","diversity_participation")]:
            if len(z)>=10 and z[x].nunique()>1 and z[y].nunique()>1:
                fit=smf.ols(f"{y} ~ {x} + log_degree",z).fit(cov_type="HC3")
                by.append({"ego_id":ego,"relationship":label,"coefficient":fit.params[x],"std_error":fit.bse[x],"p_value":fit.pvalues[x],"ci_low":fit.conf_int().loc[x,0],"ci_high":fit.conf_int().loc[x,1],"n":len(z),"r_squared":fit.rsquared})
    pd.DataFrame(by).to_csv(C.OUTPUT_DIRS["results"]/"results_by_ego.csv",index=False)


def _partial_slope(y,x,degree,egos):
    mask=np.isfinite(y)&np.isfinite(x)&np.isfinite(degree)
    y=np.asarray(y)[mask]; x=np.asarray(x)[mask]; degree=np.asarray(degree)[mask]; egos=np.asarray(egos)[mask]
    dummies=pd.get_dummies(pd.Series(egos),drop_first=True,dtype=float).to_numpy()
    Z=np.column_stack([np.ones(len(y)),np.log1p(degree),dummies])
    xr=x-Z@np.linalg.lstsq(Z,x,rcond=None)[0]; yr=y-Z@np.linalg.lstsq(Z,y,rcond=None)[0]
    return float(xr@yr/(xr@xr)) if xr@xr else np.nan


def step13_permutations():
    """Run within-ego attribute permutations and configuration-model nulls."""
    df=pd.read_parquet(C.ANALYTIC/"node_level_analysis.parquet").query("eligible_main_regression").copy()
    fwide=pd.read_parquet(C.NODE_FEATURES/"node_features_wide.parquet")
    R=C.N_PERMUTATIONS_FAST if C.USE_FAST_PERMUTATIONS else C.N_PERMUTATIONS_MAIN
    prepared=[]
    for ego,z in df.groupby("ego_id",sort=True):
        z=z.sort_values("node_id").reset_index(drop=True)
        fw=fwide.query("ego_id==@ego and has_features").sort_values("node_id").reset_index(drop=True)
        all_nodes=fw.node_id.astype(int).tolist(); arr=np.asarray(fw.feature_vector.tolist(),dtype=np.uint8); idx={n:i for i,n in enumerate(all_nodes)}
        g=load_graph(int(ego)); edges=np.array([(idx[u],idx[v]) for u,v in g.edges() if u in idx and v in idx],dtype=int)
        targets=np.array([idx[int(n)] for n in z.node_id],dtype=int)
        prepared.append((int(ego),z,arr,edges,targets))
    obs={"similarity_clustering_spearman":st.spearmanr(df.similarity_jaccard_mean,df.clustering).statistic,
         "diversity_betweenness_spearman":st.spearmanr(df.diversity_complement,df.betweenness).statistic,
         "diversity_participation_spearman":st.spearmanr(df.diversity_complement,df.participation_coefficient).statistic,
         "similarity_clustering_regression":_partial_slope(df.clustering,df.similarity_jaccard_mean,df.degree,df.ego_id),
         "diversity_betweenness_regression":_partial_slope(df.log_betweenness,df.diversity_complement,df.degree,df.ego_id),
         "diversity_participation_regression":_partial_slope(df.participation_coefficient,df.diversity_complement,df.degree,df.ego_id)}
    dist=[]
    for r in range(R):
        rng_iter=np.random.default_rng(C.RANDOM_SEED+r)
        sims=[]; base=[]
        for ego,z,arr,edges,targets in prepared:
            perm=arr[rng_iter.permutation(len(arr))]
            a,b=perm[edges[:,0]],perm[edges[:,1]]; inter=np.logical_and(a,b).sum(1); union=np.logical_or(a,b).sum(1)
            ev=np.divide(inter,union,out=np.zeros_like(inter,dtype=float),where=union>0)
            sums=np.bincount(edges.ravel(),weights=np.repeat(ev,2),minlength=len(arr))
            counts=np.bincount(edges.ravel(),minlength=len(arr)); node=np.divide(sums,counts,out=np.full(len(arr),np.nan),where=counts>0)
            sims.append(node[targets]); base.append(z)
        z=pd.concat(base,ignore_index=True); sim=np.concatenate(sims); div=1-sim
        vals={"iteration":r+1,"seed":C.RANDOM_SEED+r,
              "similarity_clustering_spearman":st.spearmanr(sim,z.clustering,nan_policy="omit").statistic,
              "diversity_betweenness_spearman":st.spearmanr(div,z.betweenness,nan_policy="omit").statistic,
              "diversity_participation_spearman":st.spearmanr(div,z.participation_coefficient,nan_policy="omit").statistic,
              "similarity_clustering_regression":_partial_slope(z.clustering,sim,z.degree,z.ego_id),
              "diversity_betweenness_regression":_partial_slope(z.log_betweenness,div,z.degree,z.ego_id),
              "diversity_participation_regression":_partial_slope(z.participation_coefficient,div,z.degree,z.ego_id)}
        dist.append(vals)
        if (r+1)%100==0: print(f"  permutation {r+1}/{R}",flush=True)
    ddf=pd.DataFrame(dist); ddf.to_parquet(C.OUTPUT_DIRS["null"]/"permutation_distributions.parquet",index=False)
    stats=[]; pvals=[]
    for name,value in obs.items():
        null=ddf[name].dropna().to_numpy(); p=(1+np.sum(np.abs(null)>=abs(value)))/(len(null)+1)
        stats.append({"statistic":name,"observed":value,"null_mean":null.mean(),"null_sd":null.std(ddof=1),"null_q025":np.quantile(null,.025),"null_q975":np.quantile(null,.975),"permutations":len(null)})
        pvals.append({"statistic":name,"observed":value,"empirical_p_value_two_sided":p,"percentile":st.percentileofscore(null,value),"permutations":len(null)})
    pd.DataFrame(stats).to_csv(C.OUTPUT_DIRS["null"]/"permutation_statistics.csv",index=False); pd.DataFrame(pvals).to_csv(C.OUTPUT_DIRS["null"]/"empirical_pvalues.csv",index=False)
    nullrows=[]
    for ego in df.ego_id.unique():
        g=load_graph(int(ego)); observed={"clustering":nx.average_clustering(g),"modularity":float(pd.read_csv(C.OUTPUT_DIRS["communities"]/"community_summary_by_ego.csv").query("ego_id==@ego").modularity.iloc[0])}
        for rep in range(C.CONFIGURATION_MODEL_REPLICATIONS):
            seed=C.RANDOM_SEED+rep; seq=[d for _,d in g.degree()]
            mg=nx.configuration_model(seq,seed=seed); ng=nx.Graph(mg); ng.remove_edges_from(nx.selfloop_edges(ng))
            if ng.number_of_edges()==0: continue
            c=list(nx.community.louvain_communities(ng,seed=seed)); sample=min(100,len(ng))
            bt=nx.betweenness_centrality(ng,k=sample,seed=seed)
            nullrows.append({"ego_id":ego,"replication":rep+1,"seed":seed,"null_clustering":nx.average_clustering(ng),
                             "null_modularity":nx.community.modularity(ng,c),"null_mean_betweenness":np.mean(list(bt.values())),
                             "observed_clustering":observed["clustering"],"observed_modularity":observed["modularity"]})
    ndf=pd.DataFrame(nullrows); ndf.to_csv(C.OUTPUT_DIRS["null"]/"configuration_model_summary.csv",index=False)
    ndf.groupby("ego_id").agg(observed_clustering=("observed_clustering","first"),null_clustering_mean=("null_clustering","mean"),
                               observed_modularity=("observed_modularity","first"),null_modularity_mean=("null_modularity","mean"),
                               null_mean_betweenness=("null_mean_betweenness","mean")).reset_index().to_csv(C.OUTPUT_DIRS["null"]/"observed_vs_null.csv",index=False)


def _simple_spec(df,label,outcome,predictor,mask=None):
    z=df.copy() if mask is None else df[mask].copy(); z=z[[outcome,predictor,"log_degree","ego_id"]].dropna()
    if len(z)<20 or z[predictor].nunique()<2:return {"specification":label,"outcome":outcome,"predictor":predictor,"coefficient":np.nan,"std_error":np.nan,"p_value":np.nan,"n":len(z)}
    z["ego_fe"]=z["ego_id"].astype("category")
    fit=smf.ols(f"{outcome} ~ {predictor} + log_degree + ego_fe",z).fit(cov_type="HC3")
    return {"specification":label,"outcome":outcome,"predictor":predictor,"coefficient":fit.params[predictor],"std_error":fit.bse[predictor],"p_value":fit.pvalues[predictor],"ci_low":fit.conf_int().loc[predictor,0],"ci_high":fit.conf_int().loc[predictor,1],"n":len(z)}


def step14_robustness():
    """Evaluate alternative measures, samples, communities, and bootstrap inference."""
    df=pd.read_parquet(C.ANALYTIC/"node_level_analysis.parquet").query("eligible_main_regression").copy(); results=[]
    sims=[]
    for pred in ["similarity_jaccard_mean","similarity_cosine_mean"]+[c for c in df if c.startswith("similarity_") and c.endswith("_mean") and c not in ["similarity_jaccard_mean","similarity_cosine_mean"]]:
        if pred in df and df[pred].notna().sum()>=20:sims.append(_simple_spec(df,f"Similarity: {pred}","clustering",pred))
    pd.DataFrame(sims).to_csv(C.OUTPUT_DIRS["robustness"]/"alternative_similarity.csv",index=False); results+=sims
    divs=[]
    for pred in ["diversity_complement","diversity_category_entropy","circle_entropy","outside_dominant_circle_share"]:
        for out in ["log_betweenness","participation_coefficient"]:
            if pred in df and df[pred].notna().sum()>=20:divs.append(_simple_spec(df,f"Diversity: {pred} -> {out}",out,pred))
    pd.DataFrame(divs).to_csv(C.OUTPUT_DIRS["robustness"]/"alternative_diversity.csv",index=False); results+=divs
    restrictions=[]
    qdeg=df.degree.quantile(.99); qbt=df.betweenness.quantile(.99); mednodes=df.groupby("ego_id").size().median(); goodmods=df.groupby("ego_id").modularity.first(); good=set(goodmods[goodmods>=goodmods.median()].index)
    masks={"all":np.ones(len(df),bool),"degree_gt_1":df.degree>1,"exclude_top1_degree":df.degree<=qdeg,
           "exclude_top1_betweenness":df.betweenness<=qbt,"lcc_only":df.in_lcc,"complete_feature_coverage":df.has_features,
           "large_ego_networks":df.ego_id.isin(df.groupby("ego_id").size().loc[lambda x:x>=mednodes].index),"high_modularity_egos":df.ego_id.isin(good)}
    for name,mask in masks.items():
        restrictions.extend([_simple_spec(df,f"{name}: similarity-clustering","clustering","similarity_jaccard_mean",mask),
                             _simple_spec(df,f"{name}: diversity-betweenness","log_betweenness","diversity_complement",mask),
                             _simple_spec(df,f"{name}: diversity-participation","participation_coefficient","diversity_complement",mask)])
    pd.DataFrame(restrictions).to_csv(C.OUTPUT_DIRS["robustness"]/"sample_restrictions.csv",index=False); results+=restrictions
    community=[]
    for ego in df.ego_id.unique():
        g=load_graph(int(ego))
        greedy=list(nx.community.greedy_modularity_communities(g)); community.append({"ego_id":ego,"method":"greedy","resolution":np.nan,"n_communities":len(greedy),"modularity":nx.community.modularity(g,greedy)})
        for res in [.5,1,1.5,2]:
            cs=list(nx.community.louvain_communities(g,seed=C.RANDOM_SEED,resolution=res)); community.append({"ego_id":ego,"method":"louvain","resolution":res,"n_communities":len(cs),"modularity":nx.community.modularity(g,cs,resolution=res)})
    pd.DataFrame(community).to_csv(C.OUTPUT_DIRS["robustness"]/"alternative_community_methods.csv",index=False)
    rng=np.random.default_rng(C.RANDOM_SEED); boot=[]; egos=df.ego_id.unique()
    for r in range(C.BOOTSTRAP_REPLICATIONS):
        sampled=rng.choice(egos,len(egos),replace=True); chunks=[]
        for j,e in enumerate(sampled):
            z=df.query("ego_id==@e").copy(); z["boot_ego"]=j; chunks.append(z)
        z=pd.concat(chunks,ignore_index=True)
        for out,pred,label in [("clustering","similarity_jaccard_mean","similarity_clustering"),("log_betweenness","diversity_complement","diversity_betweenness"),("participation_coefficient","diversity_complement","diversity_participation")]:
            boot.append({"replication":r+1,"relationship":label,"coefficient":_partial_slope(z[out],z[pred],z.degree,z.boot_ego)})
    bdf=pd.DataFrame(boot); bsum=bdf.groupby("relationship").coefficient.agg(mean="mean",std_error="std",ci_low=lambda x:np.quantile(x,.025),ci_high=lambda x:np.quantile(x,.975),replications="count").reset_index()
    bsum.to_csv(C.OUTPUT_DIRS["robustness"]/"bootstrap_results.csv",index=False)
    pd.DataFrame(results).to_csv(C.OUTPUT_DIRS["robustness"]/"robustness_summary.csv",index=False)


COLORS={"blue":"#176B87","teal":"#2A9D8F","gold":"#E9C46A","orange":"#F4A261","red":"#E76F51","navy":"#264653","gray":"#6B7280"}


def _plot_style():
    sns.set_theme(style="whitegrid",context="paper",font_scale=1.15)
    plt.rcParams.update({"figure.dpi":140,"savefig.dpi":300,"font.family":"DejaVu Sans","axes.spines.top":False,
                         "axes.spines.right":False,"axes.edgecolor":"#374151","grid.color":"#E5E7EB","grid.linewidth":.6,
                         "legend.frameon":False,"pdf.fonttype":42,"ps.fonttype":42})


def _savefig(fig,name):
    for ext in ["png","pdf"]: fig.savefig(C.OUTPUT_DIRS["figures"]/f"{name}.{ext}",bbox_inches="tight",facecolor="white")
    plt.close(fig)


def _binscatter(ax,df,x,y,color=COLORS["blue"],bins=25,size=None):
    z=df[[x,y]+([size] if size else [])].dropna().copy()
    ax.scatter(z[x],z[y],s=np.clip(z[size]*1.2,7,70) if size else 14,alpha=.12,color=color,edgecolors="none",rasterized=True)
    if len(z)>3:
        z["bin"]=pd.qcut(z[x].rank(method="first"),min(bins,len(z)),duplicates="drop")
        b=z.groupby("bin",observed=True)[[x,y]].mean(); ax.plot(b[x],b[y],color=color,lw=2.2); ax.scatter(b[x],b[y],color="white",edgecolor=color,s=25,zorder=3)
    ax.set_xlabel(x.replace("_"," ").title()); ax.set_ylabel(y.replace("_"," ").title())


def step15_figures():
    """Render title-free publication figures in PNG and vector PDF formats."""
    _plot_style(); df=pd.read_parquet(C.ANALYTIC/"node_level_analysis.parquet"); main=df.query("eligible_main_regression").copy()
    net=pd.read_csv(C.OUTPUT_DIRS["network"]/"network_summary_by_ego.csv"); cs=pd.read_csv(C.OUTPUT_DIRS["communities"]/"community_summary_by_ego.csv")
    overview=net.merge(cs,on="ego_id")
    fig,axes=plt.subplots(1,5,figsize=(13.5,2.9)); cols=[("nodes","Nodes"),("edges","Edges"),("density","Density"),("mean_clustering","Mean clustering"),("modularity","Modularity")]
    for ax,(col,label) in zip(axes,cols):
        sns.stripplot(data=overview,y=col,ax=ax,color=COLORS["blue"],size=6,jitter=.12); ax.set_xlabel("");ax.set_ylabel(label);ax.set_xticks([])
    fig.subplots_adjust(wspace=.5); _savefig(fig,"fig_01_network_overview")
    fig,ax=plt.subplots(figsize=(6.2,4.2));_binscatter(ax,main,"similarity_jaccard_mean","clustering",COLORS["blue"],size="degree");_savefig(fig,"fig_02_similarity_clustering")
    fig,ax=plt.subplots(figsize=(6.2,4.2));_binscatter(ax,main,"diversity_complement","log_betweenness",COLORS["red"],size="degree"); ax.set_ylabel("Log(1 + normalized betweenness)");_savefig(fig,"fig_03_diversity_betweenness")
    fig,ax=plt.subplots(figsize=(6.2,4.2));_binscatter(ax,main,"diversity_complement","participation_coefficient",COLORS["teal"],size="degree");_savefig(fig,"fig_04_diversity_participation")
    rank=main.copy(); rank["degree_percentile"]=rank.groupby("ego_id").degree.rank(pct=True); rank["betweenness_percentile"]=rank.groupby("ego_id").betweenness.rank(pct=True); rank["participation_percentile"]=rank.groupby("ego_id").participation_coefficient.rank(pct=True)
    highlight=(rank.betweenness_percentile>=.9)&(rank.degree_percentile.between(.25,.75))
    fig,ax=plt.subplots(figsize=(6.2,4.6)); ax.scatter(rank.degree_percentile,rank.betweenness_percentile,s=12,alpha=.18,color=COLORS["gray"],label="Node records");ax.scatter(rank.loc[highlight,"degree_percentile"],rank.loc[highlight,"betweenness_percentile"],s=22,color=COLORS["red"],label="Moderate degree, high betweenness");ax.plot([0,1],[0,1],ls="--",lw=1,color="#9CA3AF");ax.set(xlabel="Within-network degree percentile",ylabel="Within-network betweenness percentile");ax.legend(loc="lower right");_savefig(fig,"fig_05_degree_vs_brokerage")
    # Four automatically selected local neighborhoods.
    candidates=main.copy(); candidates["sim_clust"]=candidates.similarity_jaccard_mean.rank(pct=True)+candidates.clustering.rank(pct=True); candidates["div_btw"]=candidates.diversity_complement.rank(pct=True)+candidates.betweenness.rank(pct=True); candidates["degree_lowpart"]=candidates.degree.rank(pct=True)-candidates.participation_coefficient.rank(pct=True); candidates["moderate_broker"]=candidates.betweenness.rank(pct=True)-abs(candidates.degree.rank(pct=True)-.5)
    picks=[candidates.nlargest(1,"sim_clust").iloc[0],candidates.nlargest(1,"div_btw").iloc[0],candidates.nlargest(1,"degree_lowpart").iloc[0],candidates.nlargest(1,"moderate_broker").iloc[0]]
    fig,axes=plt.subplots(2,2,figsize=(10,9)); comm=pd.read_parquet(C.COMMUNITIES/"community_assignments.parquet")
    for k,(ax,row) in enumerate(zip(axes.ravel(),picks)):
        g=load_graph(int(row.ego_id)); nodes={int(row.node_id)}|set(g.neighbors(int(row.node_id))); sg=g.subgraph(nodes).copy(); cmap=comm.query("ego_id==@row.ego_id").set_index("node_id").community_id.to_dict();pos=nx.spring_layout(sg,seed=C.RANDOM_SEED,k=1/math.sqrt(max(2,len(sg)))); colors=[plt.cm.tab20(cmap.get(n,0)%20) for n in sg]; sizes=[150 if n==row.node_id else 16+2*math.sqrt(g.degree(n)) for n in sg]
        nx.draw_networkx_edges(sg,pos,ax=ax,width=.45,alpha=.25,edge_color="#6B7280");nx.draw_networkx_nodes(sg,pos,ax=ax,node_color=colors,node_size=sizes,edgecolors=[COLORS["navy"] if n==row.node_id else "white" for n in sg],linewidths=[1.8 if n==row.node_id else .25 for n in sg]);ax.text(.01,.98,f"({chr(97+k)})  ego {int(row.ego_id)}, node {int(row.node_id)}",transform=ax.transAxes,va="top",fontsize=9);ax.set_axis_off()
    fig.subplots_adjust(wspace=.02,hspace=.05);_savefig(fig,"fig_06_node_archetypes")
    rep=int(overview.iloc[(overview.nodes-overview.nodes.median()).abs().argmin()].ego_id); g=load_graph(rep); cmap=comm.query("ego_id==@rep").set_index("node_id").community_id.to_dict(); bmap=main.query("ego_id==@rep").set_index("node_id").betweenness.to_dict(); pos=nx.spring_layout(g,seed=C.RANDOM_SEED,iterations=100)
    fig,ax=plt.subplots(figsize=(8,7));nx.draw_networkx_edges(g,pos,ax=ax,width=.25,alpha=.12,edge_color="#64748B");nx.draw_networkx_nodes(g,pos,ax=ax,node_size=[8+700*bmap.get(n,0) for n in g],node_color=[cmap.get(n,0) for n in g],cmap=plt.cm.tab20,linewidths=0,alpha=.9);ax.set_axis_off();ax.text(.01,.99,f"ego-network {rep}",transform=ax.transAxes,va="top",color="#374151");_savefig(fig,"fig_07_community_structure")
    dist=pd.read_parquet(C.OUTPUT_DIRS["null"]/"permutation_distributions.parquet"); statsdf=pd.read_csv(C.OUTPUT_DIRS["null"]/"permutation_statistics.csv").set_index("statistic")
    for suffix,var,xlab,color in [("08a_null_similarity_clustering","similarity_clustering_spearman","Spearman coefficient",COLORS["blue"]),("08b_null_diversity_betweenness","diversity_betweenness_spearman","Spearman coefficient",COLORS["red"]),("08c_null_diversity_participation","diversity_participation_spearman","Spearman coefficient",COLORS["teal"])]:
        fig,ax=plt.subplots(figsize=(6.2,4));sns.histplot(dist[var],bins=35,ax=ax,color=color,alpha=.65,edgecolor="white");ax.axvline(statsdf.loc[var,"observed"],color="#111827",lw=2,label="Observed");ax.set_xlabel(xlab);ax.set_ylabel("Permutation count");ax.legend();_savefig(fig,f"fig_{suffix}")
    by=pd.read_csv(C.OUTPUT_DIRS["results"]/"results_by_ego.csv"); rels=list(by.relationship.unique()); fig,axes=plt.subplots(1,len(rels),figsize=(12,4.6),sharey=False)
    for ax,rel,color in zip(np.atleast_1d(axes),rels,[COLORS["blue"],COLORS["red"],COLORS["teal"]]):
        z=by.query("relationship==@rel").sort_values("coefficient"); y=np.arange(len(z));ax.errorbar(z.coefficient,y,xerr=[z.coefficient-z.ci_low,z.ci_high-z.coefficient],fmt="o",color=color,ecolor=color,capsize=2);ax.axvline(0,color="#111827",lw=.8);ax.set_yticks(y,z.ego_id.astype(str));ax.set_xlabel(rel.replace("_"," "))
    fig.subplots_adjust(wspace=.5);_savefig(fig,"fig_09_heterogeneity_by_ego")
    rob=pd.read_csv(C.OUTPUT_DIRS["robustness"]/"sample_restrictions.csv").dropna(subset=["coefficient"])
    relationships=[("similarity-clustering",COLORS["blue"]),("diversity-betweenness",COLORS["red"]),("diversity-participation",COLORS["teal"])]
    fig,axes=plt.subplots(1,3,figsize=(12.5,5.3),sharey=True)
    for ax,(rel,color) in zip(axes,relationships):
        z=rob[rob.specification.str.endswith(rel)].copy();z["restriction"]=z.specification.str.split(":").str[0];z=z.reset_index(drop=True);y=np.arange(len(z))
        ax.errorbar(z.coefficient,y,xerr=[z.coefficient-z.ci_low,z.ci_high-z.coefficient],fmt="o",color=color,ecolor=color,capsize=2,ms=5)
        ax.axvline(0,color="#111827",lw=.8);ax.set_yticks(y,z.restriction.str.replace("_"," "));ax.set_xlabel(rel.replace("-"," -- "));ax.invert_yaxis()
    fig.subplots_adjust(wspace=.35);_savefig(fig,"fig_10_robustness_specification_curve")


def _flatten_columns(df):
    d=df.copy()
    if isinstance(d.columns,pd.MultiIndex): d.columns=["_".join(str(x) for x in col if str(x)!="").strip("_") for col in d.columns]
    return d


def _export_table(df,name,index=False):
    d=_flatten_columns(df)
    d.to_csv(C.OUTPUT_DIRS["tables"]/f"{name}.csv",index=index)
    (C.OUTPUT_DIRS["tables"]/f"{name}.md").write_text(d.to_markdown(index=index),encoding="utf-8")
    (C.OUTPUT_DIRS["tables"]/f"{name}.tex").write_text(d.to_latex(index=index,float_format=lambda x:f"{x:.4f}",escape=True),encoding="utf-8")


def step16_tables():
    """Export report tables consistently as CSV, Markdown, and LaTeX."""
    _export_table(pd.read_csv(C.OUTPUT_DIRS["sample"]/"sample_flow.csv"),"tab_01_sample_flow")
    net=pd.read_csv(C.OUTPUT_DIRS["network"]/"network_summary_by_ego.csv"); com=pd.read_csv(C.OUTPUT_DIRS["communities"]/"community_summary_by_ego.csv")
    _export_table(net.merge(com,on="ego_id")[["ego_id","nodes","edges","density","mean_degree","mean_clustering","n_communities","modularity"]],"tab_02_network_descriptives")
    df=pd.read_parquet(C.ANALYTIC/"node_level_analysis.parquet"); cols=["degree","similarity_jaccard_mean","diversity_complement","clustering","betweenness","participation_coefficient","communities_reached","constraint","effective_size"]
    desc=df[cols].describe(percentiles=[.25,.5,.75]).T.reset_index(names="variable");_export_table(desc,"tab_03_node_descriptives")
    _export_table(pd.read_csv(C.OUTPUT_DIRS["results"]/"correlations.csv"),"tab_04_correlations")
    _export_table(pd.read_csv(C.OUTPUT_DIRS["results"]/"regression_main.csv"),"tab_05_main_regressions")
    _export_table(pd.read_csv(C.OUTPUT_DIRS["null"]/"empirical_pvalues.csv").merge(pd.read_csv(C.OUTPUT_DIRS["null"]/"permutation_statistics.csv"),on=["statistic","observed","permutations"]),"tab_06_permutation_tests")
    _export_table(pd.read_csv(C.OUTPUT_DIRS["results"]/"results_by_ego.csv"),"tab_07_results_by_ego")
    _export_table(pd.read_csv(C.OUTPUT_DIRS["robustness"]/"robustness_summary.csv"),"tab_08_robustness")
    top=pd.concat([df.nlargest(10,"degree").assign(ranking="degree"),df.nlargest(10,"betweenness").assign(ranking="betweenness"),df.nlargest(10,"participation_coefficient").assign(ranking="participation"),df.nlargest(10,"effective_size").assign(ranking="effective_size")])
    _export_table(top[["ranking","ego_id","node_id","degree","betweenness","participation_coefficient","effective_size"]],"tab_09_top_nodes")


def step17_report_inputs():
    """Generate verified narrative facts and non-causal interpretation flags."""
    sample=json.loads((C.OUTPUT_DIRS["sample"]/"final_sample_summary.json").read_text()); net=pd.read_csv(C.OUTPUT_DIRS["network"]/"network_summary_by_ego.csv"); feat=pd.read_csv(C.OUTPUT_DIRS["sample"]/"feature_coverage_by_ego.csv"); com=pd.read_csv(C.OUTPUT_DIRS["communities"]/"community_summary_by_ego.csv")
    facts=(f"# Data-section facts\n\n- Ego-networks in raw archive: {sample['raw_ego_networks']}.\n- Node--ego records: {sample['raw_node_records']:,}; distinct anonymized node IDs: {sample['raw_unique_nodes']:,}.\n- Unique alter--alter ties in raw ego files: {sample['raw_ego_edge_records']:,}; ties after adding ego--alter links: {sample['constructed_ego_edge_records']:,}.\n- Final regression records: {sample['sample_E_nodes']:,}.\n- Mean feature coverage: {feat.feature_coverage.mean():.1%}.\n- Mean LCC share: {net.largest_component_share.mean():.1%}.\n- Community method: Louvain; mean selected modularity: {com.modularity.mean():.3f}.\n")
    (C.OUTPUT_DIRS["report"]/"data_section_facts.md").write_text(facts,encoding="utf-8");(C.OUTPUT_DIRS["report"]/"data_section_facts.tex").write_text(facts.replace("# Data-section facts\n\n","").replace("- ","\\noindent ").replace("%",r"\%"),encoding="utf-8")
    method=("# Methodology facts\n\nSimilarity is mean edge-level Jaccard overlap of binary attributes, calculated only within ego-network. Diversity is its complement. Cohesion is local clustering; brokerage is normalized betweenness and the participation coefficient from selected Louvain partitions. Pooled OLS specifications use HC3 errors, log degree, and ego-network fixed effects. Attribute vectors are permuted within ego-network while graph structure remains fixed.\n")
    (C.OUTPUT_DIRS["report"]/"methodology_facts.md").write_text(method,encoding="utf-8")
    corr=pd.read_csv(C.OUTPUT_DIRS["results"]/"correlations.csv"); reg=pd.read_csv(C.OUTPUT_DIRS["results"]/"regression_main.csv"); emp=pd.read_csv(C.OUTPUT_DIRS["null"]/"empirical_pvalues.csv")
    def cr(x,y): return corr.query("x==@x and y==@y and method=='spearman'").iloc[0]
    a=cr("similarity_jaccard_mean","clustering");b=cr("diversity_complement","betweenness");d=cr("diversity_complement","participation_coefficient")
    m2=reg.query("model=='M2' and term=='similarity_jaccard_mean'").iloc[0];m4=reg.query("model=='M4' and term=='diversity_complement'").iloc[0];m5=reg.query("model=='M5' and term=='diversity_complement'").iloc[0]
    key=(f"# Key numerical results\n\n- Similarity--clustering Spearman rho: {a.coefficient:.3f} (p={a.p_value:.3g}, N={int(a.n):,}).\n- Diversity--betweenness Spearman rho: {b.coefficient:.3f} (p={b.p_value:.3g}, N={int(b.n):,}).\n- Diversity--participation Spearman rho: {d.coefficient:.3f} (p={d.p_value:.3g}, N={int(d.n):,}).\n- Degree-adjusted similarity coefficient in M2: {m2.coefficient:.3f} (HC3 p={m2.p_value:.3g}).\n- Degree-adjusted diversity coefficient in M4: {m4.coefficient:.3g} (HC3 p={m4.p_value:.3g}).\n- Degree-adjusted diversity coefficient in M5: {m5.coefficient:.3f} (HC3 p={m5.p_value:.3g}).\n- Permutation p-values are stored in `empirical_pvalues.csv`; {len(emp)} planned statistics were evaluated with {int(emp.permutations.min())} permutations.\n")
    (C.OUTPUT_DIRS["report"]/"results_key_numbers.md").write_text(key,encoding="utf-8");(C.OUTPUT_DIRS["report"]/"results_key_numbers.tex").write_text(key.replace("# Key numerical results\n\n","").replace("- ","\\noindent ").replace("%",r"\%"),encoding="utf-8")
    flags={"similarity_clustering_positive":bool(m2.coefficient>0),"similarity_clustering_significant":bool(m2.p_value<C.ALPHA),
           "diversity_betweenness_positive":bool(m4.coefficient>0),"diversity_betweenness_significant":bool(m4.p_value<C.ALPHA),
           "diversity_participation_positive":bool(m5.coefficient>0),"diversity_participation_significant":bool(m5.p_value<C.ALPHA),
           "results_robust_to_degree":bool(m2.p_value<C.ALPHA and m4.p_value<C.ALPHA and m5.p_value<C.ALPHA),
           "heterogeneity_high":bool(pd.read_csv(C.OUTPUT_DIRS["results"]/"results_by_ego.csv").groupby("relationship").coefficient.apply(lambda x:(x>0).mean()).between(.25,.75).any())}
    save_json(flags,C.OUTPUT_DIRS["report"]/"result_interpretation_flags.json")
