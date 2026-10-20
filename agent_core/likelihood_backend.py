from __future__ import annotations

from pathlib import Path

from agent_core.p_value import local_p_value_estimate
from agent_core.schemas import ConfigError, NormalizedAnalysis
from analysis_backend.dr1_catalog import run_catalog_time_integrated
from analysis_backend.dr1_single_source import run_single_source_time_integrated

DR2_SAMPLE = "icecube_public_ps_14yr_dr2"


def run_likelihood_backend(normalized: NormalizedAnalysis, repo_root: str | Path | None = None) -> dict[str, object]:
    if normalized.time_mode != "time_integrated":
        raise ConfigError("likelihood backend Phase 1.1 only supports time_integrated")
    if normalized.sample == DR2_SAMPLE:
        try:
            from analysis_backend.skyllh_dr2_stacking import run_dr2_stacking, run_dr2_single_source
        except ModuleNotFoundError as exc:
            raise ConfigError("the 14-year DR2 backend requires the pinned SkyLLH v26 environment") from exc
        specs = [{"name": source.name, "ra_rad": source.ra_rad, "dec_rad": source.dec_rad, "w_model": source.weight} for source in normalized.sources]
        gamma_legacy = float(normalized.spectral_indices[0])
        options = dict(repo_root=repo_root or ".", gamma_mode=normalized.gamma_mode, gamma=abs(gamma_legacy), random_seed=normalized.random_seed, likelihood_mode=normalized.likelihood_mode, event_abs_dec_max_deg=normalized.event_abs_dec_max_deg, event_dec_min_deg=normalized.event_dec_min_deg, event_dec_max_deg=normalized.event_dec_max_deg)
        operation = normalized.catalog_operation if normalized.analysis_type == "catalog_stacking" else "stack"
        backend_name = "skyllh_v26_dr2_spatial_only" if normalized.likelihood_mode == "spatial_only" else "skyllh_v26_dr2_spatial_energy"
        limit_options = dict(flux_upper_limit_cl=normalized.flux_upper_limit_cl, flux_upper_limit_gammas=normalized.flux_upper_limit_gammas)
        if normalized.analysis_type == "single_source":
            result = run_dr2_single_source(specs, source_dec_window_deg=normalized.source_dec_window_deg,
                flux_measurement_ts_threshold=normalized.flux_measurement_ts_threshold, fit_procedure=normalized.fit_procedure, **limit_options, **options)
        else:
            result = {} if operation == "scan" else run_dr2_stacking(specs, fit_procedure=normalized.fit_procedure, **options)
        if operation != "scan":
            result.update({"ts": result["TS"], "best_fit_ns": result["ns"]})
        result.update({"backend": backend_name})
        if normalized.analysis_type == "catalog_stacking":
            result["catalog_operation"] = operation
        if operation in {"scan", "scan_and_stack"}:
            from analysis_backend.skyllh_dr2_catalog_scan import run_individual_source_scan
            scan_options = dict(options, fit_procedure=normalized.scan_fit_procedure or getattr(normalized, "fit_procedure", "skyllh_lbfgs_v1"))
            result["source_results"] = run_individual_source_scan(specs, source_dec_window_deg=normalized.source_dec_window_deg, **limit_options, **scan_options)
            result["scan_fit_procedure"] = scan_options["fit_procedure"]
            result["catalog_post_trial_p"] = None
            result["catalog_post_trial_note"] = "Local estimates use the declared Gamma-mode half-chi-square approximation; reporting adds the analytic independent-source catalog correction. Empirical calibration is unavailable."
        for fit in [result, *(item["fit"] for item in result.get("source_results", []))]:
            if "TS" in fit:
                fit.update(local_p_value_estimate(fit["TS"], normalized.gamma_mode))
        return result
    if normalized.sample != "icecube_public_ps_10yr":
        raise ConfigError(f"unsupported data sample: {normalized.sample}")
    if normalized.analysis_type == "catalog_stacking":
        return run_catalog_time_integrated(normalized, repo_root=repo_root or ".")
    if normalized.analysis_type != "single_source":
        raise ConfigError("unsupported analysis type")
    if len(normalized.sources) != 1:
        raise ConfigError("likelihood backend Phase 1.1 expects exactly one source")
    source = normalized.sources[0]
    return run_single_source_time_integrated(source.ra_deg, source.dec_deg, repo_root=repo_root or ".", gamma=normalized.spectral_indices[0])
