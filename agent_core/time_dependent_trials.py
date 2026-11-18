"""Fixed-count, checkpointed shared trials following a reviewed observed task."""
from __future__ import annotations

from dataclasses import asdict
import fcntl
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

from agent_core.file_cache import sha256_file
from agent_core.schemas import NormalizedAnalysis, NormalizedSource
from agent_core.simple_yaml import load_simple_yaml


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def code_identity(root):
    import importlib.metadata
    root = Path(root)
    paths = [root/"run_agent_wrap.py", *sorted((root/"analysis_backend").rglob("*.py")),
             *sorted((root/"agent_core").glob("*.py"))]
    return dict(files={str(path.relative_to(root)): sha256_file(path) for path in paths},
        packages={name: importlib.metadata.version(name) for name in ("numpy", "scipy", "skyllh", "numba")})


def prepare(root, directory, baseline_task, n_trials, seed, workers, batch_size, request):
    from agent_core.task_state import load_task
    from agent_core.review import review_run
    root, directory = Path(root).resolve(), Path(directory).resolve()
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (n_trials, seed, workers, batch_size)) or min(n_trials, workers, batch_size) < 1 or seed < 0:
        raise ValueError("Require positive trial/worker/batch counts and nonnegative seed")
    if seed + n_trials - 1 > 2**32-1:
        raise ValueError("Trial seed range exceeds uint32")
    baseline, baseline_path = load_task(baseline_task, root)
    if baseline.get("status") not in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
        raise ValueError("Trials require a completed reviewed observed task")
    run_dir = Path(baseline["artifacts"]["run_directory"])
    reviewed = review_run(str(run_dir), str(root), write_artifacts=False)
    if reviewed["status"] == "fail":
        raise ValueError("Baseline review failed")
    normalized = load_simple_yaml((run_dir/"config.normalized.yaml").read_text())
    if normalized.get("temporal", {}).get("scope") != "per_source_catalog_windows":
        raise ValueError("Shared seasonal trials require fixed per-source time profiles")
    observed = load_simple_yaml((run_dir/"report.yaml").read_text())["result"]
    if observed["time_dependent_engine"].get("code_identity") != code_identity(root):
        raise ValueError("Observed fit code or numerical packages differ from the current runtime; create a new baseline")
    immutable = dict(normalized=normalized, observed=observed,
        baseline_task=str(baseline_path), baseline_run=str(run_dir),
        baseline_files={str(path): sha256_file(path) for path in
            (run_dir/"report.yaml", run_dir/"config.normalized.yaml", run_dir/"provenance.yaml")},
        code=code_identity(root), n_trials=n_trials, base_seed=seed,
        method="seasonal_time_scrambling", event_count="fixed_per_phase", shared_realization=True)
    task = dict(status="READY", request=request, immutable=immutable, request_sha256=digest(immutable),
        workers=workers, batch_size=batch_size, completed=0, shards=[], baseline_review=reviewed)
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory/"task.json", task)
    return task


def read_task(directory):
    task = json.loads((Path(directory)/"task.json").read_text())
    if digest(task["immutable"]) != task["request_sha256"]:
        raise ValueError("Trial scientific request or imported observed fit changed")
    return task


def verify_baseline(task, root):
    immutable = task["immutable"]
    if immutable["code"] != code_identity(root):
        raise ValueError("Code or numerical package versions changed; cannot resume this ensemble")
    for path, expected in immutable["baseline_files"].items():
        if sha256_file(path) != expected:
            raise ValueError("Reviewed baseline changed")
    for path, expected in immutable["observed"]["time_dependent_engine"]["input_sha256"].items():
        if sha256_file(Path(root)/path) != expected:
            raise ValueError("Numerical input changed")


