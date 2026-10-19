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


def plot_flux_limits(limits, source_name, output_stem, root, measurement=None):
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
        if measurement is not None and measurement["reported"]:
            energy = np.geomspace(1e3, 1e7, 401)
            central = energy**2 * measurement["phi0_hat"] * (energy/measurement["pivot_energy_gev"])**(-measurement["gamma"])
            if measurement["contours"]:
                contour = measurement["contours"][0]
                points = contour["lower_branch"] + contour["upper_branch"]
                spectra = np.asarray([energy**2 * point["phi0"] * (energy/1e3)**(-point["gamma"]) for point in points])
                lower, upper = spectra.min(axis=0), spectra.max(axis=0)
                band_label = "68.27% joint-region envelope"
            else:
                interval = next(item for item in measurement["intervals"] if item["parameter"] == "phi0" and item["confidence_level"] < .7)
                lower, upper = [central * interval[key]/measurement["phi0_hat"] for key in ("lower", "upper")]
                band_label = "68.27% fixed-spectrum interval"
            ax.fill_between(energy, lower, upper, color="#d17c12", alpha=.2,
                            label=band_label, zorder=2)
            ax.plot(energy, central, color="#d17c12", lw=2.4, label=label_name+" primary best fit", zorder=5)
            limit_values.extend(central)
            rows.extend(dict(curve="source_measurement", energy_gev=float(e), e2_flux=float(y),
                e2_flux_unit="GeV cm^-2 s^-1", original_e2_flux=float(y),
                original_e2_flux_unit="GeV cm^-2 s^-1", display_factor=1.,
                band_lower=float(lo), band_upper=float(hi), band_confidence_level=0.6826894921370859)
                for e, y, lo, hi in zip(energy, central, lower, upper))
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
        ax.legend(loc="upper right", fontsize=10.2, frameon=True, framealpha=.93,
                  edgecolor="none", handlelength=3, labelspacing=.45, borderaxespad=.7)
        title = fig.text(.14, .96, source_name + " and reference neutrino spectra", fontsize=22, parse_math=False)
        fig.text(.14, .915, r'Common flux units  |  $\nu_\mu+\bar\nu_\mu$  |  Published reference uncertainty bands', fontsize=13.5, color="#404040")
        foot = [
            r'Diffuse is integrated over the full sky: $\mathrm{d}F/\mathrm{d}E=4\pi\,\mathrm{sr}\times\mathrm{d}I/\mathrm{d}E$; point-source fluxes are unchanged.',
            'Reference shading: published bands. Source shading: 68.27% region envelope, not a simultaneous confidence band.',
            'NGC 1068 and 9.5 yr tracks: 68% bands. Starting tracks: band as in Fig. 17 [3]; CL not stated there.',
            'Source estimates use profile likelihood; confidence levels are stated in the legend.',
            'Source curves are complete power laws; the display range is not a measured sensitive range.',
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


def plot_flux_contours(measurement, source_name, output_stem):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with plt.rc_context({"font.family": "serif", "mathtext.fontset": "stix", "font.size": 12,
                         "pdf.fonttype": 42, "svg.fonttype": "none"}):
        fig, ax = plt.subplots(figsize=(7.8, 6.4))
        fig.subplots_adjust(left=.15, right=.96, bottom=.23, top=.89)
        for contour, color in zip(reversed(measurement["contours"]), ("#7752a5", "#d17c12")):
            lower, upper = contour["lower_branch"], contour["upper_branch"]
            points = lower+list(reversed(upper))
            label = f"{100*contour['confidence_level']:.2f}% joint CL"
            if contour["closed"]:
                points += points[:1]
                ax.fill([p["gamma"] for p in points], [p["phi0"]*1e14 for p in points], color=color, alpha=.12)
                ax.plot([p["gamma"] for p in points], [p["phi0"]*1e14 for p in points], color=color, label=label)
            else:
                for index, branch in enumerate((lower, upper)):
                    ax.plot([p["gamma"] for p in branch], [p["phi0"]*1e14 for p in branch], color=color,
                            label=label+" (truncated)" if index == 0 else None)
        ax.plot(measurement["gamma"], measurement["phi0_hat"]*1e14, "k*", ms=12, label="Primary best fit")
        ax.set_xlabel(r"$\Gamma$ in $\mathrm{d}\Phi/\mathrm{d}E\propto E^{-\Gamma}$", fontsize=16)
        ax.set_ylabel(r"$\phi_{1\,\mathrm{TeV}}\ [10^{-14}\ \mathrm{GeV}^{-1}\,\mathrm{cm}^{-2}\,\mathrm{s}^{-1}]$", fontsize=15)
        ax.set_title(source_name+": flux and spectral index", pad=16)
        ax.tick_params(which="both", direction="in", top=True, right=True)
        ax.legend(frameon=False)
        fig.text(.15, .105, "Joint regions: 2 degrees of freedom; normalization and Gamma vary together.", fontsize=10)
        fig.text(.15, .075, "Profile-likelihood confidence regions; statistical uncertainty.", fontsize=10)
        fig.text(.15, .045, "TS > 9 is a reporting criterion.", fontsize=10)
        outputs = {}
        for suffix in ("png", "pdf", "svg"):
            path = Path(str(output_stem)+"."+suffix)
            fig.savefig(path, dpi=200)
            outputs[suffix] = str(path)
        plt.close(fig)
    return outputs


def write_measurement_tables(folder, measurement, files):
    from agent_core.analysis_outputs import write_csv
    base = {k: v for k, v in measurement.items() if not isinstance(v, (dict, list))}
    rows = [dict(base, **interval) for interval in measurement["intervals"]] or [base]
    table = folder / "flux_measurement.csv"
    write_csv(table, list(rows[0]), rows)
    files["flux_measurement"] = str(table)
    if not measurement["reported"]:
        return
    table = folder / "flux_measurement_profiles.csv"
    write_csv(table, list(measurement["profiles"][0]), measurement["profiles"])
    files["flux_measurement_profiles"] = str(table)
    if measurement["contours"]:
        rows = [dict(confidence_level=c["confidence_level"], dof=c["dof"], critical_q=c["critical_q"],
                     branch=branch, **point) for c in measurement["contours"]
                for branch in ("lower_branch", "upper_branch") for point in c[branch]]
        table = folder / "flux_measurement_contours.csv"
        write_csv(table, list(rows[0]), rows)
        files["flux_measurement_contours"] = str(table)


def write_flux_outputs(run_dir, normalized, result, root):
    """Write each source's limits, evaluated profiles, plot curves and provenance."""
    from agent_core.analysis_outputs import write_csv
    entries = [(1, normalized.sources[0].name, result)] if normalized.analysis_type == "single_source" else [
        (item["source_number"], item["source_name"], item["fit"]) for item in result.get("source_results", [])]
    for number, name, fit in entries:
        fits = fit.get("flux_upper_limit_fits", [])
        scalar = fit.get("flux_upper_limit")
        measurement = fit.get("flux_measurement")
        if not fits and scalar is None and measurement is None:
            continue
        folder = run_dir if normalized.analysis_type == "single_source" else run_dir / f"source_{number:05d}"
        folder.mkdir(parents=True, exist_ok=True)
        files = fit.setdefault("generated_files", {})
        if measurement is not None:
            write_measurement_tables(folder, measurement, files)
        limits = [item["flux_upper_limit"] for item in fits] if fits else [scalar]
        limits = [limit for limit in limits if limit is not None]
        rows = [{k: v for k, v in limit.items() if not isinstance(v, (dict, list))} for limit in limits]
        table = folder / "flux_upper_limits.csv"
        if rows:
            write_csv(table, list(rows[0]), rows)
        profile_rows = [dict(gamma=limit["gamma"], **point) for limit in limits for point in limit["profile"]]
        profile = folder / "upper_limit_profiles.csv"
        if profile_rows:
            write_csv(profile, list(profile_rows[0]), profile_rows)
            files.update(flux_upper_limits=str(table), upper_limit_profiles=str(profile))
        # Keep scalar artifacts separately to preserve existing test-checkout requests.
        if scalar is not None:
            single_table = folder / "flux_upper_limit.csv"
            single_profile = folder / "upper_limit_profile.csv"
            write_csv(single_table, list(rows[0]), rows)
            write_csv(single_profile, list(scalar["profile"][0]), scalar["profile"])
            files.update(flux_upper_limit=str(single_table), upper_limit_profile=str(single_profile))
        reported_measurement = measurement is not None and measurement["reported"]
        if not fits and not reported_measurement:
            continue
        figures = root / "figures/runs" / run_dir.name / f"source_{number:05d}"
        figures.mkdir(parents=True, exist_ok=False)
        stem = "flux_upper_limits_95" if fits else "flux_measurement_spectrum"
        curves, outputs, hashes = plot_flux_limits(limits, name, figures / stem, root, measurement)
        curve_path = folder / "spectrum_curves.csv"
        write_csv(curve_path, list(curves[0]), curves)
        files.update({"flux_spectrum_"+key: value for key, value in outputs.items()})
        if reported_measurement and measurement["contours"]:
            outputs.update({"contour_"+key: value for key, value in plot_flux_contours(
                measurement, name, figures/"flux_measurement_contours").items()})
            files.update({"flux_"+key: value for key, value in outputs.items() if key.startswith("contour_")})
        files["spectrum_curves"] = str(curve_path)
        provenance_path = folder / "flux_plot_provenance.json"
        artifact_paths = [*outputs.values(), str(curve_path)]
        artifact_paths.extend(files[key] for key in ("flux_upper_limits", "upper_limit_profiles", "flux_measurement", "flux_measurement_profiles", "flux_measurement_contours") if key in files)
        provenance = dict(source_name=name, reference_sha256=hashes,
            diffuse_conversion="F_diffuse(E) = 4*pi sr * I_diffuse(E); full-sky integrated isotropic flux",
            flavor="nu_mu+anti_nu_mu; no factor of three", energy_flux_unit="GeV cm^-2 s^-1",
            source_energy_range_gev=[1e3, 1e7], source_range_meaning="power-law hypothesis display range; not a measured sensitive range",
            limits=[{k: v for k, v in limit.items() if k != "profile"} for limit in limits],
            measurement=None if measurement is None else {k: v for k, v in measurement.items() if k not in {"profiles", "contours"}},
            measurement_band_meaning="sampled envelope of the 68.27% joint phi1TeV-Gamma region, not a simultaneous confidence band; fixed-Gamma uses its 1D interval",
            outputs_sha256={path: sha256_file(path) for path in artifact_paths})
        provenance_path.write_text(json.dumps(provenance, indent=2, allow_nan=False)+"\n")
        files["flux_plot_provenance"] = str(provenance_path)
