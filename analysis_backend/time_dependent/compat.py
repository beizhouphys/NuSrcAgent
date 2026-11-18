"""Transient-only SkyLLH v26 safeguards; never patch global SkyLLH classes."""
import numpy as np
from skyllh.core.flux_model import GaussianTimeFluxProfile as NativeGaussianTimeFluxProfile
from skyllh.core.signalpdf import SignalTimePDF as NativeSignalTimePDF


class GaussianTimeFluxProfile(NativeGaussianTimeFluxProfile):
    """Local v26 Gaussian profile with validated, mutable fixed sigma support."""

    def __init__(self, t0, sigma_t, tol=1e-12, **kwargs):
        if not 0.0 < tol < 1.0:
            raise ValueError("Gaussian tail tolerance must lie strictly between zero and one")
        if sigma_t <= 0.0:
            raise ValueError("Gaussian sigma_t must be positive")
        self._tol = float(tol)
        super().__init__(t0=t0, sigma_t=sigma_t, tol=tol, **kwargs)

    @NativeGaussianTimeFluxProfile.sigma_t.setter
    def sigma_t(self, sigma):
        sigma = float(sigma)
        if sigma <= 0.0:
            raise ValueError("Gaussian sigma_t must be positive")
        self._sigma_t = sigma
        if hasattr(self, "_t_start"):
            center = self.t0
            half_support = np.sqrt(-2.0 * sigma**2 * np.log(self._tol))
            self._t_start = center - half_support
            self._t_stop = center + half_support


class SignalTimePDF(NativeSignalTimePDF):
    """Return zero density for sources with no uptime overlap in a phase."""

    def _calculate_sum_of_ontime_time_flux_profile_integrals(self):
        intervals = self._livetime.uptime_mjd_intervals_arr
        start = np.maximum(intervals[:, 0], self._time_flux_profile.t_start)
        stop = np.minimum(intervals[:, 1], self._time_flux_profile.t_stop)
        keep = stop > start
        if not np.any(keep):
            return 0.0
        return np.sum(self._time_flux_profile.get_integral(start[keep], stop[keep]))

    def _calculate_pd(self, tdm, params_recarray, tl=None):
        src_idxs, evt_idxs = tdm.src_evt_idxs
        pd = np.zeros(len(evt_idxs), dtype=np.float64)
        events_time = tdm.get_data('time')
        for src_idx, row in enumerate(params_recarray):
            params = dict(zip(params_recarray.dtype.names, row, strict=True))
            if self._time_flux_profile.set_params(params):
                self._S = self._calculate_sum_of_ontime_time_flux_profile_integrals()
            mask = src_idxs == src_idx
            times = events_time[evt_idxs[mask]]
            on = self._livetime.is_on(times)
            values = np.zeros(len(times), dtype=np.float64)
            if self._S > 0:
                values[on] = self._time_flux_profile(t=times[on]) / self._S
            pd[mask] = values
        return pd