def load_shards(directory, task):
    import numpy as np
    chunks, next_index = [], 0
    from analysis_backend.time_dependent.seeds import trial_seed
    for shard in task["shards"]:
        path = Path(directory)/shard["file"]
        if sha256_file(path) != shard["sha256"] or shard["start"] != next_index:
            raise ValueError("Trial shard changed, overlaps, or leaves an index gap")
        with np.load(path, allow_pickle=False) as data:
            arrays = {key: data[key].copy() for key in data.files}
        count = shard["stop"] - shard["start"]
        if count < 1 or shard["stop"] > task["immutable"]["n_trials"]:
            raise ValueError("Invalid trial shard index range")
        n_sources = len(task["immutable"]["normalized"]["sources"])
        for prefix, shape in (("source", (count, n_sources)), ("stack", (count,))):
            for suffix in ("ts", "ns", "gamma", "fit_ok"):
                key = prefix + "_" + suffix
                if key not in arrays or arrays[key].shape != shape:
                    raise ValueError("Trial array shape mismatch: " + key)
            if not np.isfinite(arrays[prefix+"_ns"]).all() or (arrays[prefix+"_ns"] < 0).any() or (arrays[prefix+"_ts"] < 0).any():
                raise ValueError("Invalid trial fit statistics")
        indices = np.arange(shard["start"], shard["stop"])
        if not np.array_equal(arrays["trial_index"], indices) or not np.array_equal(arrays["seed"], [trial_seed(task["immutable"]["base_seed"], int(i)) for i in indices]):
            raise ValueError("Trial index/seed mapping mismatch")
        if not arrays["source_fit_ok"].all() or not arrays["stack_fit_ok"].all():
            raise ValueError("Failed trial fits cannot calibrate significance")
        if not np.isfinite(arrays["source_ts"]).all() or not np.isfinite(arrays["stack_ts"]).all():
            raise ValueError("Nonfinite trial statistics")
        chunks.append(arrays)
        next_index = shard["stop"]
    if next_index != task["completed"]:
        raise ValueError("Checkpoint count and shard index range disagree")
    return chunks


def run(root, directory, max_batches=None):
    import numpy as np
    from analysis_backend.time_dependent.adapter import prepare_analysis, run_background_trials
    directory = Path(directory).resolve()
    with (directory/"run.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another process is running this ensemble") from exc
        task = read_task(directory)
        from agent_core.cpu import configure_threads
        configure_threads(1)
        verify_baseline(task, root)
        load_shards(directory, task)
        target = task["immutable"]["n_trials"]
        if task["completed"] == target:
            return report(root, directory)
        if (directory/"STOP").exists():
            task["status"] = "PAUSED"
            write_json(directory/"task.json", task)
            return task
        if max_batches is not None and max_batches < 1:
            raise ValueError("max_batches must be positive")
        payload = dict(task["immutable"]["normalized"])
        payload["sources"] = [NormalizedSource(**source) for source in payload["sources"]]
        normalized = NormalizedAnalysis(**payload)
        prepared = prepare_analysis(normalized, root, workers=task["workers"], for_trials=True)
        expected = task["immutable"]["observed"]["time_dependent_engine"]
        for key in ("engine", "spectrum", "likelihood", "dataset_names", "input_sha256", "windows"):
            if prepared.metadata[key] != expected[key]:
                raise ValueError("Observed and trial construction differ: " + key)
        if expected.get("time_profile") is not None and prepared.metadata["time_profile"] != expected["time_profile"]:
            raise ValueError("Observed and trial construction differ: time_profile")
        task["status"] = "RUNNING"
        write_json(directory/"task.json", task)
        start, initial, batches = monotonic(), task["completed"], 0
        try:
            while task["completed"] < target:
                first = task["completed"]
                count = min(task["batch_size"], target-first)
                trials = run_background_trials(prepared, n_trials=count, base_seed=task["immutable"]["base_seed"],
                    trial_index_start=first, workers=task["workers"])
                if not trials.source_fit_ok.all() or not trials.stack_fit_ok.all():
                    raise ValueError("Background trial fit failed; no failed trials may be discarded")
                arrays = asdict(trials)
                name = f"trials_{first:09d}_{first+count:09d}.npz"
                path = directory/name
                # A crash may leave an unreferenced shard. Never overwrite it.
                if path.exists():
                    raise ValueError("Unreferenced shard exists; inspect recovery before resuming: " + str(path))
                temporary = directory/(name+".tmp")
                with temporary.open("wb") as stream:
                    np.savez(stream, **arrays)
                temporary.replace(path)
                task["shards"].append(dict(file=name, sha256=sha256_file(path), start=first, stop=first+count))
                task["completed"] += count
                batches += 1
                elapsed = monotonic()-start
                eta = elapsed/(task["completed"]-initial)*(target-task["completed"])
                task["execution_timing"] = dict(elapsed_seconds=elapsed, remaining_seconds=eta,
                    estimate_scope="remaining_trials_only", newly_completed=task["completed"]-initial)
                write_json(directory/"task.json", task)
                print(f"NuSrcAgent progress: shared trials {task['completed']}/{target}; remaining trials about {eta:.1f} s", file=sys.stderr, flush=True)
                if (directory/"STOP").exists() or (max_batches is not None and batches >= max_batches):
                    break
        except BaseException:
            task["status"] = "INTERRUPTED"
            write_json(directory/"task.json", task)
            raise
        task["status"] = "COMPLETED" if task["completed"] == target else "PAUSED"
        write_json(directory/"task.json", task)
    return report(root, directory) if task["completed"] == target else task


