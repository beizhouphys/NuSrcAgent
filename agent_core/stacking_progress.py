"""Observational stacking-fit ETA; never controls the optimizer or likelihood."""
from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
from statistics import median
from agent_core.stage_progress import environment_identity, error_summary
from time import monotonic

from agent_core import progress as progress_module
from agent_core.environment import _required_paths
from agent_core.file_cache import sha256_file
from agent_core.simple_yaml import load_simple_yaml


SETTING_KEYS = ('likelihood_mode', 'gamma_mode', 'gamma_seed', 'ns_seed', 'gamma_bounds',
    'ns_bounds', 'random_seed', 'data_selection', 'background_pdf_version',
    'event_abs_dec_max_deg', 'event_dec_min_deg', 'event_dec_max_deg', 'source_dec_window',
    'signal_energy_declination_mode', 'signal_energy_gamma_interpolation',
    'source_ra_scramble_seed', 'event_ra_scramble_seed', 'fit_procedure', 'event_counts')


def signature(sources, settings):
    payload = dict(sources=[[float(s['ra_rad']), float(s['dec_rad']), float(s.get('w_model', 1.))]
                            for s in sources], settings={k: settings[k] for k in SETTING_KEYS})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def historical_settings(result, normalized):
    seeds, bounds = result['fit_seeds'], result['fit_bounds']
    settings = {key: result.get(key) for key in SETTING_KEYS}
    settings.update(gamma_seed=seeds['gamma_skyllh'] if result['gamma_mode']=='fitted' else result['gamma'],
        ns_seed=seeds['ns'], gamma_bounds=bounds['gamma_skyllh'], ns_bounds=bounds['ns'],
        random_seed=normalized['random_seed'], source_ra_scramble_seed=result['ra_scramble']['source_seed'],
        event_ra_scramble_seed=result['ra_scramble']['event_seed'])
    return settings


def matching_history(root, key, input_hashes, packages, n_sources):
    """Use only call counts from reviewed, matched fits; never reuse old speed."""
    references = []
    directory = Path(root)/'data_output/runs'
    for path in sorted(directory.glob('run*/report.yaml'), reverse=True)[:64]:
        try:
            # Avoid parsing full source results for irrelevant samples.
            header = path.open(encoding='utf-8')
            with header:
                prefix = header.read(1200)
            if f'n_sources: {n_sources}\n' not in prefix:
                continue
            run = path.parent
            review = json.loads((run/'review.json').read_text())
            if review.get('status') not in ('pass', 'warning'):
                continue
            report = load_simple_yaml(path.read_text())
            if report['analysis'].get('catalog_operation') not in ('stack', 'scan_and_stack'):
                continue
            result = report['result']
            if result.get('stacking_phase') == 'flux':
                continue
            normalized = load_simple_yaml((run/'config.normalized.yaml').read_text())
            sources = [dict(ra_rad=s['ra_rad'], dec_rad=s['dec_rad'], w_model=s['weight']) for s in normalized['sources']]
            if signature(sources, historical_settings(result, normalized)) != key:
                continue
            provenance = load_simple_yaml((run/'provenance.yaml').read_text())
            if any(provenance['packages'].get(k) != v for k,v in packages.items()):
                continue
            old_hashes = provenance['input_sha256']
            if any(old_hashes.get(str(Path(root)/relative)) != digest for relative,digest in input_hashes.items()):
                continue
            status = result['minimizer_status']
            count = int(status['n_llhratio_func_calls'])
            if count < 1 or int(status['warnflag']) != 0:
                continue
            references.append(dict(report=str(path), evaluations=count, timing=result.get('fit_timing', {})))
            if len(references) == 5:
                break
        except (OSError, ValueError, KeyError, TypeError):
            continue  # A missing or incompatible old report is not a fit failure.
    return references


