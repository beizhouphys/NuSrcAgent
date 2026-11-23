"""Time profiles on the existing DR2 SkyLLH spatial/energy likelihood.

Each source is fitted independently. The time-dependent detector yield is
the steady yield times integral(profile over uptime) / integrated livetime.
An outer bounded, explicitly seeded Powell search profiles the original
SkyLLH n and s maximization; no background trials or flux fits run here.
"""
from __future__ import annotations

from itertools import product
from time import monotonic

import numpy as np
from scipy.optimize import minimize
from skyllh.core.flux_model import BoxTimeFluxProfile, GaussianTimeFluxProfile
from skyllh.core.pdfratio import PDFRatio
from skyllh.core.random import RandomStateService
from skyllh.core.services import DatasetSignalWeightFactorsService
from skyllh.i3.livetime import I3Livetime

from agent_core.temporal import parameter_mode, temporal_errors, unavailable_significance

_WORKER_RUNTIME_CACHE = {}


class TemporalPDFRatio(PDFRatio):
    def __init__(self, base, controller, index):
        super().__init__(cfg=base.cfg, sig_param_names=base.sig_param_names,
                         bkg_param_names=base.bkg_param_names)
        self.base, self.controller, self.index = base, controller, index

    def initialize_for_new_trial(self, tdm, tl=None, **kwargs):
        self.base.initialize_for_new_trial(tdm, tl=tl, **kwargs)

    def get_ratio(self, tdm, src_params_recarray, tl=None):
        return self.base.get_ratio(tdm, src_params_recarray, tl=tl) * self.controller.ratios[self.index]

    def get_gradient(self, tdm, src_params_recarray, fitparam_id, tl=None):
        return self.base.get_gradient(tdm, src_params_recarray, fitparam_id, tl=tl) * self.controller.ratios[self.index]


class TemporalDatasetWeights(DatasetSignalWeightFactorsService):
    def __init__(self, source_service, controller):
        super().__init__(source_service)
        self.controller = controller

    def calculate(self):
        weights, gradients = self.src_detsigyield_weights_service.get_weights()
        factors = self.controller.yield_factors
        values = np.sum(weights, axis=1) * factors
        total = np.sum(values)
        if not np.isfinite(total) or total <= 0:
            raise ValueError("Temporal profile has zero detector acceptance")
        self._f_j = values / total
        self._f_j_grads = {}
        for index, gradient in gradients.items():
            derivative = np.sum(gradient, axis=1) * factors
            self._f_j_grads[index] = (derivative * total - values * np.sum(derivative)) / total**2


