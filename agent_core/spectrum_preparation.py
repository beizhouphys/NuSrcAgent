"""Prepare the spectrum of a READY task without executing an observed fit."""
from pathlib import Path
from agent_core.agent_orchestrator import build_analysis_payload
from agent_core.config_io import load_config_file
from agent_core.schemas import AnalysisConfig
from agent_core.spectrum import response_required
from agent_core.validate import validate_config


def prepare_task_spectrum(task, repo_root, estimate_only=False):
    if task['status'] != 'READY':
        raise ValueError('Spectrum preparation requires a READY task')
    root = Path(repo_root).resolve()
    payload = build_analysis_payload(task, root)
    config = AnalysisConfig.from_dict(payload)
    validation = validate_config(config, root)
    if not validation.ok:
        raise ValueError('; '.join(validation.errors))
    gamma = config.stacking.spectral_indices[0]
    spectrum, bounds = config.analysis.spectrum, config.analysis.gamma_bounds
    if not response_required(gamma, spectrum, bounds):
        return dict(status='READY', cached=True, remaining_seconds=0., message='Use the existing conventional SEpdfs')
    from agent_core.environment import check_environment
    if check_environment(root, config.data.sample, config.analysis.likelihood_mode)['status'] == 'fail':
        raise ValueError('Spectrum preparation environment check failed')
    if config.data.sample != 'icecube_public_ps_14yr_dr2':
        # DR1 is spatial-only: its acceptance is evaluated directly by its
        # original response integration, with no SEpdf construction required.
        return dict(status='READY', remaining_seconds=None, message='DR1 spatial-only: detector acceptance is calculated during setup; no energy PDFs enter the fit')
    from skyllh.core.config import Config
    from analysis_backend.skyllh_dr2_stacking import _dr2_datasets
    from analysis_backend.spectrum_response import prepare_response
    cfg = Config()
    options = dict(gamma=0. if spectrum else -gamma, gamma_mode=config.stacking.gamma_mode,
                   spectrum=spectrum, likelihood_mode=config.analysis.likelihood_mode, estimate_only=estimate_only)
    if bounds:
        options.update(gamma_min=-bounds[1], gamma_max=-bounds[0])
    return prepare_response(root, _dr2_datasets(root, cfg, 'full14'), cfg, **options)
