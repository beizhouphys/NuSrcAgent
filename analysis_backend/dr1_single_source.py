#!/usr/bin/python
from __future__ import annotations

# Copied from likelihood_v4.py with minimal edits for a callable single-source backend.

import math
import builtins
from pathlib import Path
from typing import Any

from numpy import *
from numpy import trapezoid # NumPy 2 replacement for removed trapz alias


d2r = 180./pi
ROI = 20./d2r
DEFAULT_GAMMA = -2.53
_CACHE: dict[tuple[str, float], dict[str, Any]] = {}


def run_single_source_time_integrated(ra_deg, dec_deg, repo_root='.', gamma=DEFAULT_GAMMA):
    data = load_backend_data(repo_root, gamma)
    RA_src = float(ra_deg)/d2r
    Dec_src = float(dec_deg)/d2r
    fks = source_sample_weights(Dec_src, data)
    S_ji, B_i, Nj = SnB_PDF(RA_src, Dec_src, data)
    SB_ji = [S_ji[k]/B_i[k] for k in range(len(data['Nks']))]
    logB_ki = [log(B_i[k]).sum() for k in range(len(data['Nks']))]
    tmp1 = max_TS_j1(fks, SB_ji, logB_ki, Nj, data)
    ts = float(tmp1[1])
    ns_hat = float(tmp1[2])
    p_loc = 0.5*math.erfc(math.sqrt(builtins.max(ts, 0.)/2.))
    return {
        "backend": "likelihood_single_source_v1",
        "best_fit_ns": ns_hat,
        "ts": ts,
        "pre_trial_p": p_loc,
        "post_trial_p": None,
        "n_events_in_roi": int(tmp1[0]),
        "gamma": float(gamma),
        "roi_deg": float(ROI*d2r),
        "note": "single-source time-integrated backend copied from likelihood_v4.py; p-value uses chi2(df=1)/2 approximation",
        "warnings": ["Phase 1.1 does not run background trials; background.n_trials is not used by this backend.", "Current callable backend uses NumPy-only integration/optimization compatibility code instead of SciPy SLSQP."],
    }






def load_backend_data(repo_root='.', gamma=DEFAULT_GAMMA):
    root = Path(repo_root).resolve()
    cache_key = (str(root), float(gamma))
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    Nks, RAs_nu, Decs_nu, sgms_nu = load_neutrino_events(root)
    bkgd_pdfs_nu = load_background_pdfs(root)
    uptimes = load_uptimes(root)
    W_accs = load_acceptance_weights(root, gamma)
    data = {"root": root, "Nks": Nks, "RAs_nu": RAs_nu, "Decs_nu": Decs_nu, "sgms_nu": sgms_nu, "bkgd_pdfs_nu": bkgd_pdfs_nu, "uptimes": uptimes, "W_accs": W_accs}
    _CACHE[cache_key] = data
    return data


