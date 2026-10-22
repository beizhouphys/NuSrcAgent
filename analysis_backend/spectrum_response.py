"""On-demand signal-energy response using the existing SkyLLH calculation.

This is runtime preparation for a requested spectrum. Frozen background and
conventional signal-energy products are never regenerated or overwritten.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from skyllh.core.flux_model import PowerLawEnergyFluxProfile, SteadyPointlikeFFM
from skyllh.core.parameters import Parameter, ParameterGrid
from skyllh.analyses.i3.publicdata_ps.signalpdf import PDSignalEnergyPDFSet
from skyllh.analyses.i3.publicdata_ps.smearing_matrix import PDSmearingMatrix
from skyllh.analyses.i3.publicdata_ps.aeff import PDAeff, load_effective_area_array
from agent_core.file_cache import sha256_file
from agent_core.progress import update_work_progress

RESPONSE_VERSION = 'requested_spectrum_v1'
ENERGY_STEP = 0.0025


class TabulatedSpectrumProfile(PowerLawEnergyFluxProfile):
    """Fixed piecewise spectrum; gamma is a passive fixed SkyLLH coordinate.

    Positive adjacent nodes use log-log power-law interpolation. A segment
    touching zero uses a linear function of energy. Integrals use the exact
    same segments, including the explicitly chosen outside-support rule.
    """
    def __init__(self, spectrum, cfg):
        super().__init__(E0=1e3, gamma=0., cfg=cfg)
        self.spectrum = spectrum
        self.energies = np.asarray(spectrum['energy_gev'], dtype=float)
        self.values = np.asarray(spectrum['shape'], dtype=float)

    @property
    def math_function_str(self):
        return 'fixed tabulated dN/dE shape'

    def _segment(self, index):
        x0, x1 = self.energies[index:index+2]
        y0, y1 = self.values[index:index+2]
        if y0 > 0 and y1 > 0:
            exponent = np.log(y1/y0) / np.log(x1/x0)
            return x0, y0, exponent, None
        return x0, y0, None, (y1-y0)/(x1-x0)

    def __call__(self, E, unit=None):
        energy = np.asarray(E, dtype=float)
        if unit is not None:
            energy = energy * unit.to(self.energy_unit)
        result = np.zeros_like(energy)
        indices = np.clip(np.searchsorted(self.energies, energy, side='right')-1, 0, len(self.energies)-2)
        valid = energy > 0
        if self.spectrum['outside_support'] == 'zero':
            valid &= (energy >= self.energies[0]) & (energy <= self.energies[-1])
        for index in np.unique(indices[valid]):
            mask = valid & (indices == index)
            x0, y0, exponent, slope = self._segment(index)
            result[mask] = y0*(energy[mask]/x0)**exponent if slope is None else y0+slope*(energy[mask]-x0)
        return result

    def get_integral(self, E1, E2, unit=None):
        lower, upper = np.broadcast_arrays(np.atleast_1d(E1).astype(float), np.atleast_1d(E2).astype(float))
        if unit is not None:
            lower, upper = lower*unit.to(self.energy_unit), upper*unit.to(self.energy_unit)
        result = np.zeros(lower.shape)
        for position in np.ndindex(lower.shape):
            lo, hi = lower[position], upper[position]
            if self.spectrum['outside_support'] == 'zero':
                lo, hi = max(lo, self.energies[0]), min(hi, self.energies[-1])
            if lo <= 0 or hi <= lo:
                continue
            edges = np.concatenate(([lo], self.energies[(self.energies > lo) & (self.energies < hi)], [hi]))
            total = 0.
            for a, b in zip(edges[:-1], edges[1:]):
                index = int(np.clip(np.searchsorted(self.energies, (a+b)/2)-1, 0, len(self.energies)-2))
                x0, y0, exponent, slope = self._segment(index)
                if slope is not None:
                    total += (b-a)*(y0+slope*((a+b)/2-x0))
                elif abs(exponent+1) < 1e-10:
                    total += y0*x0*np.log(b/a)
                else:
                    # expm1 retains precision for nearly logarithmic segments.
                    total += y0*(a/x0)**exponent*a*np.expm1((exponent+1)*np.log(b/a))/(exponent+1)
            result[position] = total
        return result


def energy_profile(cfg, gamma, spectrum=None):
    return TabulatedSpectrumProfile(spectrum, cfg) if spectrum else PowerLawEnergyFluxProfile(E0=1e3, gamma=float(gamma), cfg=cfg)


def interpolation_grid(gamma, gamma_mode='fixed', gamma_min=1., gamma_max=6.):
    parameter = (Parameter('gamma', initial=float(gamma), valmin=float(gamma_min), valmax=float(gamma_max))
                 if gamma_mode == 'fitted' else Parameter('gamma', initial=float(gamma)))
    grid = parameter.as_linear_grid(delta=0.1)
    grid.add_extra_lower_and_upper_bin()
    return grid


def _artifact_sha256(path):
    # Generated response files are small, immutable snapshots. Hash their
    # actual bytes on each check: Dropbox may change inode metadata while
    # the new file is being indexed, without changing any numerical bytes.
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _atomic_json(path, value):
    temporary = path.with_suffix('.json.pending')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def _atomic_npz(path, **arrays):
    temporary = path.with_suffix('.npz.pending')
    with temporary.open('wb') as handle:
        np.savez_compressed(handle, **arrays)
    temporary.replace(path)


def prepare_response(root, datasets, cfg, gamma, gamma_mode='fixed', gamma_min=1., gamma_max=6.,
                     spectrum=None, likelihood_mode='spatial_energy', estimate_only=False):
    """Prepare all native Dec intervals once, with a current-invocation pilot.

    Cache identity includes spectrum bytes/interpretation, interpolation grid,
    detector IRF hashes and the numerical implementation. Fit/trial settings
    remain outside this immutable response cache; background is independent.
    """
    root = Path(root).resolve()
    grid = interpolation_grid(gamma, gamma_mode, gamma_min, gamma_max)
    inputs = {}
    for dataset in datasets:
        for key in ('eff_area_datafile', 'smearing_datafile'):
            if key == 'smearing_datafile' and likelihood_mode == 'spatial_only':
                continue
            for name in dataset.get_abs_pathfilename_list(dataset.get_aux_data_definition(key)):
                inputs[str(Path(name).resolve())] = sha256_file(name)
    identity = dict(version=RESPONSE_VERSION, spectrum=spectrum or dict(kind='power_law'),
        gamma_grid=grid.grid.tolist(), likelihood_mode=likelihood_mode, energy_step=ENERGY_STEP,
        irf_sha256=inputs, implementation_sha256=sha256_file(__file__))
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    output = root/'data_output/spectrum_responses'/digest
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output/'response.json'
    with (output/'writer.lock').open('a') as lock:
        # A lock is local to this host; host-specific cache roots are required
        # when preparing concurrently on computers linked through Dropbox.
        fcntl.flock(lock, fcntl.LOCK_EX)
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            verify_response(manifest_path, identity)
            return dict(manifest=str(manifest_path), cached=True, remaining_seconds=0., status='READY')
        records = []
        flux = SteadyPointlikeFFM(Phi0=1., energy_profile=energy_profile(cfg, gamma, spectrum), cfg=cfg)
        last_remaining = None
        for dataset_number, dataset in enumerate(datasets):
            stem = dataset.name.replace('/', '_')
            table_path = output/f'{stem}_response.npz'
            # Detector-acceptance integrals use the same profile and public
            # effective-area block as PDSingleParamFlux...DetSigYieldBuilder.
            aeff_names = dataset.get_abs_pathfilename_list(dataset.get_aux_data_definition('eff_area_datafile'))
            aeff, sin_lo, sin_hi, log_lo, log_hi = load_effective_area_array(aeff_names)
            acceptance_started = perf_counter()
            acceptance = []
            for value in grid.grid:
                profile = energy_profile(cfg, value, spectrum)
                acceptance.append(np.sum(aeff*profile.get_integral(10.**log_lo, 10.**log_hi), axis=1))
            acceptance = np.asarray(acceptance).T
            if not np.all(np.isfinite(acceptance)) or np.any(acceptance < 0) or not np.any(acceptance > 0):
                raise ValueError('Invalid detector acceptance for the requested spectrum')
            if likelihood_mode == 'spatial_only':
                _atomic_npz(table_path, gamma=grid.grid, acceptance_per_second=acceptance, sin_dec_lower=sin_lo, sin_dec_upper=sin_hi)
                records.append(dict(dataset=dataset.name, file=str(table_path), sha256=_artifact_sha256(table_path)))
                update_work_progress('requested-spectrum detector acceptance', dataset_number+1, len(datasets), perf_counter()-acceptance_started)
                continue
            sm = PDSmearingMatrix(pathfilenames=dataset.get_abs_pathfilename_list(dataset.get_aux_data_definition('smearing_datafile')))
            aeff_obj = PDAeff(pathfilenames=aeff_names)
            dec_edges = np.unique(np.concatenate((aeff_obj.decnu_binedges, sm.true_dec_bin_edges)))
            centers = (dec_edges[:-1]+dec_edges[1:])/2
            energy_binning = dataset.get_binning_definition('log_energy')
            energy = energy_binning.lower_edge+(np.arange(int(round((energy_binning.upper_edge-energy_binning.lower_edge)/ENERGY_STEP)))+.5)*ENERGY_STEP
            values = np.empty((len(centers), len(energy), len(grid.grid)), dtype=np.float32)
            elapsed, computed = 0., 0
            for index, dec in enumerate(centers):
                # Per-interval checkpoints retain the estimate-only pilot and
                # make interrupted preparation recoverable without overwrites.
                partial = output/f'{stem}_dec_{index:03d}.npz'
                checksum = partial.with_suffix('.sha256.json')
                if partial.exists():
                    if not checksum.exists() or _artifact_sha256(partial) != json.loads(checksum.read_text())['sha256']:
                        raise ValueError('Incomplete spectrum-response checkpoint changed; do not use it')
                    with np.load(partial, allow_pickle=False) as saved:
                        values[index] = saved['values']
                else:
                    started = perf_counter()
                    # Copied from the validated pre-calculation path. For a
                    # fixed non-PL shape, all passive Gamma nodes are identical.
                    construction_grid = (ParameterGrid('gamma', grid=np.asarray([0.]), delta=.1, decimals=1)
                                         if spectrum else grid)
                    pdf_set = PDSignalEnergyPDFSet(cfg=cfg, ds=dataset, src_dec=float(dec),
                        fluxmodel=flux, param_grid_set=construction_grid, ncpu=1, sm=sm)
                    for gamma_index, value in enumerate(grid.grid):
                        pdf = pdf_set.get_pdf({'gamma': 0. if spectrum else float(value)})
                        dense = pdf.get_pd_by_log10_reco_e(energy)
                        if not np.all(np.isfinite(dense)) or np.any(dense < 0) or abs(np.sum(dense)*ENERGY_STEP-1) > .005:
                            raise ValueError('Requested-spectrum SEpdf failed normalization/nonnegativity checks')
                        middle = (energy[:-1]+energy[1:])/2
                        direct = pdf.get_pd_by_log10_reco_e(middle)
                        interpolated = np.interp(middle, energy, dense)
                        if np.sum(np.abs(interpolated-direct))*ENERGY_STEP > .001:
                            raise ValueError('Requested-spectrum SEpdf failed direct interpolation validation')
                        values[index, :, gamma_index] = dense
                    elapsed += perf_counter()-started
                    computed += 1
                    _atomic_npz(partial, values=values[index])
                    _atomic_json(checksum, dict(sha256=_artifact_sha256(partial)))
                    # Only same-dataset work in this invocation sets its ETA.
                    remaining = len(centers)-index-1
                    last_remaining = elapsed/computed*remaining
                    update_work_progress(f'{dataset.name} requested-spectrum SEpdfs', computed, computed+remaining, elapsed)
                    if estimate_only:
                        return dict(status='PREPARATION_REQUIRED', output_directory=str(output),
                            current_dataset=dataset.name, remaining_seconds=last_remaining,
                            estimate_scope='current_dataset_preparation_only', completed_units=computed,
                            remaining_datasets=len(datasets)-dataset_number-1,
                            message='Current measured pilot; later datasets, loading, saving and LLH fitting are not included.')
            if (not np.all(np.isfinite(values)) or np.any(values < 0)
                    or np.max(np.abs(np.sum(values,axis=1,dtype=np.float64)*ENERGY_STEP-1)) > .005):
                raise ValueError('Prepared or restored SEpdfs failed normalization/nonnegativity checks')
            _atomic_npz(table_path, dec_edges=dec_edges, energy=energy, gamma=grid.grid, values=values,
                        acceptance_per_second=acceptance, sin_dec_lower=sin_lo, sin_dec_upper=sin_hi)
            records.append(dict(dataset=dataset.name, file=str(table_path), sha256=_artifact_sha256(table_path),
                                validation=dict(finite_nonnegative_normalized=True, direct_interpolation_l1_tolerance=.001)))
        manifest = dict(status='READY', identity=identity, datasets=records,
                        method='SkyLLH PDSignalEnergyPDFSet and public effective-area convolution; fixed shape or recorded PL grid')
        _atomic_json(manifest_path, manifest)
        return dict(status='READY', manifest=str(manifest_path), cached=False, remaining_seconds=0.)


def verify_response(path, identity=None):
    manifest = json.loads(Path(path).read_text())
    if manifest.get('status') != 'READY' or (identity is not None and manifest['identity'] != identity):
        raise ValueError('Requested-spectrum response identity mismatch')
    for name, digest in manifest['identity']['irf_sha256'].items():
        if sha256_file(name) != digest:
            raise ValueError('Detector response changed since spectrum preparation')
    spectrum = manifest['identity']['spectrum']
    if spectrum.get('file') and sha256_file(spectrum['file']) != spectrum['sha256']:
        raise ValueError('Supplied spectrum changed since response preparation')
    for record in manifest['datasets']:
        if _artifact_sha256(record['file']) != record['sha256']:
            raise ValueError('Requested-spectrum response artifact hash mismatch')
    return manifest
