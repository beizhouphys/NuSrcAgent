"""Observational stacking-fit ETA; never controls the optimizer or likelihood."""
from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
from statistics import mean, median
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
            references.append(dict(report=str(path), evaluations=count))
            if len(references) == 5:
                break
        except (OSError, ValueError, KeyError, TypeError):
            continue  # A missing or incompatible old report is not a fit failure.
    return references


class StackingFitProgress:
    """A revisable call-count prior times measured current evaluation durations.

    Unknown optimizer stopping time prevents a completion percentage. The range
    is heuristic, not a confidence interval or an optimizer limit. A first cold
    evaluation is excluded from the rolling speed once warm samples exist.
    """
    def __init__(self, command, references=(), fitted_gamma=True, clock=monotonic):
        self.command, self.clock = command, clock
        self.references = list(references)
        self.started = clock()
        self.durations = []
        self.last_completed = self.started
        self.last_emitted = -math.inf
        self.initial_budget = (float(median(r['evaluations'] for r in references)) if references
                               else (32. if fitted_gamma else 12.))
        self.budget = self.initial_budget
        self.previous_provider = command.phase_provider
        self.previous_phase = command.phase
        command.phase = None
        command.phase_provider = self.snapshot
        command.emit()

    def snapshot(self, now):
        count = len(self.durations)
        row = dict(phase='joint stacking fit', estimate_scope='stacking_fit_only',
            completed_evaluations=count, estimated_total_evaluations=self.budget,
            evaluation_budget_is_estimated=True, estimate_is_heuristic=True,
            historical_reference_count=len(self.references), historical_speed_used=False,
            estimate_basis=('matched_reviewed_fit_call_count_and_current_evaluation_times' if self.references
                            else 'heuristic_call_budget_and_current_evaluation_times'),
            phase_elapsed_seconds=max(0., now-self.started), remaining_seconds=None,
            remaining_seconds_range=None, estimate_status='awaiting_first_evaluation',
            estimate_note='Revisable optimizer ETA; no fixed iteration count or completion percentage. Excludes artifacts and review.')
        if not count:
            return row
        warm = self.durations[1:] or self.durations
        rate = mean(warm[-5:])
        age = max(0., now-self.last_completed)
        # A slow in-flight evaluation revises the speed instead of yielding zero
        # while the optimizer is still running. Exceeded budgets are extended.
        rate = max(rate, age)
        horizon = max(1., self.budget-count)
        remaining = max(rate*horizon-age, rate*.1)
        low = max(0., rate*max(1., self.budget*.5-count)-age)
        high = max(remaining, rate*max(horizon, self.budget*1.5-count)-age)
        row.update(remaining_seconds=remaining, remaining_seconds_range=[low, high],
            estimate_status='estimated_from_evaluations', seconds_per_evaluation=rate,
            estimate_age_seconds=age, evaluation_budget_extended=self.budget>self.initial_budget)
        return row

    def evaluate(self, function, *args, **kwargs):
        started = self.clock()
        result = function(*args, **kwargs)
        ended = self.clock()
        with self.command.lock:
            self.durations.append(max(1e-9, ended-started))
            self.last_completed = ended
            if len(self.durations) > self.budget:
                self.budget = len(self.durations)+max(3., math.ceil(self.initial_budget*.25))
        if ended-self.last_emitted >= 1.:
            self.command.emit()
            self.last_emitted = ended
        return result

    def close(self):
        elapsed = max(0., self.clock()-self.started)
        with self.command.lock:
            self.command.phase_provider = self.previous_provider
            self.command.phase = self.previous_phase
        return dict(completed_evaluations=len(self.durations), fit_wall_seconds=elapsed,
            evaluation_seconds=self.durations, initial_evaluation_budget=self.initial_budget,
            final_evaluation_budget=self.budget, references=self.references,
            strategy='current_evaluation_speed_with_revisable_call_count_prior', scientific_behavior_changed=False)


def start_stacking_progress(root, sources, settings):
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
    return StackingFitProgress(command, references, settings['gamma_mode']=='fitted')
