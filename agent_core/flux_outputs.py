"""Tables and publication-style spectra for separately fitted flux limits."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

from agent_core.file_cache import sha256_file


def load_reference_spectra(root):
    directory = Path(root) / "data_input/references/neutrino_spectra"
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        if sha256_file(directory / name) != digest:
            raise ValueError("Reference-spectrum hash mismatch: " + name)
    metadata = json.loads((directory / "reference_spectra.json").read_text())
    references = []
    for ref in metadata["references"]:
        with (directory / ref["band_data_file"]).open() as handle:
            band = np.asarray([[float(row[k]) for k in ("energy_gev", "e2_flux_lower", "e2_flux_upper")]
                               for row in csv.DictReader(handle)])
        if not (np.all(np.isfinite(band)) and np.all(band > 0)
                and np.all(np.diff(band[:, 0]) > 0) and np.all(band[:, 2] >= band[:, 1])):
            raise ValueError("Invalid published reference band: " + ref["id"])
        references.append((ref, band))
    return references, {str((directory / name).relative_to(root)): digest
                        for name, digest in manifest["sha256"].items()}


def plot_flux_limits(limits, source_name, output_stem, root):
    """Use the approved one-panel style, with full-sky integrated diffuse flux."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    references, reference_hashes = load_reference_spectra(root)
    rows = []
    styles = [("#e43d30", "--"), ("#2458d3", "-"), ("#198446", "-.")]
    settings = {"font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
                "mathtext.fontset": "stix", "font.size": 13, "axes.linewidth": 1.05,
                "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"}
    with plt.rc_context(settings):
        fig, ax = plt.subplots(figsize=(9.2, 8.9))
        fig.subplots_adjust(left=.14, right=.965, bottom=.27, top=.87)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlim(5e2, 1e7)
        ax.tick_params(which="both", direction="in", top=True, right=True, labelsize=14)
        ax.tick_params(which="major", length=7, width=1)
        ax.tick_params(which="minor", length=3.5, width=.8)
        label_name = source_name.replace("$", r"\$")
        limit_values = []
        for index, limit in enumerate(limits):
            gamma = float(limit["gamma"])
            energy = np.geomspace(1e3, 1e7, 401)
            values = energy**2 * limit["phi0_upper_limit"] * (energy / 1e5)**(-gamma)
            limit_values.extend(values)
            color, linestyle = styles[index % len(styles)]
            ax.plot(energy, values, color=color, ls=linestyle, lw=2.1,
                    label=label_name + f" {100*limit['confidence_level']:g}% UL: " + rf"$\Gamma={gamma:g}$", zorder=4)
            arrow = (4e5, 7e4, 2.5e4)[index % 3]
            value = arrow**2 * limit["phi0_upper_limit"] * (arrow / 1e5)**(-gamma)
            ax.annotate("", xy=(arrow, value*.52), xytext=(arrow, value),
                        arrowprops={"arrowstyle": "-|>", "color": color, "lw": 1.5, "mutation_scale": 13, "shrinkA": 0, "shrinkB": 0})
            rows.extend(dict(curve=f"source_gamma_{gamma:g}", energy_gev=float(e),
                             e2_flux=float(y), e2_flux_unit="GeV cm^-2 s^-1",
                             original_e2_flux=float(y), original_e2_flux_unit="GeV cm^-2 s^-1",
                             display_factor=1., band_lower=None, band_upper=None, band_confidence_level=None)
                        for e, y in zip(energy, values))
        reference_styles = [("#171717", "-", "NGC 1068 + 68% band [1]"),
                            ("#7952a8", "-", r"$4\pi I$: 9.5 yr tracks + 68% band [2]"),
                            ("#008b95", "--", r"$4\pi I$: 10.3 yr starting tracks + band [3]")]
        for (ref, band), (color, linestyle, label) in zip(references, reference_styles, strict=True):
            energy = np.geomspace(*ref["range_gev"], 401)
            raw = energy**2 * ref["phi0_gev_units"] * (energy/ref["pivot_energy_gev"])**(-ref["gamma"])
            factor = 4*math.pi if ref["type"] == "diffuse_intensity" else 1.
            ax.plot(energy, raw*factor, color=color, ls=linestyle, lw=2.1, label=label, zorder=4)
            lo, hi = max(energy[0], band[0, 0]), min(energy[-1], band[-1, 0])
            grid = np.geomspace(lo, hi, 601)
            lower = np.exp(np.interp(np.log(grid), np.log(band[:, 0]), np.log(band[:, 1])))
            upper = np.exp(np.interp(np.log(grid), np.log(band[:, 0]), np.log(band[:, 2])))
            central = grid**2 * ref["phi0_gev_units"] * (grid/ref["pivot_energy_gev"])**(-ref["gamma"])
            if not (np.all(central >= lower*.99) and np.all(central <= upper*1.01)):
                raise ValueError("Published central spectrum falls outside its extracted band")
            ax.fill_between(grid, lower*factor, upper*factor, color=color, alpha=.19, linewidth=0, zorder=2)
            for e, y in zip(energy, raw):
                within = band[0, 0] <= e <= band[-1, 0]
                rows.append(dict(curve=ref["id"], energy_gev=float(e), e2_flux=float(y*factor),
                    e2_flux_unit="GeV cm^-2 s^-1", original_e2_flux=float(y),
                    original_e2_flux_unit="GeV cm^-2 s^-1 sr^-1" if factor != 1 else "GeV cm^-2 s^-1",
                    display_factor=factor,
                    band_lower=float(np.exp(np.interp(np.log(e), np.log(band[:, 0]), np.log(band[:, 1])))*factor) if within else None,
                    band_upper=float(np.exp(np.interp(np.log(e), np.log(band[:, 0]), np.log(band[:, 2])))*factor) if within else None,
                    band_confidence_level=None if ref["id"] == "diffuse_starting_tracks" else .68))
        ax.set_ylim(min(1e-10, min(limit_values)*.4), max(9e-6, max(limit_values)*1.5))
        ax.set_xlabel(r'$E_\nu\;[\mathrm{GeV}]$', fontsize=23, labelpad=9)
        ax.set_ylabel(r'$E_\nu^2\,\mathrm{d}F_{\nu_\mu+\bar\nu_\mu}/\mathrm{d}E_\nu\;[\mathrm{GeV\,cm^{-2}\,s^{-1}}]$', fontsize=20, labelpad=11)
        ax.legend(loc="upper right", fontsize=11.3, frameon=False, handlelength=3, labelspacing=.55, borderaxespad=1)
        title = fig.text(.14, .96, source_name + " and reference neutrino spectra", fontsize=22, parse_math=False)
        fig.text(.14, .915, r'Common flux units  |  $\nu_\mu+\bar\nu_\mu$  |  Published reference uncertainty bands', fontsize=13.5, color="#404040")
        foot = [
            r'Diffuse is integrated over the full sky: $\mathrm{d}F/\mathrm{d}E=4\pi\,\mathrm{sr}\times\mathrm{d}I/\mathrm{d}E$; point-source fluxes are unchanged.',
            'Shading reproduces the published vector bands, including parameter correlations.',
            'NGC 1068 and 9.5 yr tracks: 68% bands. Starting tracks: band as in Fig. 17 [3]; CL not stated there.',
            'Source limits: preliminary asymptotic estimates; coverage unvalidated; detector/PDF systematics excluded.',
            '[1] IceCube, ApJ 981, 131 (2025), arXiv:2406.06684, Fig. 2.',
            '[2] IceCube, ApJ 928, 50 (2022), arXiv:2111.10299, Fig. 4.',
            '[3] IceCube, Phys. Rev. D 110, 022001 (2024), arXiv:2402.18026, Fig. 17.']
        for index, line in enumerate(foot):
            fig.text(.14, .168-.019*index, line, fontsize=9.3, color="#4b4b4b")
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        if title.get_window_extent(renderer).x1 > .965*fig.bbox.width:
            title.set_fontsize(22*(.825*fig.bbox.width)/title.get_window_extent(renderer).width)
            fig.canvas.draw()
        for artist in (ax.xaxis.label, ax.yaxis.label, *fig.texts):
            box = artist.get_window_extent(renderer)
            if box.x0 < 0 or box.y0 < 0 or box.x1 > fig.bbox.width or box.y1 > fig.bbox.height:
                raise ValueError("Spectrum figure text extends beyond the canvas")
        outputs = {}
        for suffix in ("png", "pdf", "svg"):
            path = Path(str(output_stem) + "." + suffix)
            fig.savefig(path, dpi=220, facecolor="white", metadata={"Creator": "NuSrcAgent"})
            outputs[suffix] = str(path)
        plt.close(fig)
    return rows, outputs, reference_hashes