def report(root, directory):
    import numpy as np
    from scipy.stats import beta, norm
    from agent_core.analysis_outputs import write_csv
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    directory = Path(directory).resolve()
    task = read_task(directory)
    verify_baseline(task, root)
    chunks = load_shards(directory, task)
    total = task["immutable"]["n_trials"]
    if task["completed"] != total:
        raise ValueError("Empirical significance is reported only for the complete recorded ensemble")
    source_ts = np.concatenate([x["source_ts"] for x in chunks])
    stack_ts = np.concatenate([x["stack_ts"] for x in chunks])
    max_ts = source_ts.max(axis=1)
    observed = task["immutable"]["observed"]
    normalized = task["immutable"]["normalized"]
    rows = []
    def add(scope, name, ts, distribution):
        k = int(np.count_nonzero(distribution >= ts))
        p = (k+1)/(total+1)
        row = dict(scope=scope, name=name, TS=float(ts), exceedances=k, n_trials=total,
            p_value=p, significance=float(norm.isf(p)) if p < 1 else None,
            significance_boundary="negative_infinity" if p == 1 else None)
        for level in (.68, .95):
            alpha = 1-level
            row[f"p_lower_{int(100*level)}"] = 0. if k == 0 else float(beta.ppf(alpha/2, k, total-k+1))
            row[f"p_upper_{int(100*level)}"] = 1. if k == total else float(beta.ppf(1-alpha/2, k+1, total-k))
        rows.append(row)
    single = normalized["analysis_type"] == "single_source"
    if single or normalized["catalog_operation"] in {"scan", "scan_and_stack"}:
        for i, item in enumerate(observed["source_results"]):
            add("source_local", item["source_name"], item["fit"]["TS"], source_ts[:, i])
            if not single:
                add("catalog_max_TS", item["source_name"], item["fit"]["TS"], max_ts)
    if not single and normalized["catalog_operation"] in {"stack", "scan_and_stack"}:
        add("stack", "catalog", observed["stack_result"]["TS"], stack_ts)
    table = directory/"empirical_results.csv"
    write_csv(table, list(rows[0]), rows)
    figures = Path(root)/"figures"/("td_trials_" + task["request_sha256"][:16])
    figures.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    if single or normalized["catalog_operation"] in {"scan", "scan_and_stack"}:
        ax.hist(max_ts, bins=40, histtype="step", label="Source TS" if single else "Catalog maximum TS")
    if not single and normalized["catalog_operation"] in {"stack", "scan_and_stack"}:
        ax.hist(stack_ts, bins=40, histtype="step", label="Stack TS")
    ax.set(xlabel="TS", ylabel="Background trials")
    ax.legend()
    files = dict(results=str(table))
    for suffix in ("png", "pdf"):
        path = figures/("background_ts."+suffix)
        fig.savefig(path, dpi=170)
        files[suffix] = str(path)
    plt.close(fig)
    result = dict(status="COMPLETED", n_trials=total, rows=rows, request_sha256=task["request_sha256"],
        p_value_method="(N(TS_bg >= TS_obs)+1)/(N_trials+1)",
        uncertainty="Clopper-Pearson fixed-N binomial intervals; fixed target, no significance-based stopping",
        baseline_review=task["baseline_review"], generated_files=files,
        artifact_sha256={key: sha256_file(path) for key, path in files.items()})
    from agent_core.time_dependent_standard_results import finalize_time_dependent_results
    result["standardized_results"] = finalize_time_dependent_results(
        root, directory, task, chunks
    )
    write_json(directory/"report.json", result)
    return result
