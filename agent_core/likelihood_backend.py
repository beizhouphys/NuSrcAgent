from __future__ import annotations

from pathlib import Path

from agent_core.p_value import local_p_value_estimate
from agent_core.schemas import ConfigError, NormalizedAnalysis
from analysis_backend.dr1_catalog import run_catalog_time_integrated
from analysis_backend.dr1_single_source import run_single_source_time_integrated

DR2_SAMPLE = "icecube_public_ps_14yr_dr2"


def run_likelihood_backend(normalized: NormalizedAnalysis, repo_root: str | Path | None = None, stacking_primary=None, workers: int = 1) -> dict[str, object]:
    if normalized.time_mode == "time_dependent":
        from analysis_backend.skyllh_dr2_time_dependent import run_time_dependent
        if normalized.sample != DR2_SAMPLE or (normalized.analysis_type == "catalog_stacking" and normalized.catalog_operation != "scan"):
            raise ConfigError("Time-dependent runtime supports only DR2 single-source analysis and independent catalog scans")
        return run_time_dependent(normalized, repo_root or ".", workers)
    if normalized.time_mode != "time_integrated":
        raise ConfigError("likelihood backend Phase 1.1 only supports time_integrated")
    if normalized.sample == DR2_SAMPLE:
        try:
            from analysis_backend.skyllh_dr2_stacking import run_dr2_stacking, run_dr2_single_source, run_dr2_flux_suite
        except ModuleNotFoundError as exc:
            raise ConfigError("the 14-year DR2 backend requires the pinned SkyLLH v26 environment") from exc
        specs = [{"name": source.name, "ra_rad": source.ra_rad, "dec_rad": source.dec_rad, "w_model": source.weight} for source in normalized.sources]
        gamma_legacy = float(normalized.spectral_indices[0])
        options = dict(repo_root=repo_root or ".", gamma_mode=normalized.gamma_mode, gamma=-gamma_legacy, random_seed=normalized.random_seed, likelihood_mode=normalized.likelihood_mode, event_abs_dec_max_deg=normalized.event_abs_dec_max_deg, event_dec_min_deg=normalized.event_dec_min_deg, event_dec_max_deg=normalized.event_dec_max_deg)
        if normalized.spectrum:
            options.update(spectrum=normalized.spectrum, gamma=0.)
        if normalized.gamma_bounds:
            options.update(gamma_min=-normalized.gamma_bounds[1], gamma_max=-normalized.gamma_bounds[0])
        operation = normalized.catalog_operation if normalized.analysis_type == "catalog_stacking" else "stack"
        backend_name = "skyllh_v26_dr2_spatial_only" if normalized.likelihood_mode == "spatial_only" else "skyllh_v26_dr2_spatial_energy"
        limit_options = dict(flux_upper_limit_cl=normalized.flux_upper_limit_cl, flux_upper_limit_gammas=normalized.flux_upper_limit_gammas)
        if normalized.analysis_type == "single_source":
            if normalized.signal_energy_gamma_interpolation is not None:
                options["signal_energy_gamma_interpolation"] = normalized.signal_energy_gamma_interpolation
            result = run_dr2_single_source(specs, source_dec_window_deg=normalized.source_dec_window_deg,
                flux_measurement_ts_threshold=normalized.flux_measurement_ts_threshold, fit_procedure=normalized.fit_procedure, **limit_options, **options)
        else:
            if stacking_primary is not None:
                settings = normalized.stacking_flux
                result = run_dr2_flux_suite(specs, primary_result=stacking_primary,
                    flux_upper_limit_cl=settings["upper_limit_cl"],
                    flux_upper_limit_gammas=settings["upper_limit_gammas"],
                    flux_measurement_ts_threshold=settings["measurement_ts_threshold"],
                    fit_procedure=normalized.fit_procedure, **options)
                result["stacking_phase"] = "flux"
            else:
                result = {} if operation == "scan" else run_dr2_stacking(specs, fit_procedure=normalized.fit_procedure, **options)
                if normalized.stacking_flux:
                    result["stacking_phase"] = "primary"
        if operation != "scan":
            result.update({"ts": result["TS"], "best_fit_ns": result["ns"]})
        result.update({"backend": backend_name})
        if normalized.analysis_type == "catalog_stacking":
            result["catalog_operation"] = operation
        if operation in {"scan", "scan_and_stack"} and stacking_primary is None:
            from analysis_backend.skyllh_dr2_catalog_scan import run_individual_source_scan
            scan_options = dict(options, fit_procedure=normalized.scan_fit_procedure or getattr(normalized, "fit_procedure", "skyllh_lbfgs_v1"))
            result["source_results"] = run_individual_source_scan(specs, workers=workers, source_dec_window_deg=normalized.source_dec_window_deg, **limit_options, **scan_options)
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
        return run_catalog_time_integrated(normalized, repo_root=repo_root or ".", workers=workers)
    if normalized.analysis_type != "single_source":
        raise ConfigError("unsupported analysis type")
    if len(normalized.sources) != 1:
        raise ConfigError("likelihood backend Phase 1.1 expects exactly one source")
    source = normalized.sources[0]
    return run_single_source_time_integrated(source.ra_deg, source.dec_deg, repo_root=repo_root or ".",
        gamma=normalized.spectral_indices[0], spectrum=normalized.spectrum,
        source_dec_window_deg=normalized.source_dec_window_deg,
        event_abs_dec_max_deg=normalized.event_abs_dec_max_deg,
        event_dec_min_deg=normalized.event_dec_min_deg, event_dec_max_deg=normalized.event_dec_max_deg)
