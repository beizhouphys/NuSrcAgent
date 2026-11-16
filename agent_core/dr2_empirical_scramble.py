"""Persistent conditional event-RA calibration using the unchanged DR2 LLH.

Trials inherit the reviewed single-source or stacking configuration,
including fixed/fitted Gamma, event selections and supplied spectra. No PDF optimization or analytic TS calibration.
"""
from __future__ import annotations

from agent_core.progress import update_work_progress

import csv
from contextlib import redirect_stderr, redirect_stdout
import errno
import fcntl
import hashlib
import json
import io
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait

from agent_core.dr2_pdf_release import (
    BACKGROUND_PDF_PROVENANCE, RC1_MANIFEST,
    sha256, verify_background_release, verify_v3_release,
)
from agent_core.task_state import create_task_record, parameter, save_task, utc_now


THREAD_VARIABLES = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                    'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS')
DISTRIBUTED_SEED_NAMESPACE = 0xD157BEEF
MACOS_DATALESS_FLAG = 0x40000000


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    tmp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text())


def read_available_shard_checkpoint(path):
    """Read one local shard checkpoint, or identify an unavailable Dropbox placeholder."""
    path = Path(path)
    if getattr(path.stat(), 'st_flags', 0) & MACOS_DATALESS_FLAG:
        return None, 'macOS dataless Dropbox placeholder'
    try:
        return read_json(path), None
    except OSError as exc:
        if exc.errno == errno.ETIMEDOUT:
            return None, 'Dropbox checkpoint read timed out'
        raise


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def event_seed_for_index(config, index):
    """Return the deterministic event-RA seed, preserving the pilot sequence."""
    import numpy as np
    if index < 0:
        return None
    overrides = config.get('event_seed_overrides', {})
    if str(index) in overrides:
        return int(overrides[str(index)])
    if config.get('distributed_shard'):
        sequence = np.random.SeedSequence([
            int(config['catalog_seed']), DISTRIBUTED_SEED_NAMESPACE,
            int(config['shard_number']), int(index),
        ])
        return int(sequence.generate_state(1, dtype=np.uint64)[0])
    if config.get('event_seeds') is not None:
        if index < len(config['event_seeds']) or not _discard_negative_ts(config):
            return int(config['event_seeds'][index])
    children = np.random.SeedSequence(int(config['catalog_seed'])).spawn(index + 2)
    return int(children[index + 1].generate_state(1)[0])


def trial_id_for_index(config, index):
    if index < 0:
        return 'observed'
    if config.get('distributed_shard'):
        return f"{config['shard_id']}:{index:06d}"
    return f'legacy:{index:06d}'


def next_available_trial_index(completed_indices, in_flight_indices=(), start_index=0):
    """Return the lowest trial index that is neither complete nor in flight."""
    unavailable = {int(index) for index in completed_indices}
    unavailable.update(int(index) for index in in_flight_indices)
    index = start_index
    while index in unavailable:
        index += 1
    return index


def _discard_negative_ts(config):
    # Existing task configurations retain their recorded execution protocol.
    return config.get('negative_ts_policy') == 'discard_without_record'


def _trial_cursor(out):
    path = Path(out)/'control.json'
    return int(read_json(path).get('next_trial_index', 0)) if path.exists() else 0


def _advance_trial_cursor(out, completed):
    # Generic execution progress only; no rejected-fit records or counters.
    path = Path(out)/'control.json'
    control = read_json(path) if path.exists() else {}
    control['next_trial_index'] = next_available_trial_index(
        completed, start_index=int(control.get('next_trial_index', 0)))
    write_json(path, control)


def _load_analysis(root, baseline_task):
    """Read a sealed primary result without modifying or rerunning its task."""
    from importlib.metadata import version
    from agent_core.task_state import load_task, stable_payload_hash
    from agent_core.agent_orchestrator import build_analysis_payload
    from agent_core.simple_yaml import load_simple_yaml
    from agent_core.review import review_run
    task, task_path = load_task(baseline_task, root)
    if task['status'] in ('READY', 'RUNNING', 'REVIEWING', 'AWAITING_CONFIRMATION', 'DRAFT'):
        raise ValueError('Background trials require a reviewed primary analysis')
    payload = build_analysis_payload(task, root)
    single = task.get('stages', {}).get('llh', {})
    stack = task.get('stacking_stages', {}).get('primary', {})
    files = []
    if single:
        checkpoint = Path(single['checkpoint'])
        if single.get('status') not in ('pass', 'warning') or sha256(checkpoint) != single['checkpoint_sha256']:
            raise ValueError('Invalid primary checkpoint or review')
        saved = read_json(checkpoint)
        if saved['full_request_sha256'] != stable_payload_hash(payload):
            raise ValueError('Scientific request changed after primary fit')
        sealed = saved['files_sha256']
        result = saved['result']
        folder = Path(saved['run_directory'])
        files.append(checkpoint)
    elif stack:
        if stack.get('status') not in ('COMPLETED', 'COMPLETED_WITH_WARNINGS'):
            raise ValueError('Stacking primary did not pass review')
        if stack['request_sha256'] != stable_payload_hash(payload):
            raise ValueError('Scientific request changed after primary fit')
        sealed = stack['artifacts_sha256']
        result = read_json(stack['result_file'])
        folder = Path(stack['run_directory'])
    else:
        if task['status'] not in ('COMPLETED', 'COMPLETED_WITH_WARNINGS'):
            raise ValueError('No successfully reviewed primary result')
        folder = Path(task['artifacts']['run_directory'])
        sealed = {}
        result = load_simple_yaml((folder/'report.yaml').read_text())['result']
    for name, expected in sealed.items():
        if sha256(name) != expected:
            raise ValueError('Primary artifact changed: '+name)
    normalized = load_simple_yaml((folder/'config.normalized.yaml').read_text())
    if normalized['sample'] != 'icecube_public_ps_14yr_dr2' or normalized['time_mode'] != 'time_integrated':
        raise ValueError('Background trials currently require DR2 time-integrated analysis')
    if normalized['analysis_type'] not in ('single_source', 'catalog_stacking') or 'TS' not in result:
        raise ValueError('Require a single-source or stacking result, not a scan maximum')
    if normalized['analysis_type'] == 'catalog_stacking' and normalized.get('catalog_operation') == 'scan':
        raise ValueError('Catalog-global scan calibration is not implemented')
    if review_run(str(folder), str(root), write_artifacts=False)['status'] == 'fail':
        raise ValueError('Primary analysis failed scientific/artifact review')
    provenance = load_simple_yaml((folder/'provenance.yaml').read_text())
    if any(version(name) != expected for name, expected in provenance['packages'].items() if expected is not None):
        raise ValueError('Primary runtime packages changed')
    # Orchestration may gain follow-ups; the scientific implementation must match.
    scientific_code = {name: expected for name, expected in provenance['code_sha256'].items()
                       if name.startswith('analysis_backend/') or name == 'agent_core/spectrum.py'}
    for name, expected in {**provenance['input_sha256'], **scientific_code}.items():
        path = Path(name) if Path(name).is_absolute() else root/name
        if sha256(path) != expected:
            raise ValueError('Scientific input/code changed after primary fit: '+name)
        files.append(path)
    files.extend(path for path in folder.iterdir() if path.is_file())
    return task, normalized, result, files


def prepare(root, out, request, n_trials=100, seed=2026091501, workers=2,
            baseline_task=None, continuous=False):
    """Prepare matched event-RA trials for an existing reviewed analysis."""
    root, out = Path(root).resolve(), Path(out).resolve()
    if not baseline_task:
        raise ValueError('prepare requires --baseline-task')
    if not request.strip() or n_trials < 1 or workers < 1 or seed < 0:
        raise ValueError('Require request, positive counts and nonnegative seed')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory must be new or empty; existing trials are unchanged')
    baseline, normalized, observed, paths = _load_analysis(root, baseline_task)
    if observed.get('background_pdf_version') != 'v3':
        raise ValueError('New follow-ups require the production frozen v3 PDFs')
    verify_v3_release(root)
    source_specs = [dict(name=row['name'], ra_rad=row['ra_rad'], dec_rad=row['dec_rad'], w_model=row['weight'])
                    for row in normalized['sources']]
    bounds = observed['fit_bounds']
    seeds = observed['fit_seeds']
    fitted = normalized['gamma_mode'] == 'fitted'
    gamma_bounds = bounds['gamma_skyllh'] if fitted else [1., 6.]
    options = dict(likelihood_mode=normalized['likelihood_mode'], gamma_mode=normalized['gamma_mode'],
        gamma=seeds['gamma_skyllh'] if fitted else (observed['gamma'] if observed['gamma'] is not None else 0.),
        gamma_min=gamma_bounds[0], gamma_max=gamma_bounds[1], ns_seed=seeds['ns'], ns_max=bounds['ns'][1],
        random_seed=normalized['random_seed'], fit_procedure=observed['fit_procedure'],
        data_selection=observed['data_selection'], background_pdf_version=observed['background_pdf_version'],
        event_abs_dec_max_deg=normalized.get('event_abs_dec_max_deg'),
        event_dec_min_deg=normalized.get('event_dec_min_deg'), event_dec_max_deg=normalized.get('event_dec_max_deg'),
        source_dec_window_deg=normalized.get('source_dec_window_deg') if normalized['analysis_type']=='single_source' else None,
        signal_energy_gamma_interpolation=observed.get('signal_energy_gamma_interpolation'),
        signal_energy_declination_mode=observed.get('signal_energy_declination_mode') or 'source',
        spectrum=normalized.get('spectrum') or None)
    config = dict(n_trials=None if continuous else n_trials, continuous=continuous,
        n_sources=len(source_specs), catalog_seed=seed, workers=workers, numerical_threads_per_worker=1,
        sample=normalized['sample'], **{key: options[key] for key in ('data_selection','likelihood_mode','gamma_mode',
            'gamma','gamma_min','gamma_max','ns_seed','ns_max','fit_procedure','background_pdf_version')},
        fit_seed=normalized['random_seed'], fit_options=options,
        weight_mode='inherited_from_primary', negative_ts_policy='discard_without_record',
        randomization='independent uniform event RA; other event quantities preserved',
        hypothesis_family='one specified '+('single-source analysis' if normalized['analysis_type']=='single_source' else 'stacking analysis'),
        analysis_type=normalized['analysis_type'], expected_event_selection=observed['event_selection'],
        expected_event_counts=observed['event_counts'],
        stopping_rule='continuous; user-requested graceful stop' if continuous else 'fixed N retained trials',
        p_estimator='(k+1)/(N+1); inclusive TS >= observed')
    out.mkdir(parents=True, exist_ok=True)
    write_json(out/'catalog.json', source_specs)
    with (out/'catalog.csv').open('w', newline='') as stream:
        import numpy as np
        writer=csv.writer(stream);writer.writerow(['name','ra_deg','dec_deg','w_model'])
        writer.writerows((row['name'], np.rad2deg(row['ra_rad']), np.rad2deg(row['dec_rad']), row['w_model']) for row in source_specs)
    write_json(out/'baseline_task.json', baseline)
    # Freeze source/settings snapshots and all runtime code, inputs and responses.
    paths += [root/'run_agent_wrap.py', *list((root/'agent_core').glob('*.py')),
              *list((root/'analysis_backend').glob('*.py')),
              out/'catalog.json', out/'catalog.csv', out/'baseline_task.json']
    if observed.get('spectrum_response'):
        from analysis_backend.spectrum_response import verify_response
        response_path=Path(observed['spectrum_response']['manifest'])
        response=verify_response(response_path)
        paths += [response_path, *(Path(row['file']) for row in response['datasets'])]
    inputs=[dict(path=str(path),sha256=sha256(path)) for path in sorted(set(paths)) if path.is_file()]
    task=create_task_record(request, 'empirical_background_calibration', 'dr2_empirical_scramble',
        'Matched event-RA trials for a reviewed '+normalized['analysis_type'], {'files':inputs},
        {'gamma':parameter(-options['gamma'],'inherited',True), 'experiment':parameter(config,'user',True)})
    task['baseline_analysis']=dict(task_id=baseline['task_id'], snapshot=str(out/'baseline_task.json'),
        primary_warnings=baseline.get('single_source_llh_summary',{}).get('warnings',[]) or
                         baseline.get('stacking_stages',{}).get('primary',{}).get('warnings',[]) or
                         observed.get('warnings', []))
    task['parameter_provenance']=dict(scientific_settings='inherited from reviewed primary; only event RA changes',
        trial_seed='user or recorded default; does not change optimizer RNG', workers='user or recorded default')
    task['artifacts']={'output_directory':str(out)}
    task['planned_tools']=['run_agent_wrap.py dr2-empirical-scramble']
    task['request_sha256']=digest({'config':config,'inputs':inputs})
    central=save_task(task,root);task['central_task_path']=str(central)
    write_json(out/'control.json',dict(stop_requested=False,next_trial_index=0))
    row=dict(index=-1,trial_id='observed',kind='observed',request_sha256=task['request_sha256'],
        event_ra_scramble_seed=None,result=observed,review=fit_review(observed,config),
        elapsed_seconds=0.,completed_at_utc=utc_now(),primary_maximization_repeated=False)
    if row['review']['status']=='fail':
        raise ValueError('Imported primary result failed trial review: '+str(row['review']))
    write_json(out/'fits/observed.json',row)
    write_json(central,task);write_json(out/'task.json',task)
    return dict(task_id=task['task_id'],status=task['status'],request_sha256=task['request_sha256'],
        baseline_task_id=baseline['task_id'],observed_imported=True,config=config)