class StackingFitProgress:
    """Observe PDF recomputation separately from inexpensive cached evaluations.

    Matched completed traces provide a remaining-work template. Current cost-class
    speeds rescale that template. Unknown stopping times remain explicitly uncertain.
    """
    def __init__(self, command, references=(), fitted_gamma=True, clock=monotonic, cost_state=None):
        self.command, self.clock, self.cost_state = command, clock, cost_state
        self.references = list(references)
        self.started = clock()
        self.durations, self.kinds, self.predictions = [], [], []
        self.completed_at = []
        self.last_completed = self.started
        self.last_emitted = self.last_prediction = -math.inf
        self.environment = environment_identity()
        self.templates = [r['timing'] for r in references
                          if r.get('timing', {}).get('version') == 2
                          and r['timing'].get('environment') == self.environment]
        self.initial_budget = float(median(r['evaluations'] for r in references)) if references else None
        self.budget = self.initial_budget
        self.previous_provider, self.previous_phase = command.phase_provider, command.phase
        command.phase, command.phase_provider = None, self.snapshot
        command.emit()

    def _forecast(self, now):
        n = len(self.durations)
        forecasts = []
        for template in self.templates:
            durations, kinds = template['evaluation_seconds'], template['cost_classes']
            if n >= len(durations) or kinds[:n] != self.kinds:
                continue
            scales = {}
            for kind in set(kinds):
                ratios = [self.durations[i]/durations[i] for i in range(n)
                          if kinds[i] == kind and durations[i] > 0]
                # Warm full-PDF calls estimate machine speed for the first/cold call.
                scales[kind] = median(ratios[-8:]) if ratios else 1.
            forecasts.append(sum(durations[i]*scales[kinds[i]] for i in range(n,len(durations))))
        age = max(0., now-self.last_completed)
        if forecasts:
            estimate = max(0., median(forecasts)-age)
            return estimate, 'matched_cost_sequence_rescaled_by_class', len(forecasts)
        if self.budget is not None and n == self.budget:
            return None, 'reference_endpoint_reached_waiting_for_optimizer', 0
        full = [d for d,k in zip(self.durations,self.kinds) if k == 'pdf_recomputed']
        if not full or self.budget is None:
            return None, 'no_comparable_stopping_history', 0
        # Legacy history supplies only call counts. Cheap calls never reduce this rate.
        rate = median(full[-8:])
        return max(0., rate*max(1.,self.budget-n)-age), 'cost_class_speed_and_legacy_call_count', 0

    def snapshot(self, now):
        count = len(self.durations)
        estimate, basis, matched = self._forecast(now)
        age = max(0., now-self.last_completed)
        if estimate is not None and estimate <= 0:
            estimate = None  # An overdue forecast is not evidence that work is finished.
            basis = 'forecast_overdue_waiting_for_completion'
        row = dict(phase='joint stacking fit', estimate_scope='stacking_fit_only',
            completed_evaluations=count, estimated_total_evaluations=self.budget,
            evaluation_budget_is_estimated=True, estimate_is_heuristic=True,
            historical_reference_count=len(self.references), matched_cost_templates=matched,
            historical_speed_used=bool(matched), estimate_basis=basis,
            phase_elapsed_seconds=max(0., now-self.started), remaining_seconds=estimate,
            remaining_seconds_range=None, estimate_age_seconds=age,
            estimate_status='estimated_from_cost_classes' if estimate is not None else basis,
            cost_class_counts={kind:self.kinds.count(kind) for kind in set(self.kinds)},
            evaluation_budget_extended=self.budget is not None and self.budget>self.initial_budget,
            estimate_note='Fit-only forecast; matched cost sequence, not a fixed stopping count. No calibrated interval with fewer than three independent error histories.')
        # Historical held-out errors, never errors from this unfinished fit.
        errors = [abs(p['signed_error_seconds']) for t in self.templates
                  for p in t.get('prediction_errors', []) if p.get('remaining_seconds') is not None]
        histories = sum(bool(t.get('prediction_errors')) for t in self.templates)
        if estimate is not None and histories >= 3 and errors:
            margin = sorted(errors)[math.ceil(.9*len(errors))-1]
            row['remaining_seconds_range'] = [max(0.,estimate-margin),estimate+margin]
            row['interval_basis'] = 'past_independent_absolute_prediction_errors_90th_percentile'
        if estimate is not None and now-self.last_prediction >= 5.:
            self.predictions.append(dict(elapsed_seconds=now-self.started,
                completed_evaluations=count, remaining_seconds=estimate, estimate_basis=basis))
            self.last_prediction = now
        return row

    def evaluate(self, function, *args, **kwargs):
        before = self.cost_state() if self.cost_state is not None else None
        started = self.clock()
        result = function(*args, **kwargs)
        ended = self.clock()
        after = self.cost_state() if self.cost_state is not None else None
        kind = ('cold_start' if not self.durations else
                'pdf_recomputed' if self.cost_state is None or before != after else 'pdf_reused')
        with self.command.lock:
            self.durations.append(max(1e-9,ended-started));self.kinds.append(kind)
            self.last_completed = ended
            self.completed_at.append(ended-self.started)
            if self.budget is not None and len(self.durations)>self.budget:
                self.budget=len(self.durations)+max(3.,math.ceil(self.initial_budget*.25))
        if ended-self.last_emitted>=1.:
            self.command.emit();self.last_emitted=ended
        return result

    def close(self):
        elapsed=max(0.,self.clock()-self.started)
        with self.command.lock:
            self.command.phase_provider,self.command.phase=self.previous_provider,self.previous_phase
        errors=[dict(p,actual_remaining_seconds=max(0.,elapsed-p['elapsed_seconds']),
                     signed_error_seconds=p['remaining_seconds']-max(0.,elapsed-p['elapsed_seconds']))
                for p in self.predictions]
        return dict(version=2,completed_evaluations=len(self.durations),fit_wall_seconds=elapsed,
            evaluation_seconds=self.durations,evaluation_completed_seconds=self.completed_at,
            cost_classes=self.kinds,environment=self.environment,
            initial_evaluation_budget=self.initial_budget,final_evaluation_budget=self.budget,
            references=[dict(report=r.get('report'),evaluations=r['evaluations']) for r in self.references],
            prediction_errors=errors,prediction_error_summary=error_summary(errors),
            strategy='matched_cost_sequence_with_current_class_speed',scientific_behavior_changed=False)


def start_stacking_progress(root, sources, settings, cost_state=None):
    command = progress_module._active
    if command is None or len(sources) < 2:
        return None
    key = signature(sources, settings)
    # Input/code validation remains the backend's responsibility. Old timing
    # references are optional and cannot authorize any scientific change.
    references = []
    try:
        root = Path(root).resolve()
        inputs = {str(p): sha256_file(root/p) for p in _required_paths('icecube_public_ps_14yr_dr2', settings['likelihood_mode'])}
        packages = {name:version(name) for name in ('skyllh','numpy','scipy')}
        references = matching_history(root, key, inputs, packages, len(sources))
    except (OSError, ValueError, KeyError):
        pass
    return StackingFitProgress(command, references, settings['gamma_mode']=='fitted', cost_state=cost_state)
