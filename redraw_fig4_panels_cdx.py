#!/usr/bin/env python3  # Codex
from numpy import *  # Codex
import matplotlib  # Codex
matplotlib.use('Agg')  # Codex
import matplotlib.pyplot as plt  # Codex
import os  # Codex
import use  # Codex

d2r = 180. / pi  # Codex
OUTDIR = 'data_output/stacking_cdx'  # cdx
FIGDIR = 'figures'  # Codex
os.makedirs(FIGDIR, exist_ok=True)  # Codex

GAMMAS = array([-2.00, -2.53, -3.00])  # Codex
WEIGHTINGS = [('equal', 'Equal weighting', 'red'), ('xband', 'X-band flux-density weighting', 'blue')]  # Codex
WEIGHT_TAGS = {'equal': 'WeightEq', 'xband': 'WeightXband'}  # Codex
LINESTYLES = {-2.00: '--', -2.53: '-', -3.00: '-.'}  # Codex
GAMMA_LABELS = {-2.00: '-2.0', -2.53: '-2.53', -3.00: '-3.0'}  # Codex
ASTRO_NS_REFS = {-2.00: 3217.3, -2.53: 8845.7, -3.00: 49282.2}  # Codex
PHI0_MU = {-2.00: 5e-18 / 3., -2.53: 1.66e-18, -3.00: 5e-18 / 3.}  # Codex
ASTRO_FLUX_100 = {gamma: 3. * PHI0_MU[gamma] * 1e10 for gamma in ASTRO_NS_REFS}  # Codex


def gamma_tag(gamma):  # Codex
    return '%.2f' % abs(gamma)  # Codex


def load_ts_curve(weighting, gamma):  # Codex
    flm = os.path.join(OUTDIR, 'RQs3386_10yrNu_TS_%s_GM%s_cdx.txt' % (WEIGHT_TAGS[weighting], gamma_tag(gamma)))  # cdx
    return loadtxt(flm).T  # Codex


def crossing_ns(ns, ts, target=-3.84):  # Codex
    diff = ts - target  # Codex
    inds = where(diff[:-1] * diff[1:] <= 0.)[0]  # Codex
    if len(inds) == 0:  # Codex
        raise RuntimeError('No 95 percent crossing found in TS curve.')  # Codex
    i = inds[0]  # Codex
    return ns[i] + (target - ts[i]) * (ns[i + 1] - ns[i]) / (ts[i + 1] - ts[i])  # Codex


def build_summary_from_likelihood_outputs():  # Codex
    summary = {}  # Codex
    for weighting, label, color in WEIGHTINGS:  # Codex
        for gamma in GAMMAS:  # Codex
            ns, ts = load_ts_curve(weighting, float(gamma))  # Codex
            imax = argmax(ts)  # Codex
            summary[(weighting, float(gamma))] = dict(TS_max=0.0, ns_hat=ns[imax], ns_95=crossing_ns(ns, ts))  # Codex
    return summary  # Codex


def ns_to_flux100(ns, gamma):  # Codex
    return ns / ASTRO_NS_REFS[float(gamma)] * ASTRO_FLUX_100[float(gamma)]  # Codex


def setup_ticks(ax):  # Codex
    ax.tick_params(axis='both', which='major', direction='in', length=10, width=1.4, labelsize=18, top=True, right=True)  # Codex
    ax.tick_params(axis='both', which='minor', direction='in', length=5, width=1.0, labelsize=18, top=True, right=True)  # Codex
    for spine in ax.spines.values():  # Codex
        spine.set_linewidth(1.1)  # Codex


def draw_left_panel():  # Codex
    fig = plt.figure(figsize=(6.2, 6.2), facecolor='w')  # Codex
    ax = fig.add_axes([0.15, 0.13, 0.80, 0.82])  # Codex
    ax.set_xscale('log')  # Codex
    ax.set_yscale('linear')  # Codex
    handles = []  # Codex
    for weighting, label, color in WEIGHTINGS:  # Codex
        for gamma in GAMMAS:  # Codex
            ns, ts = load_ts_curve(weighting, float(gamma))  # Codex
            flux = ns_to_flux100(ns, float(gamma))  # Codex
            line, = ax.plot(flux, ts, color=color, ls=LINESTYLES[float(gamma)], lw=2.0)  # Codex
            if float(gamma) == -2.53:  # Codex
                handles += [line]  # Codex
    ax.axhline(-3.84, color='k', ls='--', lw=1.8)  # Codex
    astro_center = ASTRO_FLUX_100[-2.53]  # Codex
    ax.axvspan(astro_center * 0.78, astro_center * 1.22, color='mediumseagreen', alpha=0.65, ec='green', lw=1.5)  # Codex
    ax.axvline(astro_center, color='green', lw=2.0)  # Codex
    ax.annotate(r'95\% limit', xy=(3.1e-10, -3.84), xytext=(6.3e-11, -3.72), fontsize=18, color='k', arrowprops=dict(arrowstyle='-|>', color='k', lw=1.5))  # Codex
    ax.text(3.6e-8, 0.78, 'Tot. astroph. $\\nu$ flux at 100 TeV\n(IceCube)', color='green', fontsize=18, ha='right', va='top')  # Codex
    ax.text(1.5e-8, -2.35, '-2.0', color='red', fontsize=18)  # Codex
    ax.text(2.1e-9, -2.35, '-2.53', color='red', fontsize=18)  # Codex
    ax.text(4.0e-10, -2.35, '-3.0', color='red', fontsize=18)  # Codex
    ax.text(8.0e-9, -5.25, '-2.0', color='blue', fontsize=18)  # Codex
    ax.text(1.2e-9, -5.25, '-2.53', color='blue', fontsize=18)  # Codex
    ax.text(1.3e-10, -5.25, r'$\Gamma=-3.0$', color='blue', fontsize=18)  # Codex
    ax.set_xlabel(r'$E_\nu^2 dF_\nu/dE_\nu$ at 100 TeV  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]', fontsize=20)  # Codex
    ax.set_ylabel('TS', fontsize=22)  # Codex
    ax.set_xlim(5e-11, 1e-7)  # Codex
    ax.set_ylim(-10, 1)  # Codex
    ax.legend(handles, [WEIGHTINGS[0][1], WEIGHTINGS[1][1]], loc='lower left', fontsize=16, framealpha=0.80)  # Codex
    setup_ticks(ax)  # Codex
    fig.savefig(os.path.join(FIGDIR, 'Fig4_left_panel_reproduction_cdx.pdf'), bbox_inches='tight', pad_inches=0.06)  # cdx
    fig.savefig(os.path.join(FIGDIR, 'Fig4_left_panel_reproduction_cdx.png'), dpi=240, bbox_inches='tight', pad_inches=0.06)  # cdx
    plt.close(fig)  # Codex