def fit_review(result, config):
    import math
    failures, warnings = [], []
    if (config.get('fit_procedure', 'skyllh_lbfgs_v1') != 'skyllh_lbfgs_v1'
            or result.get('fit_procedure', 'skyllh_lbfgs_v1') != 'skyllh_lbfgs_v1'):
        failures.append('unsupported or inconsistent fit procedure')
    for name in (('TS', 'ns') if config.get('fit_options', {}).get('spectrum') else ('TS', 'ns', 'gamma')):
        if not math.isfinite(result[name]):
            failures.append(f'nonfinite {name}')
    if (result['TS'] < 0 or not 0 <= result['ns'] <= config['ns_max'] or
            (config.get('gamma_mode', 'fitted') == 'fitted' and not config['gamma_min'] <= result['gamma'] <= config['gamma_max'])):
        failures.append('fit outside constrained domain')
    if result['minimizer_status'].get('warnflag', -1) != 0:
        failures.append('optimizer did not converge')
    if (result['gamma_mode'] != config.get('gamma_mode', 'fitted') or
            result['background_pdf_version'] != config['background_pdf_version']):
        failures.append('wrong spectral-index mode or background version')
    if result['n_sources'] != config['n_sources'] or result['event_selection'] != config.get('expected_event_selection', 'all_events'):
        failures.append('wrong catalog size or event selection')
    if config.get('gamma_mode', 'fitted') == 'fitted' and min(abs(result['gamma']-config['gamma_min']), abs(result['gamma']-config['gamma_max'])) < 1e-5:
        warnings.append('Spectral index at a fit boundary')
    if abs(result['ns']-config['ns_max']) < 1e-5:
        warnings.append('ns at upper boundary')
    if 'fit_options' in config:
        options = config['fit_options']
        for key in ('likelihood_mode', 'signal_energy_gamma_interpolation', 'spectrum'):
            if (result.get(key) or None) != (options.get(key) or None):
                failures.append('changed '+key)
        if result['event_counts'] != config['expected_event_counts']:
            failures.append('changed event counts')
        if result.get('fit_bounds', {}).get('ns') != [0., options['ns_max']]:
            failures.append('changed ns bounds')
    return dict(status='fail' if failures else ('warning' if warnings else 'pass'), failures=failures, warnings=warnings)


def _is_skippable_negative_ts(row, config):
    """Only a converged, otherwise valid background fit may be skipped."""
    import math
    result = row['result']
    return (row['index'] >= 0 and row['review']['status'] == 'fail'
            and row['review']['failures'] == ['fit outside constrained domain']
            and math.isfinite(result['TS']) and result['TS'] < 0.
            and result['minimizer_status'].get('warnflag') == 0
            and row['review'] == fit_review(result, config))


def _skipped_negative_ts_rows(out, config, accepted_hashes):
    out = Path(out)
    skipped = []
    paths = [*(out/'skipped_negative_ts').glob('trial_*.json'),
             *(out/'deferred_failed_fits').glob('*/trial_*.json')]
    for path in sorted(paths):
        row = read_json(path)
        index = row['index']
        if (path.name != f'trial_{index:04d}.json'
                or row['request_sha256'] not in accepted_hashes
                or row.get('trial_id') != trial_id_for_index(config, index)
                or row.get('event_ra_scramble_seed') != event_seed_for_index(config, index)
                or row['result']['ra_scramble']['event_seed'] != event_seed_for_index(config, index)
                or not _is_skippable_negative_ts(row, config)):
            raise ValueError(f'Invalid skipped negative-TS checkpoint: {path}')
        skipped.append((path, row))
    return skipped


def _skip_negative_ts_checkpoint(out, row, config, request_hash):
    """Move an invalid fit out of the statistical ensemble without losing it."""
    out = Path(out)
    index = row['index']
    source = out/'fits'/f'trial_{index:04d}.json'
    target = out/'skipped_negative_ts'/source.name
    if (row['request_sha256'] != request_hash
            or row.get('trial_id') != trial_id_for_index(config, index)
            or row.get('event_ra_scramble_seed') != event_seed_for_index(config, index)
            or row['result']['ra_scramble']['event_seed'] != event_seed_for_index(config, index)
            or not _is_skippable_negative_ts(row, config)
            or read_json(source) != row
            or target.exists()):
        raise ValueError(f'Cannot skip invalid or duplicate negative-TS trial {index}')
    target.parent.mkdir(parents=True, exist_ok=True)
    source.replace(target)
    print(f'{utc_now()} SKIP trial_{index:04d}: TS={row["result"]["TS"]:.8g}, '
          f'seed={row["event_ra_scramble_seed"]}, checkpoint={target}', flush=True)


def fit_one(root, out, config, request_hash, index):
    if config.get('fit_procedure', 'skyllh_lbfgs_v1') != 'skyllh_lbfgs_v1':
        raise ValueError('Unsupported empirical fit procedure; existing checkpoints are unchanged')
    # Spawned workers inherit thread limits before importing numerical libraries.
    from analysis_backend.skyllh_dr2_stacking import run_dr2_stacking
    out = Path(out)
    label = 'observed' if index < 0 else f'trial_{index:04d}'
    started = time.monotonic()
    def evaluate():
        if 'fit_options' in config:
            return run_dr2_stacking(read_json(out/'catalog.json'), repo_root=root,
                event_ra_scramble_seed=event_seed_for_index(config, index), **config['fit_options'])
        return run_dr2_stacking(read_json(out/'catalog.json'), repo_root=root,
            likelihood_mode='spatial_energy', gamma_mode='fitted', gamma=config['gamma'],
            gamma_min=config['gamma_min'], gamma_max=config['gamma_max'],
            ns_seed=config['ns_seed'], ns_max=config['ns_max'], random_seed=config['fit_seed'],
            event_ra_scramble_seed=event_seed_for_index(config, index),
            data_selection='full14', background_pdf_version=config['background_pdf_version'])

    if index >= 0 and _discard_negative_ts(config):
        # Delay all worker output until the TS is known; discarded fits leave
        # neither checkpoints nor worker-log messages, including backend output.
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = evaluate()
        except Exception:
            print(stdout.getvalue(), end='', flush=True)
            print(stderr.getvalue(), end='', file=sys.stderr, flush=True)
            raise
        if result['TS'] < 0:
            return None
        print(stdout.getvalue(), end='', flush=True)
        print(stderr.getvalue(), end='', file=sys.stderr, flush=True)
    else:
        print(f'{utc_now()} START {label}', flush=True)
        result = evaluate()
    review = fit_review(result, config)
    row = dict(index=index, trial_id=trial_id_for_index(config, index),
               shard_id=config.get('shard_id'), request_sha256=request_hash,
               event_ra_scramble_seed=event_seed_for_index(config, index),
               result=result, review=review,
               elapsed_seconds=time.monotonic()-started, completed_at_utc=utc_now(),
               numerical_thread_limits={k: os.environ.get(k) for k in THREAD_VARIABLES})
    write_json(out/'fits'/f'{label}.json', row)
    print(f'{utc_now()} DONE {label}: TS={result["TS"]:.8g}, seconds={row["elapsed_seconds"]:.1f}, review={review["status"]}', flush=True)
    return row


def _z_value(probability):
    import numpy as np
    from scipy.stats import norm
    z = float(norm.isf(probability))
    return z if np.isfinite(z) else ('+infinity' if z > 0 else '-infinity')


def _z_interval(p_interval):
    return [_z_value(p_interval[1]), _z_value(p_interval[0])]


def beta_binomial_confidence_sequence(k, n, confidence, a=.5, b=.5):
    """Two-sided beta-binomial mixture confidence sequence for Bernoulli p.

    The returned sequence has simultaneous coverage over all sample sizes by
    Ville's inequality, so it remains valid when status is checked repeatedly
    and the run is stopped at a data-dependent time.
    """
    import numpy as np
    from scipy.optimize import brentq
    from scipy.special import betaln
    if not 0 <= k <= n or n < 1 or not 0 < confidence < 1:
        raise ValueError('Invalid binomial confidence-sequence inputs')
    threshold = -np.log1p(-confidence)
    constant = betaln(k+a, n-k+b) - betaln(a, b)

    def log_mixture_ratio(p):
        if p <= 0:
            return np.inf if k else constant
        if p >= 1:
            return np.inf if k < n else constant
        return constant - k*np.log(p) - (n-k)*np.log1p(-p)

    center = k/n
    eps = np.finfo(float).eps
    if k == 0 or log_mixture_ratio(eps) <= threshold:
        lo = 0.
    else:
        lo = float(brentq(lambda p: log_mixture_ratio(p)-threshold, eps, center))
    if k == n or log_mixture_ratio(1-eps) <= threshold:
        hi = 1.
    else:
        hi = float(brentq(lambda p: log_mixture_ratio(p)-threshold, center, 1-eps))
    return [lo, hi]


def empirical_summary(observed_ts, trial_ts):
    import numpy as np
    from scipy.stats import beta
    values = np.asarray(trial_ts, dtype=float)
    if not len(values) or not np.isfinite(observed_ts) or not np.all(np.isfinite(values)):
        raise ValueError('Require finite observed and background statistics')
    n, k = len(values), int(np.count_nonzero(values >= observed_ts))
    p = (k+1)/(n+1)
    intervals = {}
    confidence_sequences = {}
    for confidence in (.68, .95):
        alpha = 1-confidence
        lo = 0. if k == 0 else float(beta.ppf(alpha/2, k, n-k+1))
        hi = 1. if k == n else float(beta.ppf(1-alpha/2, k+1, n-k))
        intervals[str(confidence)] = dict(p=[lo, hi], z=_z_interval([lo, hi]))
        sequence = beta_binomial_confidence_sequence(k, n, confidence)
        confidence_sequences[str(confidence)] = dict(p=sequence, z=_z_interval(sequence))
    return dict(n_trials=n, exceedances=k, raw_exceedance_fraction=k/n,
                p_pre=p, p_post=p, significance_one_sided=_z_value(p),
                fixed_n_mc_intervals=intervals,
                anytime_valid_confidence_sequences=confidence_sequences,
                mc_intervals=intervals, zero_exceedances=(k == 0),
                mc_standard_error_approx=None if k in (0,n) else float(np.sqrt((k/n)*(1-k/n)/n)),
                p_resolution=1/(n+1))