class TemporalController:
    def __init__(self, analysis, settings):
        errors = temporal_errors(settings)
        if errors:
            raise ValueError("; ".join(errors))
        self.analysis, self.settings = analysis, settings
        self.livetimes = [I3Livetime.from_grl_data(data.grl) for data in analysis.data_list]
        self.times = [np.asarray(data.exp["time"], dtype=float) for data in analysis.data_list]
        self.run_stop_equalities = []
        for times, livetime in zip(self.times, self.livetimes, strict=True):
            on = livetime.is_on(times)
            # IC59 contains one released event exactly equal to a published
            # run stop at the CSV precision. Extend the PDF's support to those
            # measure-zero endpoints; preserve every original event/time and
            # every uptime integral. Do not tolerate positive offsets or gaps.
            at_stop = ~on & np.isin(times, livetime.uptime_mjd_intervals_arr[:, 1])
            self.run_stop_equalities.append(int(np.count_nonzero(at_stop)))
            if not np.all(np.isfinite(times)) or not np.all(on | at_stop):
                raise ValueError("DR2 event times must be finite and inside the published good-run intervals")
        self.ratios = []
        self.yield_factors = np.ones(len(self.times))
        self.integrals = []
        self.current = None
        self.evaluations = []

    def set_profile(self, t0, width):
        cfg = self.analysis.cfg
        if self.settings["profile"] == "gaussian":
            profile = GaussianTimeFluxProfile(t0=t0, sigma_t=width, cfg=cfg)
        else:
            profile = BoxTimeFluxProfile(t0=t0, tw=width, cfg=cfg)
        integrals, ratios = [], []
        for times, livetime in zip(self.times, self.livetimes, strict=True):
            # Same integral as SkyLLH SignalTimePDF, with explicit interval
            # intersection: v26's helper raises IndexError for empty overlaps,
            # including profiles wholly within a detector downtime gap.
            intervals = livetime.uptime_mjd_intervals_arr
            start = np.maximum(intervals[:, 0], profile.t_start)
            stop = np.minimum(intervals[:, 1], profile.t_stop)
            overlap = stop > start
            integral = float(np.sum(profile.get_integral(start[overlap], stop[overlap]))) if np.any(overlap) else 0.
            if not np.isfinite(integral) or integral < 0:
                raise ValueError("Invalid time-profile integral")
            integrals.append(integral)
            ratios.append(np.zeros(len(times)) if integral == 0 else
                          np.asarray(profile(t=times), dtype=float) * livetime.livetime / integral)
        self.integrals = np.asarray(integrals)
        self.yield_factors = self.integrals / np.array([lt.livetime for lt in self.livetimes])
        self.ratios = ratios
        self.current = (float(t0), float(width))
        return bool(np.any(self.integrals > 0))

    def maximize(self, seed):
        settings, analysis = self.settings, self.analysis
        names = [name for name in ("t0", "width") if parameter_mode(settings[name]) == "fitted"]
        bounds = [settings[name]["bounds"] for name in names]
        # Scale MJD and log(width) to [0,1] for the outer optimizer.
        def decode(point):
            values = {name: settings[name]["value"] for name in ("t0", "width") if name not in names}
            for name, limits, coordinate in zip(names, bounds, point, strict=True):
                low, high = np.log(limits) if name == "width" else limits
                value = low + coordinate * (high-low)
                decoded = float(np.exp(value) if name == "width" else value)
                values[name] = min(limits[1], max(limits[0], decoded))
            return values["t0"], values["width"]
        def encode(values):
            point = []
            for name, limits, value in zip(names, bounds, values, strict=True):
                low, high = np.log(limits) if name == "width" else limits
                point.append(((np.log(value) if name == "width" else value)-low)/(high-low))
            return point
        best, cache = None, {}
        def objective(point):
            nonlocal best
            key = tuple(float(x) for x in point)
            if key in cache:
                return cache[key]
            started = monotonic()
            t0, width = decode(point)
            if not self.set_profile(t0, width):
                self.evaluations.append(dict(t0_mjd=t0, width_days=width, TS=None, ns=None,
                                             seconds=monotonic()-started, nonzero_acceptance=False, s=None))
                cache[key] = 1e100
                return cache[key]
            # initialize_trial is done once. Only the time ratios and dataset
            # weights change; observed events and frozen PDFs remain identical.
            value, parameters, status = analysis.llhratio.maximize(rss=RandomStateService(seed=int(seed)))
            if status.get("warnflag") != 0 or not np.isfinite(value):
                raise ValueError("Time-dependent inner SkyLLH maximization failed; scientific settings retained")
            ts = float(analysis.calculate_test_statistic(log_lambda=value, fitparam_values=parameters))
            fit = analysis.pmm.create_global_params_dict(gflp_values=parameters)
            row = dict(t0_mjd=t0, width_days=width, TS=ts, ns=float(fit["ns"]),
                       seconds=monotonic()-started, nonzero_acceptance=True,
                       s=float(fit["gamma"]) if "gamma" in analysis.pmm.global_paramset.floating_params_name_list else None)
            self.evaluations.append(row)
            if best is None or ts > best[0]:
                best = (ts, fit, status, t0, width)
            cache[key] = -ts
            return -ts
        analysis.initialize_trial([data.exp for data in analysis.data_list])
        searches = []
        if names:
            from agent_core.progress import track_progress
            seeds = [encode(values) for values in product(*(settings[name]["seeds"] for name in names))]
            for point in track_progress(seeds, "temporal seed grid", total=len(seeds)):
                objective(point)
            for point in track_progress(seeds, "temporal search starts", total=len(seeds)):
                fit = minimize(objective, point, method="Powell", bounds=[(0., 1.)]*len(names),
                    options={key: settings["search"][key] for key in ("maxiter", "xtol", "ftol")})
                searches.append(dict(success=bool(fit.success), message=str(fit.message),
                                     nfev=int(fit.nfev), x=fit.x.tolist()))
            if not all(item["success"] for item in searches):
                raise ValueError("Temporal search did not converge; bounds and search settings retained")
        else:
            objective([])
        if best is None:
            raise ValueError("Temporal search has no profile with nonzero detector acceptance")
        ts, parameters, status, t0, width = best
        self.set_profile(t0, width)
        # Restore all SkyLLH services to the recorded maximum, including spectral index.
        floating = np.array([parameters[name] for name in analysis.pmm.global_paramset.floating_params_name_list])
        analysis.llhratio.evaluate(floating)
        self.metadata = dict(settings=settings, t0_mjd=t0, width_days=width,
            width_meaning="sigma_t" if settings["profile"] == "gaussian" else "full_box_duration",
            t0_mode=parameter_mode(settings["t0"]), width_mode=parameter_mode(settings["width"]),
            fit_procedure="grid_powell_profile_skyllh_lbfgs_v1" if names else "fixed_profile_skyllh_lbfgs_v1",
            search_results=searches, evaluations=self.evaluations,
            datasets={dataset.name: dict(livetime_days=float(lt.livetime), profile_integral_days=float(integral),
                yield_factor=float(factor), n_events=len(times), event_time_at_run_stop_count=count)
                for dataset, lt, integral, factor, times, count in zip(analysis.dataset_list, self.livetimes,
                    self.integrals, self.yield_factors, self.times, self.run_stop_equalities, strict=True)},
            event_time_support="published_run_stop_equality_included_no_time_changes",
            background_time_model="uniform_livetime", statistic="2_log_likelihood_ratio_no_duration_penalty",
            empirical_calibration_available=False)
        return ts, parameters, status