def write_flux_outputs(run_dir, normalized, result, root):
    """Write each source's limits, evaluated profiles, plot curves and provenance."""
    from agent_core.analysis_outputs import write_csv
    entries = [(1, normalized.sources[0].name, result)] if normalized.analysis_type == "single_source" else [
        (item["source_number"], item["source_name"], item["fit"]) for item in result.get("source_results", [])]
    for number, name, fit in entries:
        fits = fit.get("flux_upper_limit_fits", [])
        scalar = fit.get("flux_upper_limit")
        if not fits and scalar is None:
            continue
        folder = run_dir if normalized.analysis_type == "single_source" else run_dir / f"source_{number:05d}"
        folder.mkdir(parents=True, exist_ok=True)
        limits = [item["flux_upper_limit"] for item in fits] if fits else [scalar]
        rows = [{k: v for k, v in limit.items() if not isinstance(v, (dict, list))} for limit in limits]
        table = folder / "flux_upper_limits.csv"
        write_csv(table, list(rows[0]), rows)
        profile_rows = [dict(gamma=limit["gamma"], **point) for limit in limits for point in limit["profile"]]
        profile = folder / "upper_limit_profiles.csv"
        write_csv(profile, list(profile_rows[0]), profile_rows)
        files = fit.setdefault("generated_files", {})
        files.update(flux_upper_limits=str(table), upper_limit_profiles=str(profile))
        # Keep scalar artifacts separately to preserve existing test-checkout requests.
        if scalar is not None:
            single_table = folder / "flux_upper_limit.csv"
            single_profile = folder / "upper_limit_profile.csv"
            write_csv(single_table, list(rows[0]), rows)
            write_csv(single_profile, list(scalar["profile"][0]), scalar["profile"])
            files.update(flux_upper_limit=str(single_table), upper_limit_profile=str(single_profile))
        if not fits:
            continue
        figures = root / "figures/runs" / run_dir.name / f"source_{number:05d}"
        figures.mkdir(parents=True, exist_ok=False)
        curves, outputs, hashes = plot_flux_limits(limits, name, figures / "flux_upper_limits_95", root)
        curve_path = folder / "spectrum_curves.csv"
        write_csv(curve_path, list(curves[0]), curves)
        files.update({"flux_spectrum_"+key: value for key, value in outputs.items()})
        files["spectrum_curves"] = str(curve_path)
        provenance_path = folder / "flux_plot_provenance.json"
        provenance = dict(source_name=name, reference_sha256=hashes,
            diffuse_conversion="F_diffuse(E) = 4*pi sr * I_diffuse(E); full-sky integrated isotropic flux",
            flavor="nu_mu+anti_nu_mu; no factor of three", energy_flux_unit="GeV cm^-2 s^-1",
            source_energy_range_gev=[1e3, 1e7], source_range_meaning="power-law hypothesis display range; not a measured sensitive range",
            limits=[{k: v for k, v in limit.items() if k != "profile"} for limit in limits],
            outputs_sha256={path: sha256_file(path) for path in [*outputs.values(), str(curve_path), str(table), str(profile)]})
        provenance_path.write_text(json.dumps(provenance, indent=2, allow_nan=False)+"\n")
        files["flux_plot_provenance"] = str(provenance_path)