def report(out, persist=True):
    out = Path(out)
    task = read_json(out/'task.json')
    config = task['parameters']['experiment']['value']
    rows = [read_json(p) for p in sorted((out/'fits').glob('*.json'))]
    accepted_hashes = {task['request_sha256'], *task.get('accepted_checkpoint_request_sha256', [])}
    skipped = _skipped_negative_ts_rows(out, config, accepted_hashes)
    for row in rows:
        if row['request_sha256'] not in accepted_hashes:
            raise ValueError('Checkpoint request hash mismatch')
        if row['review'] != fit_review(row['result'], config):
            raise ValueError('Checkpoint review mismatch')
        index = row['index']
        expected_seed = event_seed_for_index(config, index)
        if row['result']['ra_scramble']['event_seed'] != expected_seed:
            raise ValueError('Checkpoint event seed mismatch')
    indices = [r['index'] for r in rows]
    all_indices = indices + [row['index'] for _, row in skipped]
    if len(all_indices) != len(set(all_indices)):
        raise ValueError('Duplicate trial index')
    observed = next((r for r in rows if r['index'] == -1), None)
    trials = [r for r in rows if r['index'] >= 0]
    failures = [r['index'] for r in rows if r['review']['status'] == 'fail']
    if observed and any(r['result']['event_counts'] != observed['result']['event_counts'] for r in trials):
        raise ValueError('Event counts changed between realizations')
    requested_trials = config.get('n_trials')
    complete = requested_trials is not None and (
        observed is not None and len(trials) == requested_trials if _discard_negative_ts(config)
        else set(indices) == {-1, *range(requested_trials)})
    result = dict(status=task['status'], completed_trials=len(trials), requested_trials=requested_trials,
                  observed_complete=observed is not None, failed_fits=failures,
                  skipped_negative_ts_fits=[dict(index=row['index'], trial_id=row['trial_id'],
                                                  event_ra_seed=row['event_ra_scramble_seed'],
                                                  TS=row['result']['TS'], checkpoint=str(path),
                                                  checkpoint_sha256=sha256(path)) for path, row in skipped],
                  attempted_trials=len(trials)+len(skipped),
                  boundary_warning_fits=[r['index'] for r in rows if r['review']['warnings']],
                  request_sha256=task['request_sha256'])
    if _discard_negative_ts(config):
        result.pop('attempted_trials')  # Discarded attempts are not counted.
        if not skipped:
            result.pop('skipped_negative_ts_fits')
        result['negative_ts_policy'] = config['negative_ts_policy']
    if 'baseline_analysis' in task:
        result['baseline_analysis']=task['baseline_analysis']
        result['hypothesis_family']=config['hypothesis_family']
    if rows:
        average = sum(r['elapsed_seconds'] for r in rows)/len(rows)
        result['mean_fit_seconds'] = average
        result['mean_background_fit_seconds'] = (sum(r['elapsed_seconds'] for r in trials)/len(trials)
                                                 if trials else None)
        if requested_trials is not None:
            result['estimated_total_fit_wall_hours'] = average*(requested_trials+1)/config['workers']/3600
    if observed and trials and not failures:
        result['statistics'] = empirical_summary(observed['result']['TS'], [r['result']['TS'] for r in trials])
        result['observed'] = {k: observed['result'][k] for k in ('TS','ns','gamma')}
        result['statistics_status'] = 'final_fixed_n' if complete else 'running_snapshot'
        if skipped:
            result['statistics_caution'] = ('Negative-TS fits were excluded. The empirical statistics use only '
                                            'valid fits; skipped-fit selection may bias the null distribution.')
    if config.get('continuous'):
        completed_indices = [r['index'] for r in trials] + [row['index'] for _, row in skipped]
        result['next_trial_index'] = next_available_trial_index(
            completed_indices, start_index=_trial_cursor(out) if _discard_negative_ts(config) else 0)
        result['highest_completed_trial_index'] = max(completed_indices, default=-1)
        result['stop_requested'] = read_json(out/'control.json').get('stop_requested', False) if (out/'control.json').exists() else False
        result['snapshot_note'] = ('Anytime-valid confidence sequences retain simultaneous coverage under repeated status checks; '
                                   'fixed-N intervals are descriptive snapshots only when stopping is data-dependent.')
    if persist:
        write_json(out/'progress.json', result)
    return result