def attach_temporal_profile(analysis, settings):
    controller = TemporalController(analysis, settings)
    service = TemporalDatasetWeights(analysis.src_detsigyield_weights_service, controller)
    # The existing property enforces the SkyLLH service type.
    analysis._ds_sig_weight_factors_service = service
    analysis._pdfratio_list = [TemporalPDFRatio(ratio, controller, index)
                              for index, ratio in enumerate(analysis._pdfratio_list)]
    analysis.llhratio = analysis.construct_llhratio(analysis.llhratio.minimizer)
    return controller


def _fit_source(job):
    source, options = job
    from analysis_backend.skyllh_dr2_stacking import run_dr2_stacking
    return run_dr2_stacking([dict(source, w_model=1.)], runtime_cache=_WORKER_RUNTIME_CACHE, **options)


def run_time_dependent(normalized, root, workers=1):
    from agent_core.cpu import ordered_worker_map
    _WORKER_RUNTIME_CACHE.clear()
    specs = [dict(name=source.name, ra_rad=source.ra_rad, dec_rad=source.dec_rad, w_model=1.)
             for source in normalized.sources]
    options = dict(repo_root=str(root), likelihood_mode=normalized.likelihood_mode,
        gamma_mode=normalized.gamma_mode, gamma=-normalized.spectral_indices[0],
        random_seed=normalized.random_seed, temporal_settings=normalized.temporal,
        event_abs_dec_max_deg=normalized.event_abs_dec_max_deg,
        event_dec_min_deg=normalized.event_dec_min_deg, event_dec_max_deg=normalized.event_dec_max_deg,
        source_dec_window_deg=normalized.source_dec_window_deg,
        signal_energy_gamma_interpolation=normalized.signal_energy_gamma_interpolation,
        spectrum=normalized.spectrum or None)
    if normalized.gamma_bounds:
        options.update(gamma_min=-normalized.gamma_bounds[1], gamma_max=-normalized.gamma_bounds[0])
    if normalized.analysis_type == "single_source":
        result = _fit_source((specs[0], options))
        result.update(ts=result["TS"], best_fit_ns=result["ns"])
    else:
        from agent_core.progress import track_progress
        fits = track_progress(ordered_worker_map(_fit_source, [(source, options) for source in specs], workers),
                              "time-dependent catalog source fits", total=len(specs))
        records = [dict(source_number=index+1, source_name=source.name, ra_deg=source.ra_deg,
                        dec_deg=source.dec_deg, fit=fit)
                   for index, (source, fit) in enumerate(zip(normalized.sources, fits, strict=True))]
        result = dict(source_results=records, catalog_operation="scan", time_mode="time_dependent",
                      catalog_post_trial_p=None, catalog_post_trial_significance=None)
    result.update(backend="skyllh_v26_dr2_time_dependent", **unavailable_significance())
    _WORKER_RUNTIME_CACHE.clear()
    return result