def draw_right_panel(summary):  # Codex
    fig = plt.figure(figsize=(6.2, 6.2), facecolor='w')  # Codex
    ax = fig.add_axes([0.16, 0.13, 0.79, 0.82])  # Codex
    ax.set_xscale('log')  # Codex
    ax.set_yscale('log')  # Codex
    Es = use.ebs(1e3, 1e7, 500)  # Codex
    handles = []  # Codex
    for weighting, label, color in WEIGHTINGS:  # Codex
        for gamma in GAMMAS:  # Codex
            ns95 = summary[(weighting, float(gamma))]['ns_95']  # Codex
            flux100 = ns_to_flux100(ns95, float(gamma))  # Codex
            yy = flux100 * (Es / 1e5) ** (float(gamma) + 2.)  # Codex
            line, = ax.plot(Es, yy, color=color, ls=LINESTYLES[float(gamma)], lw=2.0)  # Codex
            if float(gamma) == -2.53:  # Codex
                handles += [line]  # Codex
    center = ASTRO_FLUX_100[-2.53] * (Es / 1e5) ** (-0.53)  # Codex
    ax.fill_between(Es, center * 0.78, center * 1.22, color='mediumseagreen', alpha=0.65, ec='green', lw=1.3)  # Codex
    ax.plot(Es, center, color='green', lw=2.0)  # Codex
    for weighting, color, x1, x2 in [('equal', 'red', 4.5e5, 1.5e6), ('xband', 'blue', 3.0e5, 1.0e6)]:  # Codex
        y = ns_to_flux100(summary[(weighting, -2.00)]['ns_95'], -2.00)  # Codex
        ax.hlines(y, 1e3, 1e7, colors=color, linestyles='--', lw=1.6)  # Codex
        ax.annotate('', xy=(x1, y / 2.0), xytext=(x1, y), arrowprops=dict(arrowstyle='-|>', color=color, lw=1.5))  # Codex
        ax.annotate('', xy=(x2, y / 8.0), xytext=(x2, y / 3.0), arrowprops=dict(arrowstyle='-|>', color=color, lw=1.5))  # Codex
    ax.text(1.4e5, 1.3e-8, '-2.0', color='red', fontsize=18)  # Codex
    ax.text(1.7e6, 1.0e-9, '-2.53', color='red', fontsize=18, rotation=-32)  # Codex
    ax.text(1.9e5, 4.5e-10, '-3.0', color='red', fontsize=18)  # Codex
    ax.text(7.0e4, 7.0e-9, '-2.0', color='blue', fontsize=18)  # Codex
    ax.text(6.8e5, 7.0e-10, '-2.53', color='blue', fontsize=18, rotation=-32)  # Codex
    ax.text(2.3e4, 2.6e-10, r'$\Gamma=-3.0$', color='blue', fontsize=18)  # Codex
    ax.text(1.6e4, 2.4e-7, 'Tot. astroph. $\\nu$ flux (IceCube)', color='green', fontsize=18, rotation=-28, ha='left', va='top')  # Codex
    ax.set_xlabel(r'$E_\nu$  [ GeV ]', fontsize=20)  # Codex
    ax.set_ylabel(r'$E_\nu^2 dF_\nu/dE_\nu$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]', fontsize=20)  # Codex
    ax.set_xlim(1e3, 1e7)  # Codex
    ax.set_ylim(4e-11, 3e-7)  # Codex
    ax.legend(handles, [WEIGHTINGS[0][1], WEIGHTINGS[1][1]], loc='lower left', fontsize=16, framealpha=0.80)  # Codex
    setup_ticks(ax)  # Codex
    fig.savefig(os.path.join(FIGDIR, 'Fig4_right_panel_reproduction_cdx.pdf'), bbox_inches='tight', pad_inches=0.06)  # cdx
    fig.savefig(os.path.join(FIGDIR, 'Fig4_right_panel_reproduction_cdx.png'), dpi=240, bbox_inches='tight', pad_inches=0.06)  # cdx
    plt.close(fig)  # Codex


def main():  # Codex
    summary = build_summary_from_likelihood_outputs()  # Codex
    draw_left_panel()  # Codex
    draw_right_panel(summary)  # Codex
    print('# wrote separate Fig. 4 panels to figures/')  # Codex


if __name__ == '__main__':  # Codex
    main()  # Codex