def run(root, out, resume=False, max_hours=2., max_fits=None):
    root, out = Path(root).resolve(), Path(out).resolve()
    if max_hours <= 0:
        raise ValueError('Require positive operational time budget')
    if max_fits is not None and max_fits < 1:
        raise ValueError('Require positive fit limit')
    with (out/'worker.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('An ensemble worker is already active')
        return _run_locked(root, out, resume, max_hours, max_fits)


def _run_locked(root, out, resume, max_hours, max_fits):
    task = read_json(out/'task.json')
    if task['status'] != 'READY' and not (resume and task['status'] in ('RUNNING', 'PAUSED')):
        raise ValueError('Need READY task, or explicit resume of interrupted/paused task')
    config = task['parameters']['experiment']['value']
    if config.get('fit_procedure', 'skyllh_lbfgs_v1') != 'skyllh_lbfgs_v1':
        raise ValueError('Unsupported empirical fit procedure; existing checkpoints are unchanged')
    if digest({'config': config, 'inputs': task['inputs']['files']}) != task['request_sha256']:
        raise ValueError('Configuration hash mismatch')
    for item in task['inputs']['files']:
        if sha256(item['path']) != item['sha256']:
            raise ValueError('Input/code changed: '+item['path'])
    verify_background_release(root, config['background_pdf_version'])
    prior = report(out)
    if (out/'control.json').exists():
        control=read_json(out/'control.json');control['stop_requested']=False
        write_json(out/'control.json',control)
    if prior['failed_fits']:
        raise ValueError('Failed fit needs scientific review; no automatic retry')
    for name in THREAD_VARIABLES:
        os.environ[name] = '1'
    task['status'] = 'RUNNING'
    task['attempts'].append(dict(started_at_utc=utc_now(), request_sha256=task['request_sha256'],
                                pid=os.getpid(), max_hours=max_hours, max_fits=max_fits, resume=resume))
    def persist():
        write_json(out/'task.json', task)
        write_json(task['central_task_path'], task)
    persist()
    start = time.monotonic()
    timing_target = max(0, config['n_trials'] - prior['completed_trials'])
    update_work_progress('background trials', 0, timing_target, 0.)
    try:
        pending = [i for i in [-1, *range(config['n_trials'])]
                   if not (out/'fits'/('observed.json' if i < 0 else f'trial_{i:04d}.json')).exists()]
        completed = {read_json(path)['index'] for path in (out/'fits').glob('trial_*.json')}
        if _discard_negative_ts(config):
            pending = [] if prior['observed_complete'] else [-1]
            for _ in range(max(0, config['n_trials'] - prior['completed_trials'])):
                index = next_available_trial_index(completed, pending, start_index=_trial_cursor(out))
                pending.append(index)
        limited = max_fits is not None and len(pending) > max_fits
        if limited and not _discard_negative_ts(config):
            pending = pending[:max_fits]
        with ProcessPoolExecutor(max_workers=config['workers'], mp_context=multiprocessing.get_context('spawn'),
                                 max_tasks_per_child=1) as pool:
            offset = 0
            while offset < len(pending):
                if (out/'control.json').exists() and read_json(out/'control.json').get('stop_requested'):
                    task['status']='PAUSED'
                    task['pause_reason']='User-requested graceful stop after in-flight fits checkpointed'
                    break
                if max_fits is not None and offset >= max_fits:
                    task['status'] = 'PAUSED'
                    task['pause_reason'] = 'Operational fit limit; ensemble remains incomplete'
                    break
                current = report(out)
                elapsed = time.monotonic()-start
                estimate = current.get('mean_fit_seconds', 0.)
                if elapsed + estimate > max_hours*3600:
                    task['status'] = 'PAUSED'
                    task['pause_reason'] = 'Operational wall-time budget; fixed-N ensemble remains incomplete'
                    break
                batch_size = min(config['workers'], max_fits-offset) if max_fits is not None else config['workers']
                batch = pending[offset:offset+batch_size]
                futures = [pool.submit(fit_one, str(root), str(out), config, task['request_sha256'], i) for i in batch]
                results = [f.result() for f in futures]
                if any(r is None for r in results) and not _discard_negative_ts(config):
                    raise ValueError('Missing fit result')
                if any(r is not None and r['review']['status'] == 'fail' for r in results):
                    raise ValueError('Fit review failed; inspect per-fit artifacts before continuing')
                if _discard_negative_ts(config):
                    for index, row in zip(batch, results, strict=True):
                        if row is None:
                            if index < 0:
                                raise ValueError('Missing observed fit')
                            pending.append(max([_trial_cursor(out)-1, *completed, *pending])+1)
                        completed.add(index)
                    _advance_trial_cursor(out, completed)
                offset += len(batch)
                current = report(out)
                update_work_progress('background trials',
                    current['completed_trials'] - prior['completed_trials'], timing_target,
                    time.monotonic() - start)
                print(json.dumps(current, sort_keys=True), flush=True)
            else:
                task['status'] = 'PAUSED' if limited and not _discard_negative_ts(config) else 'COMPLETED_WITH_WARNINGS'
                if task['status'] == 'PAUSED':
                    task['pause_reason'] = 'Timing pilot finished; await owner decision on full trial budget'
        task['attempts'][-1]['ended_at_utc'] = utc_now()
    except Exception as exc:
        task['status'] = 'FAILED'
        task['completion'] = dict(error=repr(exc), status='FAILED')
        task['attempts'][-1]['ended_at_utc'] = utc_now()
        persist()
        write_json(out/'review.json', dict(status='fail', error=repr(exc)))
        write_json(Path(task['central_task_path']).parent/'agent_review.json', read_json(out/'review.json'))
        raise
    finally:
        persist()
    summary = report(out)
    if task['status'] == 'COMPLETED_WITH_WARNINGS':
        if 'statistics' not in summary:
            raise ValueError('Incomplete ensemble cannot be reported as completed')
        review = dict(status='warning', checks=dict(all_requested_fits_present=True, all_fit_reviews_pass=True),
                      warnings=['Finite Monte Carlo precision; report exact binomial intervals.',
                                'Conditional uniform-RA null; PDF residuals can still bias ns/Gamma.',
                                'Uses the existing optimizer; this ensemble is not a general coverage validation.'],
                      boundary_warning_fits=summary['boundary_warning_fits'])
        write_json(out/'review.json', review)
        write_json(Path(task['central_task_path']).parent/'agent_review.json', review)
        task['completion'] = dict(status=task['status'], review=review)
        persist()
    return snapshot(out)


def prepare_continuous(root, out, parent_directory, request, workers=2):
    """Create an unbounded protocol amendment and import every pilot fit."""
    if parent_directory is None:
        raise ValueError('prepare-continuous requires --parent-directory')
    root, out = Path(root).resolve(), Path(out).resolve()
    parent = Path(parent_directory).resolve()
    if not request.strip() or workers < 1:
        raise ValueError('Require request and positive worker count')
    if (out/'task.json').exists():
        raise ValueError('Continuous task already exists')
    parent_task = read_json(parent/'task.json')
    if parent_task['status'] != 'PAUSED':
        raise ValueError('Parent timing pilot must be PAUSED before protocol amendment')
    parent_config = parent_task['parameters']['experiment']['value']
    if parent_config.get('background_pdf_version') != 'v3':
        raise ValueError('Parent task is not the required fitted-Gamma v3 calibration')
    verify_v3_release(root)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(parent/'catalog.json', out/'catalog.json')
    shutil.copy2(parent/'catalog.csv', out/'catalog.csv')
    (out/'fits').mkdir()
    parent_fits = sorted((parent/'fits').glob('*.json'))
    if not parent_fits or not any(path.name == 'observed.json' for path in parent_fits):
        raise ValueError('Parent timing pilot has no observed checkpoint')
    for path in parent_fits:
        shutil.copy2(path, out/'fits'/path.name)

    config = dict(parent_config)
    config.pop('event_seeds', None)
    config.update(n_trials=None, continuous=True, workers=workers,
                  negative_ts_policy='discard_without_record',
                  stopping_rule=('No preset trial cap. Owner may inspect at any time and request a graceful stop; '
                                 'all completed trials remain included. Anytime-valid confidence sequences are primary.'),
                  mc_intervals=('68% and 95% fixed-N Clopper-Pearson snapshots plus beta-binomial mixture '
                                'confidence sequences valid under repeated inspection and optional stopping.'))
    release = verify_v3_release(root)
    paths = [root/p for p in release['files']] + [root/BACKGROUND_PDF_PROVENANCE, root/RC1_MANIFEST]
    data = root/'data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2'
    for folder in ('events', 'uptime', 'irfs'):
        paths.extend((data/folder).glob('*.csv'))
    paths.extend((root/'data_output/signal_energy_pdfs/14yr_dr2').glob('*'))
    paths += [root/'run_agent_wrap.py', Path(__file__),
              root/'analysis_backend/skyllh_dr2_stacking.py',
              root/'analysis_backend/event_pdf_data.py',
              root/'analysis_backend/skyllh_chunked.py',
              root/'analysis_backend/skyllh_dr2_pdfs.py',
              root/'agent_core/dr2_pdf_release.py',
              parent/'task.json', parent/'catalog.json', parent/'catalog.csv',
              out/'catalog.json', out/'catalog.csv', *parent_fits]
    inputs = [dict(path=str(path), sha256=sha256(path)) for path in sorted(set(paths)) if path.is_file()]
    task = create_task_record(request, 'empirical_background_calibration_continuous',
                              'dr2_empirical_scramble_continuous',
                              'Protocol amendment: same fixed catalog and LLH, continuously extended event-RA trials',
                              {'files': inputs}, {'gamma': parameter(-3., 'system_default', True),
                              'experiment': parameter(config, 'user', True)})
    task['parent_task'] = dict(task_id=parent_task['task_id'], directory=str(parent),
                               request_sha256=parent_task['request_sha256'], imported_fits=len(parent_fits),
                               amendment_reason=('Owner-authorized continuation with unchanged scientific settings; '
                                                 'the request records the execution-protocol amendment'))
    accepted_hashes = [parent_task['request_sha256'], *parent_task.get('accepted_checkpoint_request_sha256', [])]
    task['accepted_checkpoint_request_sha256'] = list(dict.fromkeys(accepted_hashes))
    task['parameter_provenance'] = {
        'scientific_configuration': 'unchanged from parent timing pilot',
        'trial_scope': 'user-authorized continuous run without a preset upper bound',
        'monitoring': 'anytime-valid confidence sequences support repeated inspection and optional stopping',
        'workers': 'user; rolling worker queue with one numerical thread per process',
    }
    task['planned_tools'] = ['run_agent_wrap.py dr2-empirical-scramble --action launch|status|snapshot|stop|resume']
    task['request_sha256'] = digest({'config': config, 'inputs': inputs,
                                     'parent_request_sha256': parent_task['request_sha256']})
    task['artifacts'] = {'output_directory': str(out)}
    central = save_task(task, root)
    task['central_task_path'] = str(central)
    write_json(out/'control.json', dict(stop_requested=False, updated_at_utc=utc_now(),
                                          next_trial_index=_trial_cursor(parent)))
    write_json(central, task)
    write_json(out/'task.json', task)
    summary = snapshot(out)
    return dict(task_id=task['task_id'], status=task['status'], request_sha256=task['request_sha256'],
                imported_fits=len(parent_fits), snapshot=summary)


def _background_release_paths(root, version):
    release = verify_background_release(root, version)
    paths = [root/path for path in release['files']]
    if version == 'v3':
        paths += [root/BACKGROUND_PDF_PROVENANCE, root/RC1_MANIFEST]
    return paths


def _register_alias(root, task, catalog_sha256):
    alias = task.get('analysis_alias')
    if not alias:
        return
    path = root/'data_output/diagnostics/background_trial_aliases.json'
    registry = read_json(path) if path.exists() else {'aliases': {}}
    prior = registry['aliases'].get(alias)
    history = list(prior.get('history', [])) if prior else []
    if prior:
        history.append({key: prior[key] for key in
                        ('task_id', 'output_directory', 'request_sha256', 'updated_at_utc') if key in prior})
    config = task['parameters']['experiment']['value']
    registry['aliases'][alias] = {
        'task_id': task['task_id'],
        'entrance_directory': str(root/'data_output/diagnostics'/alias),
        'output_directory': task['artifacts']['output_directory'],
        'request_sha256': task['request_sha256'],
        'background_pdf_version': config['background_pdf_version'],
        'catalog_sha256': catalog_sha256,
        'updated_at_utc': utc_now(),
        'history': history,
    }
    write_json(path, registry)
    _update_alias_entrance(root, alias, registry['aliases'][alias])


def _replace_directory_symlink(path, target):
    path, target = Path(path), Path(target)
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        raise ValueError(f'Alias layout path exists and is not a symlink: {path}')
    path.symlink_to(os.path.relpath(target, path.parent), target_is_directory=True)


def _update_alias_entrance(root, alias, record):
    if not alias or Path(alias).name != alias or alias in ('.', '..'):
        raise ValueError(f'Invalid analysis alias for directory layout: {alias!r}')
    entrance = root/'data_output/diagnostics'/alias
    history = entrance/'history'
    entrance.mkdir(parents=True, exist_ok=True)
    history.mkdir(exist_ok=True)
    _replace_directory_symlink(entrance/'current', record['output_directory'])
    for item in record.get('history', []):
        task_id, output = item.get('task_id'), item.get('output_directory')
        if task_id and output:
            link = history/task_id
            if not link.exists() and not link.is_symlink():
                link.symlink_to(os.path.relpath(output, history), target_is_directory=True)
    readme = (
        f'# {alias}\n\n'
        'Stable entrance for this empirical event-RA background calibration.\n\n'
        '- `current/` resolves to the authoritative task recorded by the alias registry.\n'
        '- `history/` contains prior workflow generations retained for provenance.\n'
        '- `runs/` contains task data created after adoption of this canonical layout.\n\n'
        f"Current task: `{record['task_id']}`  \n"
        f"Background PDF: `{record['background_pdf_version']}`  \n"
        f"Catalog SHA-256: `{record['catalog_sha256']}`\n"
    )
    (entrance/'README.md').write_text(readme)


def prepare_versioned_continuous(root, out, reference_directory, request,
                                 background_version, analysis_alias, workers=2,
                                 import_reference_fits=False):
    """Create a versioned continuous task with the exact reference catalog and seeds."""
    root, out = Path(root).resolve(), Path(out).resolve()
    reference = Path(reference_directory).resolve() if reference_directory else None
    if reference is None:
        raise ValueError('prepare-versioned requires --parent-directory')
    if background_version != 'v3':
        raise ValueError('The release supports frozen background version v3 only')
    if not request.strip() or not analysis_alias.strip() or workers < 1:
        raise ValueError('Require request, analysis alias and positive worker count')
    if (out/'task.json').exists():
        raise ValueError('Versioned continuous task already exists')
    reference_task = read_json(reference/'task.json')
    if reference_task['status'] != 'PAUSED':
        raise ValueError('Reference empirical task must be PAUSED')
    reference_config = reference_task['parameters']['experiment']['value']
    if reference_config.get('gamma_mode') != 'fitted' or not reference_config.get('continuous'):
        raise ValueError('Reference is not a fitted-Gamma continuous empirical task')
    if import_reference_fits and reference_config.get('background_pdf_version') != background_version:
        raise ValueError('Cannot import fits across background-PDF versions')
    _background_release_paths(root, background_version)
    skipped_sources = []
    if import_reference_fits:
        accepted_hashes = {reference_task['request_sha256'],
                           *reference_task.get('accepted_checkpoint_request_sha256', [])}
        skipped_sources = _skipped_negative_ts_rows(reference, reference_config, accepted_hashes)
        if len({path.name for path, _ in skipped_sources}) != len(skipped_sources):
            raise ValueError('Duplicate skipped trial index in reference task')

    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(reference/'catalog.json', out/'catalog.json')
    shutil.copy2(reference/'catalog.csv', out/'catalog.csv')
    (out/'fits').mkdir()
    imported = []
    if import_reference_fits:
        imported = sorted((reference/'fits').glob('*.json'))
        if not imported or not any(path.name == 'observed.json' for path in imported):
            raise ValueError('Reference task has no observed checkpoint')
        for path in imported:
            shutil.copy2(path, out/'fits'/path.name)
        if skipped_sources:
            (out/'skipped_negative_ts').mkdir()
            for path, _ in skipped_sources:
                shutil.copy2(path, out/'skipped_negative_ts'/path.name)

    import_manifest = {
        'created_at_utc': utc_now(),
        'reference_task_id': reference_task['task_id'],
        'reference_request_sha256': reference_task['request_sha256'],
        'reference_output_directory_at_import': str(reference),
        'catalog': {
            'json_sha256': sha256(out/'catalog.json'),
            'csv_sha256': sha256(out/'catalog.csv'),
        },
        'checkpoint_files': [
            {'name': path.name, 'sha256': sha256(out/'fits'/path.name)} for path in imported
        ],
        'skipped_negative_ts_files': [
            {'name': path.name, 'sha256': sha256(out/'skipped_negative_ts'/path.name)}
            for path, _ in skipped_sources
        ],
    }
    write_json(out/'checkpoint_import_manifest.json', import_manifest)

    config = dict(reference_config)
    config.pop('event_seeds', None)
    config.update(
        n_trials=None,
        continuous=True,
        workers=workers,
        background_pdf_version=background_version,
        negative_ts_policy='discard_without_record',
        numerical_threads_per_worker=1,
        stopping_rule=('No preset trial cap. Owner may inspect at any time and request a graceful stop; '
                       'all completed trials remain included. Anytime-valid confidence sequences are primary.'),
        mc_intervals=('68% and 95% fixed-N Clopper-Pearson snapshots plus beta-binomial mixture '
                      'confidence sequences valid under repeated inspection and optional stopping.'),
    )
    paths = _background_release_paths(root, background_version)
    data = root/'data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2'
    for folder in ('events', 'uptime', 'irfs'):
        paths.extend((data/folder).glob('*.csv'))
    paths.extend((root/'data_output/signal_energy_pdfs/14yr_dr2').glob('*'))
    paths += [root/'run_agent_wrap.py', Path(__file__),
              root/'analysis_backend/skyllh_dr2_stacking.py',
              root/'analysis_backend/event_pdf_data.py',
              root/'analysis_backend/skyllh_chunked.py',
              root/'analysis_backend/skyllh_dr2_pdfs.py',
              root/'agent_core/dr2_pdf_release.py',
              out/'catalog.json', out/'catalog.csv',
              out/'checkpoint_import_manifest.json',
              *(out/'fits'/path.name for path in imported),
              *(out/'skipped_negative_ts'/path.name for path, _ in skipped_sources)]
    inputs = [dict(path=str(path), sha256=sha256(path)) for path in sorted(set(paths)) if path.is_file()]
    task = create_task_record(
        request,
        'empirical_background_calibration_continuous',
        'dr2_empirical_scramble_continuous',
        f'Same fixed catalog and event-RA trial sequence with frozen DR2 Bpdf {background_version}',
        {'files': inputs},
        {'gamma': parameter(-3., 'user', True), 'experiment': parameter(config, 'user', True)},
    )
    task['analysis_alias'] = analysis_alias
    task['parent_task'] = {
        'task_id': reference_task['task_id'],
        'directory': str(reference),
        'request_sha256': reference_task['request_sha256'],
        'imported_fits': len(imported),
        'imported_skipped_negative_ts_fits': len(skipped_sources),
        'amendment_reason': ('Code/provenance migration with unchanged v3 scientific configuration'
                             if imported else 'Owner-authorized Bpdf-version comparison using the same catalog and seeds'),
    }
    accepted = []
    if imported:
        accepted = [reference_task['request_sha256'],
                    *reference_task.get('accepted_checkpoint_request_sha256', [])]
    task['accepted_checkpoint_request_sha256'] = list(dict.fromkeys(accepted))
    task['parameter_provenance'] = {
        'scientific_configuration': 'copied from the paused reference except for the recorded Bpdf version',
        'catalog_and_trial_seeds': 'byte-identical catalog and identical deterministic trial-index seed mapping',
        'trial_scope': 'user-authorized continuous run without a preset upper bound',
        'workers': 'user; rolling worker queue with one numerical thread per process',
        'background_pdf_version': f'user-selected frozen {background_version}',
    }
    task['planned_tools'] = ['run_agent_wrap.py dr2-empirical-scramble --action launch|status|snapshot|stop|resume']
    task['request_sha256'] = digest({'config': config, 'inputs': inputs,
                                     'parent_request_sha256': reference_task['request_sha256']})
    task['artifacts'] = {'output_directory': str(out)}
    if imported:
        task['status'] = 'PAUSED'
        task['pause_reason'] = 'Migrated paused checkpoints; await owner resume by analysis alias'
    central = save_task(task, root)
    task['central_task_path'] = str(central)
    write_json(out/'control.json', dict(stop_requested=False, updated_at_utc=utc_now(),
                                          next_trial_index=_trial_cursor(reference) if import_reference_fits else 0))
    write_json(central, task)
    write_json(out/'task.json', task)
    catalog_sha256 = sha256(out/'catalog.json')
    _register_alias(root, task, catalog_sha256)
    summary = snapshot(out) if imported else report(out)
    return dict(task_id=task['task_id'], status=task['status'], analysis_alias=analysis_alias,
                background_pdf_version=background_version, request_sha256=task['request_sha256'],
                catalog_sha256=catalog_sha256, imported_fits=len(imported), snapshot=summary)


def prepare_distributed_shard(root, out, reference_directory, request, analysis_alias,
                              shard_id, shard_number, workers=2):
    """Prepare one host-owned trial stream without touching the canonical alias."""
    root, out = Path(root).resolve(), Path(out).resolve()
    reference = Path(reference_directory).resolve() if reference_directory else None
    if reference is None:
        raise ValueError('prepare-shard requires --parent-directory')
    if not request.strip() or not analysis_alias.strip() or workers < 1:
        raise ValueError('Require request, analysis alias and positive worker count')
    if (not shard_id or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for character in shard_id)
            or Path(shard_id).name != shard_id):
        raise ValueError('Shard id must use lowercase letters, digits, underscores or hyphens')
    if shard_number is None or shard_number < 0:
        raise ValueError('Require a nonnegative stable shard number')
    if (out/'task.json').exists():
        raise ValueError('Distributed shard task already exists')
    reference_task = read_json(reference/'task.json')
    reference_config = reference_task['parameters']['experiment']['value']
    if reference_task['status'] != 'PAUSED':
        raise ValueError('Canonical reference task must be PAUSED before preparing a shard')
    if not reference_config.get('continuous') or reference_config.get('gamma_mode') != 'fitted':
        raise ValueError('Reference is not a fitted-Gamma continuous empirical task')
    background_version = reference_config['background_pdf_version']
    _background_release_paths(root, background_version)
    observed_source = reference/'fits'/'observed.json'
    if not observed_source.exists():
        raise ValueError('Reference task has no observed checkpoint')

    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(reference/'catalog.json', out/'catalog.json')
    shutil.copy2(reference/'catalog.csv', out/'catalog.csv')
    (out/'fits').mkdir()
    shutil.copy2(observed_source, out/'fits'/'observed.json')
    import_manifest = {
        'created_at_utc': utc_now(),
        'reference_task_id': reference_task['task_id'],
        'reference_request_sha256': reference_task['request_sha256'],
        'reference_output_directory_at_import': str(reference),
        'analysis_alias': analysis_alias,
        'shard_id': shard_id,
        'shard_number': shard_number,
        'catalog_sha256': sha256(out/'catalog.json'),
        'observed_checkpoint_sha256': sha256(out/'fits'/'observed.json'),
    }
    write_json(out/'checkpoint_import_manifest.json', import_manifest)

    config = dict(reference_config)
    config.pop('event_seeds', None)
    config.update(
        n_trials=None,
        continuous=True,
        workers=workers,
        numerical_threads_per_worker=1,
        distributed_shard=True,
        negative_ts_policy='discard_without_record',
        shard_id=shard_id,
        shard_number=int(shard_number),
        trial_id_scheme='host-shard-id plus zero-based local counter',
        event_seed_scheme=('uint64 NumPy SeedSequence([catalog_seed, 0xD157BEEF, '
                           'shard_number, local_index])'),
        stopping_rule=('No preset trial cap. This host owns this shard exclusively; graceful stop '
                       'finishes all in-flight fits before pausing.'),
    )
    paths = _background_release_paths(root, background_version)
    data = root/'data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2'
    for folder in ('events', 'uptime', 'irfs'):
        paths.extend((data/folder).glob('*.csv'))
    paths.extend((root/'data_output/signal_energy_pdfs/14yr_dr2').glob('*'))
    paths += [root/'run_agent_wrap.py', Path(__file__),
              root/'analysis_backend/skyllh_dr2_stacking.py',
              root/'analysis_backend/event_pdf_data.py',
              root/'analysis_backend/skyllh_chunked.py',
              root/'analysis_backend/skyllh_dr2_pdfs.py',
              root/'agent_core/dr2_pdf_release.py',
              out/'catalog.json', out/'catalog.csv',
              out/'checkpoint_import_manifest.json', out/'fits'/'observed.json']
    inputs = [dict(path=str(path), sha256=sha256(path))
              for path in sorted(set(paths)) if path.is_file()]
    task = create_task_record(
        request,
        'empirical_background_calibration_distributed_shard',
        'dr2_empirical_scramble_shard',
        f'Host-owned {shard_id} stream for {analysis_alias}',
        {'files': inputs},
        {'gamma': parameter(-3., 'user', True), 'experiment': parameter(config, 'user', True)},
    )
    task['analysis_alias'] = analysis_alias
    task['shard_id'] = shard_id
    task['shard_number'] = int(shard_number)
    task['parent_task'] = {
        'task_id': reference_task['task_id'],
        'directory': str(reference),
        'request_sha256': reference_task['request_sha256'],
        'imported_fits': 1,
        'amendment_reason': 'Owner-authorized multi-host distributed trial stream',
    }
    task['accepted_checkpoint_request_sha256'] = list(dict.fromkeys([
        reference_task['request_sha256'],
        *reference_task.get('accepted_checkpoint_request_sha256', []),
    ]))
    task['parameter_provenance'] = {
        'scientific_configuration': 'copied from the paused canonical reference',
        'catalog': 'byte-identical canonical catalog',
        'trial_identity': f'{shard_id}:local_index with stable shard number {shard_number}',
        'workers': 'user; one numerical thread per worker',
        'ownership': f'only host {shard_id} may write this directory',
    }
    task['planned_tools'] = [
        'run_agent_wrap.py dr2-empirical-scramble --action launch|status|snapshot|stop|resume'
    ]
    task['request_sha256'] = digest({
        'config': config, 'inputs': inputs,
        'parent_request_sha256': reference_task['request_sha256'],
    })
    task['artifacts'] = {'output_directory': str(out)}
    task['status'] = 'PAUSED'
    task['pause_reason'] = 'Prepared distributed shard; await explicit launch'
    central = save_task(task, root)
    task['central_task_path'] = str(central)
    write_json(out/'control.json', dict(stop_requested=False, updated_at_utc=utc_now()))
    write_json(central, task)
    write_json(out/'task.json', task)
    summary = snapshot(out)
    return dict(task_id=task['task_id'], status=task['status'], analysis_alias=analysis_alias,
                background_pdf_version=background_version, shard_id=shard_id,
                shard_number=int(shard_number), request_sha256=task['request_sha256'],
                catalog_sha256=sha256(out/'catalog.json'), snapshot=summary)