def load_neutrino_events(root):
    # Copied from neutrinos_data.py with minimal edits to avoid importing plotting/scipy-heavy modules.
    filenms = array([
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC40_exp.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC59_exp.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC79_exp.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC86_I_exp.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC86_II2VII_exp_BZ.csv',])
    col_MJDs = 0
    col_sgms = 2
    col_RAs = 3
    col_Decs = 4
    col_Eproxys = 1
    Nks = zeros(len(filenms)); Nks = array(Nks, dtype=int)
    RAs_nu = []; Decs_nu = []; sgms_nu = []
    for k in range(len(filenms)):
        Nus = loadtxt(filenms[k])
        idx = where((Nus[:,col_Decs]>-87.)*(Nus[:,col_Decs]<87.))
        Nks[k] = len(idx[0])
        sgms_nu += [Nus[:, col_sgms][idx]/d2r]
        RAs_nu += [Nus[:, col_RAs][idx]/d2r]
        Decs_nu += [Nus[:, col_Decs][idx]/d2r]
        del(Nus, idx)
    return Nks, RAs_nu, Decs_nu, sgms_nu


def load_background_pdfs(root):
    # Copied from likelihood_v4.py background PDF read path.
    bkgd_pdf_dir = root/'data_output/bkgd_pdfs'
    bkgd_pdf_flms = array([
        bkgd_pdf_dir/'bkgd_pdf_IC40_exp.txt',
        bkgd_pdf_dir/'bkgd_pdf_IC59_exp.txt',
        bkgd_pdf_dir/'bkgd_pdf_IC79_exp.txt',
        bkgd_pdf_dir/'bkgd_pdf_IC86_I_exp.txt',
        bkgd_pdf_dir/'bkgd_pdf_IC86_II2VII_exp_BZ.txt',])
    bkgd_pdfs_nu = []
    for k in range(len(bkgd_pdf_flms)):
        bkgd_pdf_tmp = loadtxt(bkgd_pdf_flms[k])
        bkgd_pdfs_nu += [bkgd_pdf_tmp[:,2]]
    return bkgd_pdfs_nu


def load_uptimes(root):
    # Copied from likelihood_v4.py uptime block.
    uptime_flms = array([
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC40_exp.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC59_exp.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC79_exp.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC86_I_exp.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC86_II2VII_exp_BZ.csv',])
    uptimes = zeros(len(uptime_flms));
    for i in range(len(uptime_flms)):
        tmp = loadtxt(uptime_flms[i])
        uptimes[i] = sum(tmp[:,1]-tmp[:,0]) / 365.25
    return uptimes


def load_acceptance_weights(root, gamma):
    # Copied from likelihood_v4.py EA and f_k block with a NumPy interpolation/integration fallback.
    EAfilenms = array([
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC40_effectiveArea.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC59_effectiveArea.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC79_effectiveArea.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC86_I_effectiveArea.csv',
        root/'data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC86_II_effectiveArea.csv',])
    EAs = loadtxt(EAfilenms[0])
    Es = 10**(unique(EAs[:,0])/2.+unique(EAs[:,1])/2.)
    coszeniths = (cos(90./d2r + unique(EAs[:,2])/d2r) + cos(90./d2r + unique(EAs[:,3])/d2r))/2.
    W_accs = []
    for i in range(len(EAfilenms)):
        EAs = loadtxt(EAfilenms[i]) # 40 Es, 50 angles # Codex
        Aeff = EAs[:,4]; Aeff = Aeff.reshape(len(coszeniths),-1)
        W_acc_dat = simps_compat(Es.reshape(1,-1)**(gamma+1.)*Aeff, log(Es), axis=1) # checked # Codex
        W_accs += [(coszeniths.copy(), W_acc_dat.copy())]
    return W_accs


def source_sample_weights(Dec_src, data):
    W_accs = data['W_accs']
    uptimes = data['uptimes']
    tmp0 = interp1d_linear(W_accs[0][0], W_accs[0][1], -sin(Dec_src)) * uptimes[0]
    tmp1 = interp1d_linear(W_accs[1][0], W_accs[1][1], -sin(Dec_src)) * uptimes[1]
    tmp2 = interp1d_linear(W_accs[2][0], W_accs[2][1], -sin(Dec_src)) * uptimes[2]
    tmp3 = interp1d_linear(W_accs[3][0], W_accs[3][1], -sin(Dec_src)) * uptimes[3]
    tmp4 = interp1d_linear(W_accs[4][0], W_accs[4][1], -sin(Dec_src)) * uptimes[4]
    W_accs_src = array([tmp0, tmp1, tmp2, tmp3, tmp4])
    return W_accs_src/W_accs_src.sum()


def SnB_PDF(RA_src, Dec_src, data):
    # Copied from likelihood_v4.py::SnB_PDF with the source coordinate passed directly.
    Nks = data['Nks']
    RAs_nu = data['RAs_nu']
    Decs_nu = data['Decs_nu']
    sgms_nu = data['sgms_nu']
    bkgd_pdfs_nu = data['bkgd_pdfs_nu']
    S_ji = []; B_i = []; Nj = []
    for k in range(len(Nks)):
        RAs_nu1D = RAs_nu[k]
        Decs_nu1D = Decs_nu[k]
        sgms_nu1D = sgms_nu[k]
        tmp_idx = where(abs(Dec_src-Decs_nu1D) <= ROI)
        RAs_nu1D1 = RAs_nu1D[tmp_idx];
        Decs_nu1D1 = Decs_nu1D[tmp_idx];
        sgms_nu1D1 = sgms_nu1D[tmp_idx];
        ang_dis = cos(RA_src-RAs_nu1D1)*cos(Dec_src)*cos(Decs_nu1D1) + sin(Dec_src)*sin(Decs_nu1D1)
        ang_dis[where(ang_dis<-1.)] = -1.
        ang_dis[where(ang_dis> 1.)] = 1.
        ang_dis = arccos(ang_dis)
        ang_dis1 = ang_dis
        Njk = len(RAs_nu1D1); Nj += [Njk]
        spatial_facs = 1./(2.*pi*sgms_nu1D1**2.)*exp(-(ang_dis1**2)/(2.*sgms_nu1D1**2.))
        S_jik = spatial_facs
        S_ji = S_ji + [S_jik]
        B_ik = bkgd_pdfs_nu[k][tmp_idx]*Nks[k]/Njk # better pdf # Codex
        B_i += [B_ik]
    return S_ji, B_i, Nj




def logL_j(n_s, fks, SB_ji, logB_ki, Nj, data):
    # Copied from likelihood_v4.py::logL_j with precomputed S/B passed directly.
    logL_j = 0;
    for k in range(len(data['Nks'])):
        a = float(n_s*fks[k])/float(Nj[k])
        L_jik_fac = 1. + a*(SB_ji[k]-1.)
        if L_jik_fac.min() < 0:
            return -1e99, Nj[k]
        logL_jik = logB_ki[k] + log(L_jik_fac).sum()
        logL_j = logL_j + logL_jik
    return logL_j, sum(array(Nj)) # maybe don't output Nk? # Codex


def TS_j(n_s, fks, SB_ji, logB_ki, Nj, data):
    # Copied from likelihood_v4.py::TS_j with precomputed S/B passed directly.
    tmp3 = logL_j(n_s, fks, SB_ji, logB_ki, Nj, data)[0]
    return 2.*(tmp3 - logL_j(0., fks, SB_ji, logB_ki, Nj, data)[0])


def max_TS_j1(fks, SB_ji, logB_ki, Nj, data, ns_min=-10.):
    # Copied from likelihood_v4.py::max_TS_j1 with a NumPy bounded optimizer fallback.
    Nj_tot = logL_j(0., fks, SB_ji, logB_ki, Nj, data)[1]
    if Nj_tot == 0:
        return array([-999, -999, -999])
    def TS_j1(n_s):
        return -TS_j(n_s, fks, SB_ji, logB_ki, Nj, data)
    max_ns, min_neg_ts = bounded_minimize(TS_j1, float(ns_min), float(Nj_tot))
    max_TS_j = -1*min_neg_ts; max_ns = max_ns;
    return array([Nj_tot, max_TS_j, max_ns])


def bounded_minimize(func, lo, hi, tol=1e-5, max_iter=120):
    gr = (math.sqrt(5.) - 1.)/2.
    c = hi - gr*(hi-lo)
    d = lo + gr*(hi-lo)
    fc = func(c)
    fd = func(d)
    for i in range(max_iter):
        if abs(hi-lo) < tol:
            break
        if fc < fd:
            hi = d; d = c; fd = fc; c = hi - gr*(hi-lo); fc = func(c)
        else:
            lo = c; c = d; fc = fd; d = lo + gr*(hi-lo); fd = func(d)
    x = (lo+hi)/2.
    return x, func(x)


def interp1d_linear(xs, ys, x):
    idx = argsort(xs)
    xs1 = xs[idx]; ys1 = ys[idx]
    if x <= xs1[0]:
        return ys1[0] + (x-xs1[0])*(ys1[1]-ys1[0])/(xs1[1]-xs1[0])
    if x >= xs1[-1]:
        return ys1[-1] + (x-xs1[-1])*(ys1[-1]-ys1[-2])/(xs1[-1]-xs1[-2])
    return interp(x, xs1, ys1)


def simps_compat(y, x, axis=1):
    y1 = moveaxis(asarray(y), axis, -1)
    x1 = asarray(x)
    if y1.shape[-1] < 3:
        return trapezoid(y1, x1, axis=-1)
    if y1.shape[-1] % 2 == 0:
        return simps_compat(y1[...,:-1], x1[:-1], axis=-1) + trapezoid(y1[...,-2:], x1[-2:], axis=-1)
    h = diff(x1)
    if not allclose(h, h[0]):
        return trapezoid(y1, x1, axis=-1)
    return h[0]/3.*(y1[...,0] + y1[...,-1] + 4.*sum(y1[...,1:-1:2], axis=-1) + 2.*sum(y1[...,2:-2:2], axis=-1))