def merge_host_shards(root, out, analysis_alias, shard_id, incoming_shard_id, request):
    """Consolidate two stopped host streams without conflating their event-RA seeds.

    Original task directories and byte-identical checkpoints are archived. The
    active shard receives copies with one local index namespace; imported seeds
    are explicit overrides and every source checksum is recorded in the manifest.
    """
    root = Path(root).resolve()
    entrance = root/'data_output/diagnostics'/analysis_alias
    shards = entrance/'shards'
    primary = shards/shard_id
    incoming = shards/incoming_shard_id
    if Path(out).resolve() != primary:
        raise ValueError('Merge output directory must be the primary host shard')
    if (not request.strip() or shard_id == incoming_shard_id
            or any(Path(name).name != name or not name for name in
                   (analysis_alias, shard_id, incoming_shard_id))):
        raise ValueError('Require request and distinct, simple shard IDs')
    if not primary.is_dir() or not incoming.is_dir():
        raise ValueError('Both source shard directories must exist')
    marker = entrance/'shard_merge_in_progress.json'
    if marker.exists():
        raise ValueError('A shard merge is already in progress; inspect its marker')
    archive = entrance/'history'/'merged_shards'
    primary_task = read_json(primary/'task.json')
    incoming_task = read_json(incoming/'task.json')
    primary_archive = archive/primary_task['task_id']
    incoming_archive = archive/incoming_task['task_id']
    staging = archive/f"staging_{primary_task['task_id']}_{incoming_task['task_id']}"
    if any(path.exists() for path in (primary_archive, incoming_archive, staging)):
        raise ValueError('Merge archive/staging target already exists')
    if primary_task['status'] not in ('FAILED', 'PAUSED') or incoming_task['status'] != 'PAUSED':
        raise ValueError('Primary must be stopped and incoming shard PAUSED')
    for source in (primary, incoming):
        with (source/'worker.lock').open('r') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError(f'Shard worker still owns directory: {source}') from None
            fcntl.flock(lock, fcntl.LOCK_UN)
    if (primary_task.get('analysis_alias') != analysis_alias
            or incoming_task.get('analysis_alias') != analysis_alias
            or primary_task.get('shard_id') != shard_id
            or incoming_task.get('shard_id') != incoming_shard_id):
        raise ValueError('Source shard identity or alias mismatch')
    base = primary_task['parameters']['experiment']['value']
    other = incoming_task['parameters']['experiment']['value']
    scientific_keys = ('n_sources', 'catalog_seed', 'sample', 'data_selection',
                       'likelihood_mode', 'gamma_mode', 'gamma', 'gamma_min',
                       'gamma_max', 'ns_seed', 'ns_max', 'weight_mode', 'sky',
                       'background_pdf_version', 'randomization', 'hypothesis_family')
    if any(base.get(key) != other.get(key) for key in scientific_keys):
        raise ValueError('Source scientific configurations differ')
    if sha256(primary/'catalog.json') != sha256(incoming/'catalog.json'):
        raise ValueError('Source catalogs differ')
    if sha256(primary/'fits'/'observed.json') != sha256(incoming/'fits'/'observed.json'):
        raise ValueError('Source observed checkpoints differ')
    primary_summary, incoming_summary = report(primary, persist=False), report(incoming, persist=False)
    if (primary_summary['failed_fits'] or incoming_summary['failed_fits']
            or not primary_summary['observed_complete'] or not incoming_summary['observed_complete']):
        raise ValueError('Source fits failed review or observed fit missing')
    if _skipped_negative_ts_rows(incoming, other, {
            incoming_task['request_sha256'], *incoming_task.get('accepted_checkpoint_request_sha256', [])}):
        raise ValueError('Incoming skipped fits require explicit index migration')
    primary_paths = sorted((primary/'fits').glob('trial_*.json'))
    incoming_paths = sorted((incoming/'fits').glob('trial_*.json'))
    primary_indices = [read_json(path)['index'] for path in primary_paths]
    skipped_primary = _skipped_negative_ts_rows(primary, base, {
        primary_task['request_sha256'], *primary_task.get('accepted_checkpoint_request_sha256', [])})
    offset = max([*primary_indices, *(row['index'] for _, row in skipped_primary)], default=-1) + 1
    source_seeds = [row['event_ra_scramble_seed'] for row in
                    (read_json(path) for path in [*primary_paths, *incoming_paths])]
    source_seeds += [row['event_ra_scramble_seed'] for _, row in skipped_primary]
    if len(source_seeds) != len(set(source_seeds)):
        raise ValueError('Duplicate event-RA seed across source shards')
    overrides = {}
    source_checksums = []
    archived_sources = ((primary, primary_archive, primary_task),
                        (incoming, incoming_archive, incoming_task))
    archive.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    try:
        (staging/'fits').mkdir()
        for name in ('catalog.json', 'catalog.csv'):
            shutil.copy2(primary/name, staging/name)
        shutil.copy2(primary/'fits'/'observed.json', staging/'fits'/'observed.json')
        for path in primary_paths:
            shutil.copy2(path, staging/'fits'/path.name)
            source_checksums.append(dict(source_task_id=primary_task['task_id'],
                                         original_path=str(primary_archive/'fits'/path.name),
                                         original_sha256=sha256(path),
                                         merged_path=str(primary/'fits'/path.name)))
        for path, row in skipped_primary:
            target = staging/'skipped_negative_ts'/path.name
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(path, target)
            source_checksums.append(dict(source_task_id=primary_task['task_id'],
                                         original_path=str(primary_archive/path.relative_to(primary)),
                                         original_sha256=sha256(path),
                                         merged_path=str(primary/'skipped_negative_ts'/path.name)))
        for path in incoming_paths:
            row = read_json(path)
            old_index = row['index']
            new_index = offset + old_index
            if (row.get('trial_id') != trial_id_for_index(other, old_index)
                    or row.get('event_ra_scramble_seed') != event_seed_for_index(other, old_index)):
                raise ValueError(f'Incoming checkpoint identity mismatch: {path}')
            new_name = f'trial_{new_index:04d}.json'
            if (staging/'fits'/new_name).exists():
                raise ValueError(f'Merged checkpoint index collision: {new_index}')
            overrides[str(new_index)] = row['event_ra_scramble_seed']
            row['source_checkpoint'] = dict(task_id=incoming_task['task_id'],
                                            trial_id=row['trial_id'], index=old_index,
                                            sha256=sha256(path))
            row['index'] = new_index
            row['trial_id'] = f'{shard_id}:{new_index:06d}'
            row['shard_id'] = shard_id
            write_json(staging/'fits'/new_name, row)
            source_checksums.append(dict(source_task_id=incoming_task['task_id'],
                                         original_path=str(incoming_archive/'fits'/path.name),
                                         original_sha256=sha256(path),
                                         merged_path=str(primary/'fits'/new_name)))
        config = dict(base)
        config.update(workers=other['workers'], event_seed_overrides=overrides,
                      trial_id_scheme='one host-shard local index; imported seed overrides',
                      event_seed_scheme='original shard stream except explicit imported overrides')
        manifest = dict(created_at_utc=utc_now(), analysis_alias=analysis_alias,
                        shard_id=shard_id, primary_task_id=primary_task['task_id'],
                        incoming_task_id=incoming_task['task_id'], index_offset=offset,
                        source_tasks=[dict(task_id=task['task_id'], directory=str(archived),
                                           original_task_sha256=sha256(source/'task.json'))
                                      for source, archived, task in archived_sources],
                        checkpoints=source_checksums,
                        failed_fit_policy='negative-TS checkpoint retained separately, never in fits')
        write_json(staging/'shard_merge_manifest.json', manifest)
        paths = _background_release_paths(root, config['background_pdf_version'])
        data = root/'data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2'
        for folder in ('events', 'uptime', 'irfs'):
            paths.extend((data/folder).glob('*.csv'))
        paths.extend((root/'data_output/signal_energy_pdfs/14yr_dr2').glob('*'))
        paths += [root/'run_agent_wrap.py', Path(__file__),
                  root/'analysis_backend/skyllh_dr2_stacking.py',
                  root/'analysis_backend/event_pdf_data.py',
                  root/'analysis_backend/skyllh_chunked.py',
                  root/'analysis_backend/skyllh_dr2_pdfs.py',
                  root/'agent_core/dr2_pdf_release.py',
                  staging/'catalog.json', staging/'catalog.csv',
                  staging/'fits'/'observed.json', staging/'shard_merge_manifest.json']
        inputs = [dict(path=str(primary/path.relative_to(staging)) if path.is_relative_to(staging)
                       else str(path), sha256=sha256(path))
                  for path in sorted(set(paths)) if path.is_file()]
        task = create_task_record(request, 'empirical_background_calibration_distributed_shard',
                                  'dr2_empirical_scramble_shard',
                                  f'Merged host-owned {shard_id} stream for {analysis_alias}',
                                  {'files': inputs},
                                  {'gamma': parameter(-3., 'user', True),
                                   'experiment': parameter(config, 'user', True)})
        task['analysis_alias'] = analysis_alias
        task['shard_id'] = shard_id
        task['shard_number'] = base['shard_number']
        task['parent_task'] = dict(task_id=primary_task['task_id'],
                                   directory=str(primary_archive),
                                   request_sha256=primary_task['request_sha256'],
                                   amendment_reason='Owner-authorized merge of two host streams')
        task['accepted_checkpoint_request_sha256'] = list(dict.fromkeys([
            primary_task['request_sha256'], incoming_task['request_sha256'],
            *primary_task.get('accepted_checkpoint_request_sha256', []),
            *incoming_task.get('accepted_checkpoint_request_sha256', []),
        ]))
        task['parameter_provenance'] = dict(scientific_configuration='unchanged',
                                             trial_identity='contiguous host-local index namespace',
                                             event_seeds='original streams retained; incoming seeds overridden',
                                             ownership=f'only host {shard_id} may write this directory')
        task['planned_tools'] = [
            'run_agent_wrap.py dr2-empirical-scramble --action launch|status|snapshot|stop|resume'
        ]
        task['request_sha256'] = digest(dict(config=config, inputs=inputs,
                                             parent_request_sha256=primary_task['request_sha256']))
        task['artifacts'] = {'output_directory': str(primary)}
        task['status'] = 'PAUSED'
        task['pause_reason'] = 'Merged stopped host streams; await explicit launch'
        write_json(staging/'task.json', task)
        write_json(staging/'control.json', dict(stop_requested=False, updated_at_utc=utc_now()))
        merged_summary = report(staging, persist=False)
        if (merged_summary['completed_trials'] != primary_summary['completed_trials']
                + incoming_summary['completed_trials']
                or len(merged_summary.get('skipped_negative_ts_fits', [])) != len(skipped_primary)
                or merged_summary['failed_fits']):
            raise ValueError('Staged merge did not preserve source trial counts')
        write_json(marker, dict(status='in_progress', created_at_utc=utc_now(),
                                primary_task_id=primary_task['task_id'],
                                incoming_task_id=incoming_task['task_id']))
        primary.replace(primary_archive)
        incoming.replace(incoming_archive)
        staging.replace(primary)
        central = save_task(task, root)
        task['central_task_path'] = str(central)
        write_json(central, task)
        write_json(primary/'task.json', task)
        for source, archived, old_task in archived_sources:
            shutil.copy2(archived/'task.json', archived/'task_before_merge.json')
            old_task['artifacts']['output_directory'] = str(archived)
            old_task['superseded_by_task_id'] = task['task_id']
            write_json(archived/'task.json', old_task)
            if old_task.get('central_task_path'):
                write_json(old_task['central_task_path'], old_task)
        merged_result = snapshot(primary)
        marker.unlink()
        return merged_result
    except Exception:
        # A marker left after an interrupted move makes Air aggregation fail closed.
        if not marker.exists() and staging.exists():
            shutil.rmtree(staging)
        raise


def _validate_task_inputs(root, out, task):
    config = task['parameters']['experiment']['value']
    if config.get('fit_procedure', 'skyllh_lbfgs_v1') != 'skyllh_lbfgs_v1':
        raise ValueError('Unsupported empirical fit procedure; existing checkpoints are unchanged')
    expected = digest({'config': config, 'inputs': task['inputs']['files'],
                       **({'parent_request_sha256': task['parent_task']['request_sha256']} if 'parent_task' in task else {})})
    if expected != task['request_sha256']:
        raise ValueError('Continuous configuration hash mismatch')
    for item in task['inputs']['files']:
        if sha256(item['path']) != item['sha256']:
            raise ValueError('Input/code changed: '+item['path'])
    verify_background_release(root, config['background_pdf_version'])
    current = report(out)
    if current['failed_fits']:
        raise ValueError('Failed fit needs scientific review; no automatic retry')
    return config


def run_continuous(root, out):
    root, out = Path(root).resolve(), Path(out).resolve()
    with (out/'worker.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('A continuous ensemble worker is already active')
        return _run_continuous_locked(root, out)


def _run_continuous_locked(root, out):
    task = read_json(out/'task.json')
    if task['status'] not in ('READY', 'PAUSED'):
        raise ValueError('Continuous task must be READY or PAUSED')
    config = _validate_task_inputs(root, out, task)
    update_work_progress('continuous background trials', 0, None, 0.)
    for name in THREAD_VARIABLES:
        os.environ[name] = '1'
    control = read_json(out/'control.json')
    control.update(stop_requested=False, updated_at_utc=utc_now())
    write_json(out/'control.json', control)
    task['status'] = 'RUNNING'
    task.pop('pause_reason', None)
    task['attempts'].append(dict(started_at_utc=utc_now(), request_sha256=task['request_sha256'],
                                 pid=os.getpid(), mode='continuous'))

    def persist():
        write_json(out/'task.json', task)
        write_json(task['central_task_path'], task)

    persist()
    try:
        with ProcessPoolExecutor(max_workers=config['workers'], mp_context=multiprocessing.get_context('spawn'),
                                 max_tasks_per_child=1) as pool:
            completed = {row['index'] for row in
                         (read_json(path) for path in (out/'fits').glob('trial_*.json'))}
            completed.update(row['index'] for _, row in _skipped_negative_ts_rows(
                out, config, {task['request_sha256'], *task.get('accepted_checkpoint_request_sha256', [])}))
            in_flight = {}
            stopping = False
            if not (out/'fits'/'observed.json').exists():
                observed_future = pool.submit(
                    fit_one, str(root), str(out), config, task['request_sha256'], -1
                )
                in_flight[observed_future] = -1

            def fill_workers():
                nonlocal stopping
                while not stopping and len(in_flight) < config['workers']:
                    if read_json(out/'control.json').get('stop_requested'):
                        stopping = True
                        break
                    index = next_available_trial_index(completed, in_flight.values(),
                        start_index=_trial_cursor(out) if _discard_negative_ts(config) else 0)
                    future = pool.submit(fit_one, str(root), str(out), config, task['request_sha256'], index)
                    in_flight[future] = index

            fill_workers()
            while in_flight:
                done, _ = wait(in_flight, timeout=1., return_when=FIRST_COMPLETED)
                control = read_json(out/'control.json')
                stopping = stopping or bool(control.get('stop_requested'))
                if not done:
                    continue
                for future in done:
                    index = in_flight.pop(future)
                    row = future.result()
                    if row is None and index >= 0 and _discard_negative_ts(config):
                        completed.add(index)
                        continue
                    if row['index'] != index:
                        raise ValueError('Rolling scheduler trial-index mismatch')
                    if row['review']['status'] == 'fail':
                        if not _is_skippable_negative_ts(row, config):
                            raise ValueError('Fit review failed; inspect per-fit artifacts before continuing')
                        _skip_negative_ts_checkpoint(out, row, config, task['request_sha256'])
                    completed.add(index)
                if _discard_negative_ts(config):
                    _advance_trial_cursor(out, completed)
                # Refill immediately after any completion; the other worker is
                # never held behind a slower fit. A stop request suppresses refill.
                fill_workers()
                current = snapshot(out)
                print(json.dumps(current, sort_keys=True), flush=True)
            task['status'] = 'PAUSED'
            task['pause_reason'] = 'Owner-requested graceful stop after all fits already in flight checkpointed'
        task['attempts'][-1]['ended_at_utc'] = utc_now()
        persist()
    except Exception as exc:
        task['status'] = 'FAILED'
        task['completion'] = dict(error=repr(exc), status='FAILED')
        task['attempts'][-1]['ended_at_utc'] = utc_now()
        persist()
        review = dict(status='fail', error=repr(exc), auto_fix_allowed=False)
        write_json(out/'review.json', review)
        write_json(Path(task['central_task_path']).parent/'agent_review.json', review)
        raise
    return snapshot(out)


def launch_continuous(root, out):
    root, out = Path(root).resolve(), Path(out).resolve()
    task = read_json(out/'task.json')
    if not task['parameters']['experiment']['value'].get('continuous'):
        raise ValueError('Launch is only available for a continuous task')
    if task['status'] not in ('READY', 'PAUSED'):
        raise ValueError('Continuous task must be READY or PAUSED before launch')
    _validate_task_inputs(root, out, task)
    control = read_json(out/'control.json')
    control.update(stop_requested=False, updated_at_utc=utc_now())
    write_json(out/'control.json', control)
    env = os.environ.copy()
    for name in THREAD_VARIABLES:
        env[name] = '1'
    command = [sys.executable, '-u', str(root/'run_agent_wrap.py'), '--repo-root', str(root),
               'dr2-empirical-scramble', '--action', 'run', '--output-directory', str(out)]
    if sys.platform == 'darwin':
        command = ['/usr/bin/caffeinate', '-i', *command]
    log_path = out/'worker_continuous.log'
    with log_path.open('ab', buffering=0) as log:
        process = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    launch = dict(status='LAUNCHED', pid=process.pid, command=command, log_path=str(log_path),
                  created_at_utc=utc_now(), workers=task['parameters']['experiment']['value']['workers'],
                  stop_latency='after all fits already in flight finish; no completed worker waits for another')
    write_json(out/'launch.json', launch)
    return launch


def request_stop(out):
    out = Path(out).resolve()
    control = read_json(out/'control.json')
    control.update(stop_requested=True, requested_at_utc=utc_now(), updated_at_utc=utc_now())
    write_json(out/'control.json', control)
    result = report(out)
    result['stop_behavior'] = 'Graceful: stop refilling workers; fits already in flight finish and checkpoint.'
    return result


def plot_snapshot(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    out = Path(out).resolve()
    summary = report(out)
    task = read_json(out/'task.json')
    config = task['parameters']['experiment']['value']
    rows = [read_json(path) for path in sorted((out/'fits').glob('trial_*.json'))]
    observed = read_json(out/'fits'/'observed.json')['result']['TS']
    values = np.asarray([row['result']['TS'] for row in rows], dtype=float)
    if not len(values):
        raise ValueError('At least one completed background trial is required for plotting')
    figure, axis = plt.subplots(figsize=(7.4, 4.8))
    bins = max(5, min(40, int(np.ceil(np.sqrt(len(values))))))
    axis.hist(values, bins=bins, color='#4472C4', alpha=.8, edgecolor='white', label='Background trials')
    axis.axvline(observed, color='#C00000', linewidth=2.2, label=f'Observed TS = {observed:.4g}')
    stats = summary['statistics']
    cs95 = stats['anytime_valid_confidence_sequences']['0.95']
    z = stats['significance_one_sided']
    z_text = z if isinstance(z, str) else f'{z:.4g}'
    text_value = (f"N={stats['n_trials']}, k={stats['exceedances']}\n"
                  f"p=(k+1)/(N+1)={stats['p_pre']:.4g}\n"
                  f"one-sided Z={z_text}\n"
                  f"95% anytime CS p=[{cs95['p'][0]:.3g}, {cs95['p'][1]:.3g}]")
    axis.text(.98, .96, text_value, transform=axis.transAxes, ha='right', va='top',
              bbox=dict(boxstyle='round', facecolor='white', alpha=.9))
    axis.set_xlabel('TS')
    axis.set_ylabel('Number of background trials')
    label = task.get('analysis_alias', f"DR2 Bpdf {config['background_pdf_version']}")
    axis.set_title(f'{label}: event-RA background calibration ({summary["status"].lower()})')
    axis.legend(loc='upper left')
    figure.tight_layout()
    path = out/'ts_background_snapshot.png'
    temporary = out/f'ts_background_snapshot.{os.getpid()}.tmp.png'
    figure.savefig(temporary, dpi=170)
    pdf_path=out/'ts_background_snapshot.pdf'
    figure.savefig(pdf_path)
    plt.close(figure)
    temporary.replace(path)
    return str(path)


def write_snapshot_exports(out, result):
    out = Path(out).resolve()
    task = read_json(out/'task.json')
    config = task['parameters']['experiment']['value']
    rows = [read_json(path) for path in sorted((out/'fits').glob('*.json'))]
    csv_path = out/'background_trials.csv'
    temporary_csv = csv_path.with_name(csv_path.name + f'.{os.getpid()}.tmp')
    with temporary_csv.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['trial_id', 'index', 'kind', 'event_ra_seed', 'TS', 'ns', 'gamma',
                         'review_status', 'elapsed_seconds', 'completed_at_utc'])
        for row in sorted(rows, key=lambda item: item['index']):
            value = row['result']
            writer.writerow([
                row.get('trial_id', trial_id_for_index(config, row['index'])),
                row['index'], 'observed' if row['index'] < 0 else 'background',
                value['ra_scramble']['event_seed'], value['TS'], value['ns'], value['gamma'],
                row['review']['status'], row['elapsed_seconds'], row['completed_at_utc'],
            ])
    temporary_csv.replace(csv_path)

    md_path = out/'results_snapshot.md'
    lines = [
        f"# {task.get('analysis_alias', task['task_id'])}", '',
        f"- Task: `{task['task_id']}`",
        f"- Status: `{result['status']}`",
        f"- Background PDF: `{config['background_pdf_version']}`",
        f"- Catalog SHA-256: `{sha256(out/'catalog.json')}`",
        f"- Workers: `{config['workers']}`; numerical threads per worker: `{config['numerical_threads_per_worker']}`",
        f"- Completed background trials: `{result['completed_trials']}`",
        f"- Failed fits: `{len(result['failed_fits'])}`",
        f"- Hypothesis: {config.get('hypothesis_family', 'one specified stacking analysis')}", '',
    ]
    if task.get('baseline_analysis', {}).get('primary_warnings'):
        lines += ['Primary-analysis warnings: '+str(task['baseline_analysis']['primary_warnings']), '']
    if _discard_negative_ts(config):
        lines += ['- Background TS < 0 policy: discard without recording the fit.', '']
    elif 'skipped_negative_ts_fits' in result:
        lines += [f"- Skipped negative-TS fits: `{len(result['skipped_negative_ts_fits'])}`", '']
    if 'statistics' in result:
        observed, stats = result['observed'], result['statistics']
        lines += [
            '## Result', '',
            f"- Observed TS: `{observed['TS']:.12g}`",
            f"- Observed ns: `{observed['ns']:.12g}`",
            f"- Observed s_nu: `{observed['gamma']}`",
            f"- Exceedances: `{stats['exceedances']}` of `{stats['n_trials']}`",
            f"- Empirical pre-trial p-value: `{stats['p_pre']:.12g}`",
            f"- Empirical post-trial p-value: `{stats['p_post']:.12g}`",
            f"- One-sided significance: `{stats['significance_one_sided']}` sigma", '',
            '## Monte Carlo intervals', '',
            '| Coverage | Type | p interval | one-sided Z interval |',
            '|---:|---|---|---|',
        ]
        for confidence in ('0.68', '0.95'):
            for key, name in (('anytime_valid_confidence_sequences', 'anytime-valid'),
                              ('fixed_n_mc_intervals', 'fixed-N Clopper-Pearson')):
                interval = stats[key][confidence]
                lines.append(
                    f"| {float(confidence):.0%} | {name} | "
                    f"`[{interval['p'][0]:.12g}, {interval['p'][1]:.12g}]` | "
                    f"`[{interval['z'][0]}, {interval['z'][1]}]` |"
                )
        lines += ['', ('Anytime-valid intervals are primary under repeated inspection or optional stopping. '
                       'These intervals quantify Monte Carlo uncertainty, not PDF systematics.'), '']
    if result.get('statistics_caution'):
        lines += ['', result['statistics_caution'], '']
    if result.get('skipped_negative_ts_fits'):
        lines += ['## Skipped negative-TS fits', '']
        lines += [f"- `{item['trial_id']}`: TS=`{item['TS']:.12g}`, "
                  f"event-RA seed=`{item['event_ra_seed']}`, checkpoint=`{item['checkpoint']}`"
                  for item in result['skipped_negative_ts_fits']]
    temporary_md = md_path.with_name(md_path.name + f'.{os.getpid()}.tmp')
    temporary_md.write_text('\n'.join(lines))
    temporary_md.replace(md_path)
    return {'markdown': str(md_path), 'trials_csv': str(csv_path)}


def snapshot(out):
    result = report(out)
    if result.get('observed_complete') and result.get('completed_trials', 0):
        result['plot'] = plot_snapshot(out)
        result['plot_pdf'] = str(Path(out).resolve()/'ts_background_snapshot.pdf')
    if (Path(out)/'launch.json').exists():
        result['launch'] = read_json(Path(out)/'launch.json')
    result['exports'] = write_snapshot_exports(out, result)
    write_json(Path(out)/'snapshot.json', result)
    return result


def _aggregate_trial_row(row, config, source, trial_id):
    expected = event_seed_for_index(config, row['index'])
    actual = row['result']['ra_scramble']['event_seed']
    if actual != expected:
        raise ValueError(f'Checkpoint event seed mismatch for {trial_id}')
    if row['review'] != fit_review(row['result'], config):
        raise ValueError(f'Checkpoint review mismatch for {trial_id}')
    if row['review']['status'] == 'fail':
        raise ValueError(f'Failed fit cannot enter aggregate: {trial_id}')
    return {
        'trial_id': trial_id,
        'source': source,
        'index': row['index'],
        'event_ra_seed': actual,
        'TS': row['result']['TS'],
        'ns': row['result']['ns'],
        'gamma': row['result']['gamma'],
        'review_status': row['review']['status'],
        'review_warnings': row['review']['warnings'],
        'elapsed_seconds': row['elapsed_seconds'],
        'completed_at_utc': row['completed_at_utc'],
        'checkpoint_request_sha256': row['request_sha256'],
    }


def aggregate_distributed_shards(root, analysis_alias, out):
    """Aggregate immutable canonical and host-shard checkpoints on the Air owner."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    root, out = Path(root).resolve(), Path(out).resolve()
    if not analysis_alias or Path(analysis_alias).name != analysis_alias:
        raise ValueError('Require one valid analysis alias')
    registry_path = root/'data_output/diagnostics/background_trial_aliases.json'
    registry = read_json(registry_path)
    if analysis_alias not in registry.get('aliases', {}):
        raise ValueError(f'Unknown empirical-scrambling alias: {analysis_alias}')
    record = registry['aliases'][analysis_alias]
    canonical = Path(record['output_directory']).resolve()
    entrance = root/'data_output/diagnostics'/analysis_alias
    if (entrance/'shard_merge_in_progress.json').exists():
        raise ValueError('Shard merge in progress; aggregate after synchronization')
    if (entrance/'current').resolve() != canonical:
        raise ValueError('Alias current symlink and registry output directory disagree')
    canonical_task = read_json(canonical/'task.json')
    canonical_config = canonical_task['parameters']['experiment']['value']
    canonical_catalog_hash = sha256(canonical/'catalog.json')
    if canonical_catalog_hash != record['catalog_sha256']:
        raise ValueError('Canonical catalog hash and alias registry disagree')
    canonical_summary = report(canonical, persist=False)
    if canonical_summary['failed_fits'] or not canonical_summary['observed_complete']:
        raise ValueError('Canonical task is not a valid aggregate reference')
    observed_row = read_json(canonical/'fits'/'observed.json')
    observed = observed_row['result']
    scientific_keys = (
        'n_sources', 'catalog_seed', 'sample', 'data_selection', 'likelihood_mode',
        'gamma_mode', 'gamma', 'gamma_min', 'gamma_max', 'ns_seed', 'ns_max',
        'weight_mode', 'sky', 'background_pdf_version', 'randomization',
        'hypothesis_family',
    )

    combined = {}
    event_seeds = {}
    skipped_unavailable = []
    skipped_negative_ts = []
    unrecorded_attempts = _discard_negative_ts(canonical_config)
    source_tasks = [{
        'source': 'canonical', 'task_id': canonical_task['task_id'],
        'status': canonical_task['status'], 'directory': str(canonical),
    }]
    for path in sorted((canonical/'fits').glob('trial_*.json')):
        row = read_json(path)
        trial_id = row.get('trial_id', f"legacy:{row['index']:06d}")
        item = _aggregate_trial_row(row, canonical_config, 'canonical', trial_id)
        combined[trial_id] = item
        if item['event_ra_seed'] in event_seeds:
            raise ValueError(f"Duplicate event seed in aggregate: {item['event_ra_seed']}")
        event_seeds[item['event_ra_seed']] = trial_id

    skipped_negative_ts.extend(dict(source='canonical', **item)
                               for item in canonical_summary.get('skipped_negative_ts_fits', []))

    shard_tasks = sorted((entrance/'shards').glob('*/task.json')) if (entrance/'shards').exists() else []
    for task_path in shard_tasks:
        shard_dir = task_path.parent
        task = read_json(task_path)
        config = task['parameters']['experiment']['value']
        unrecorded_attempts = unrecorded_attempts or _discard_negative_ts(config)
        if not config.get('distributed_shard'):
            raise ValueError(f'Non-shard task found below shards/: {shard_dir}')
        if task.get('analysis_alias') != analysis_alias:
            raise ValueError(f'Shard alias mismatch: {shard_dir}')
        if sha256(shard_dir/'catalog.json') != canonical_catalog_hash:
            raise ValueError(f'Shard catalog mismatch: {shard_dir}')
        for key in scientific_keys:
            if config.get(key) != canonical_config.get(key):
                raise ValueError(f'Shard scientific configuration mismatch for {key}: {shard_dir}')
        shard_observed = read_json(shard_dir/'fits'/'observed.json')['result']
        for key in ('TS', 'ns', 'gamma'):
            if shard_observed[key] != observed[key]:
                raise ValueError(f'Shard observed-fit mismatch for {key}: {shard_dir}')
        trial_paths = sorted((shard_dir/'fits').glob('trial_*.json'))
        source_task = {
            'source': config['shard_id'], 'shard_number': config['shard_number'],
            'task_id': task['task_id'], 'status': task['status'], 'directory': str(shard_dir),
            'completed_trials': len(trial_paths),
        }
        accepted_hashes = {task['request_sha256'], *task.get('accepted_checkpoint_request_sha256', [])}
        skipped_rows = _skipped_negative_ts_rows(shard_dir, config, accepted_hashes)
        source_task['skipped_negative_ts_fits'] = len(skipped_rows)
        skipped_negative_ts.extend(dict(source=config['shard_id'], index=row['index'],
                                        trial_id=row['trial_id'], event_ra_seed=row['event_ra_scramble_seed'],
                                        TS=row['result']['TS'], checkpoint=str(path),
                                        checkpoint_sha256=sha256(path)) for path, row in skipped_rows)
        source_tasks.append(source_task)
        source_skipped = []
        for path in trial_paths:
            row, unavailable_reason = read_available_shard_checkpoint(path)
            if row is None:
                skipped = {
                    'source': config['shard_id'], 'path': str(path),
                    'filename': path.name, 'reason': unavailable_reason,
                }
                skipped_unavailable.append(skipped)
                source_skipped.append(path.name)
                continue
            trial_id = row.get('trial_id')
            expected_id = trial_id_for_index(config, row['index'])
            if trial_id != expected_id:
                raise ValueError(f'Shard trial id mismatch: {path}')
            if trial_id in combined:
                raise ValueError(f'Duplicate trial id in aggregate: {trial_id}')
            item = _aggregate_trial_row(row, config, config['shard_id'], trial_id)
            if item['event_ra_seed'] in event_seeds:
                raise ValueError(f"Duplicate event seed in aggregate: {item['event_ra_seed']}")
            combined[trial_id] = item
            event_seeds[item['event_ra_seed']] = trial_id
        source_task['included_trials'] = source_task['completed_trials'] - len(source_skipped)
        source_task['skipped_unavailable_checkpoints'] = source_skipped

    values = list(combined.values())
    values.sort(key=lambda item: (item['source'], item['index']))
    if len({item['trial_id'] for item in skipped_negative_ts}) != len(skipped_negative_ts):
        raise ValueError('Duplicate skipped trial id in aggregate')
    if len({item['event_ra_seed'] for item in skipped_negative_ts}) != len(skipped_negative_ts):
        raise ValueError('Duplicate skipped event seed in aggregate')
    if any(item['trial_id'] in combined or item['event_ra_seed'] in event_seeds
           for item in skipped_negative_ts):
        raise ValueError('Skipped trial duplicates a valid aggregate trial')
    statistics = empirical_summary(observed['TS'], [item['TS'] for item in values])
    result = {
        'analysis_alias': analysis_alias,
        'background_pdf_version': canonical_config['background_pdf_version'],
        'catalog_sha256': canonical_catalog_hash,
        'created_at_utc': utc_now(),
        'status': 'RUNNING' if any(item['status'] == 'RUNNING' for item in source_tasks) else 'PAUSED',
        'observed': {key: observed[key] for key in ('TS', 'ns', 'gamma')},
        'statistics': statistics,
        'completed_trials': len(values),
        'attempted_trials': len(values)+len(skipped_negative_ts),
        'skipped_negative_ts_fits': skipped_negative_ts,
        'boundary_warning_fits': [item['trial_id'] for item in values if item['review_warnings']],
        'failed_fits': [],
        'skipped_unavailable_checkpoints': skipped_unavailable,
        'source_tasks': source_tasks,
        'trial_id_scheme': 'legacy global indices plus host-owned shard_id:local_index identities',
        'snapshot_note': ('Unique completed checkpoints are combined after catalog, scientific-configuration, '
                          'trial-id and event-seed validation. Anytime-valid intervals are primary under '
                          'repeated monitoring.'),
    }
    if skipped_negative_ts:
        result['statistics_caution'] = ('Negative-TS fits were excluded. The empirical statistics use only '
                                        'valid fits; skipped-fit selection may bias the null distribution.')
    if unrecorded_attempts:
        result.pop('attempted_trials')
        result['negative_ts_policy'] = 'New-policy tasks discard negative TS without recording the fit.'
    out.mkdir(parents=True, exist_ok=True)
    write_json(out/'aggregate_snapshot.json', result)
    csv_path = out/'aggregate_trials.csv'
    temporary_csv = csv_path.with_name(csv_path.name + f'.{os.getpid()}.tmp')
    with temporary_csv.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            'trial_id', 'source', 'index', 'event_ra_seed', 'TS', 'ns', 'gamma',
            'review_status', 'elapsed_seconds', 'completed_at_utc', 'checkpoint_request_sha256',
        ])
        writer.writeheader()
        for item in values:
            writer.writerow({key: item[key] for key in writer.fieldnames})
    temporary_csv.replace(csv_path)
    md_path = out/'aggregate_results.md'
    cs95 = statistics['anytime_valid_confidence_sequences']['0.95']
    lines = [
        f'# {analysis_alias}: distributed aggregate', '',
        f"- Status: `{result['status']}`",
        f"- Background PDF: `{result['background_pdf_version']}`",
        f"- Completed unique background trials: `{statistics['n_trials']}`",
        f"- Historical preserved negative-TS fits: `{len(skipped_negative_ts)}`",
        f"- Exceedances: `{statistics['exceedances']}`",
        f"- Empirical pre/post-trial p-value: `{statistics['p_pre']:.12g}`",
        f"- One-sided significance: `{statistics['significance_one_sided']}` sigma",
        f"- 95% anytime-valid p interval: `[{cs95['p'][0]:.12g}, {cs95['p'][1]:.12g}]`",
        f"- Boundary-warning fits: `{len(result['boundary_warning_fits'])}`",
        f"- Failed fits: `0`", '',
        f"- Locally unavailable shard checkpoints skipped: `{len(skipped_unavailable)}`", '',
        '## Sources', '',
        '| Source | Task | Status | Included trials | Locally unavailable |',
        '|---|---|---|---:|---:|',
    ]
    for item in source_tasks:
        included = item.get('included_trials', item.get('completed_trials', canonical_summary['completed_trials']))
        unavailable = len(item.get('skipped_unavailable_checkpoints', []))
        lines.append(f"| {item['source']} | `{item['task_id']}` | {item['status']} | {included} | {unavailable} |")
    if skipped_unavailable:
        lines.extend(['', '## Locally unavailable shard checkpoints', '',
                      'These Dropbox placeholders were not downloaded on the Air owner and were excluded from this snapshot.', ''])
        lines.extend(f"- `{item['source']}/{item['filename']}`: {item['reason']}"
                     for item in skipped_unavailable)
    if skipped_negative_ts:
        lines.extend(['', '## Skipped negative-TS fits', '', result['statistics_caution'], ''])
        lines.extend(f"- `{item['trial_id']}`: TS=`{item['TS']:.12g}`, "
                     f"event-RA seed=`{item['event_ra_seed']}`, checkpoint=`{item['checkpoint']}`"
                     for item in skipped_negative_ts)
    temporary_md = md_path.with_name(md_path.name + f'.{os.getpid()}.tmp')
    temporary_md.write_text('\n'.join(lines) + '\n')
    temporary_md.replace(md_path)

    array = np.asarray([item['TS'] for item in values], dtype=float)
    figure, axis = plt.subplots(figsize=(7.4, 4.8))
    bins = max(5, min(40, int(np.ceil(np.sqrt(len(array))))))
    axis.hist(array, bins=bins, color='#4472C4', alpha=.82, edgecolor='white')
    axis.axvline(observed['TS'], color='#C00000', linewidth=2.2,
                label=f"Observed TS = {observed['TS']:.4g}")
    axis.set_xlabel('TS')
    axis.set_ylabel('Number of background trials')
    axis.set_title(f'{analysis_alias}: distributed event-RA aggregate')
    axis.legend(loc='upper left')
    significance = statistics['significance_one_sided']
    significance_text = (significance if isinstance(significance, str)
                         else f'{significance:.4g}')
    axis.text(.98, .96,
              f"N={statistics['n_trials']}, k={statistics['exceedances']}\n"
              f"p={statistics['p_pre']:.4g}\n"
              f"one-sided Z={significance_text}",
              transform=axis.transAxes, ha='right', va='top',
              bbox=dict(boxstyle='round', facecolor='white', alpha=.9))
    figure.tight_layout()
    plot_path = out/'aggregate_ts_background.png'
    temporary_plot = out/f'aggregate_ts_background.{os.getpid()}.tmp.png'
    figure.savefig(temporary_plot, dpi=170)
    plt.close(figure)
    temporary_plot.replace(plot_path)
    result['artifacts'] = {
        'snapshot': str(out/'aggregate_snapshot.json'),
        'trials_csv': str(csv_path), 'markdown': str(md_path), 'plot': str(plot_path),
    }
    write_json(out/'aggregate_snapshot.json', result)
    return result
