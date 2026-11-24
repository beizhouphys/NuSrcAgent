from __future__ import annotations

import builtins
import csv
import json
import math
from pathlib import Path

from numpy import *

from reportlab.pdfgen import canvas
from reportlab.lib import colors

from agent_core.schemas import NormalizedAnalysis
from analysis_backend.dr1_single_source import load_backend_data


SOURCE_COLUMNS = ["source_number", "source_name", "significance_rank", "ra_deg", "dec_deg", "intrinsic_weight", "n", "s", "ns_hat", "ts", "signed_sqrt_ts", "pre_trial_p", "pre_trial_significance", "post_trial_p", "post_trial_significance", "n_events_in_roi", "fit_status"]
STACKING_COLUMNS = ["weighting_scheme", "s", "spectral_index", "n_sources", "n", "ns_hat", "ts", "pre_trial_p", "pre_trial_significance", "post_trial_p", "post_trial_significance", "n_95", "ns_95", "flux_100tev_95", "fraction_of_diffuse_flux_95"]


def write_catalog_outputs(run_dir: Path, normalized: NormalizedAnalysis, result: dict[str, object], repo_root: Path) -> dict[str, str]:
    source_rows = [dict(row, n=row["ns_hat"]) for row in result.get("_source_results", [])]
    stacking_rows = [dict(row, n=row["ns_hat"], s=-row["spectral_index"], n_95=row.get("ns_95"))
                     for row in result.get("_stacking_results", [])]
    curves = list(result.get("_stacking_curves", []))
    source_columns = ordered_columns(SOURCE_COLUMNS, source_rows)
    stacking_columns = ordered_columns(STACKING_COLUMNS, stacking_rows)
    write_csv(run_dir/"source_results.csv", source_columns, source_rows)
    write_csv(run_dir/"stacking_results.csv", stacking_columns, stacking_rows)
    workbook_payload = {
        "source_columns": source_columns,
        "source_rows": [[clean_cell(row.get(column)) for column in source_columns] for row in source_rows],
        "stacking_columns": stacking_columns,
        "stacking_rows": [[clean_cell(row.get(column)) for column in stacking_columns] for row in stacking_rows],
        "run_information": build_run_information(normalized),
    }
    with (run_dir/"workbook_payload.json").open("w", encoding="utf-8") as handle:
        json.dump(workbook_payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    figure_dir = repo_root/"figures/runs"/run_dir.name
    figure_dir.mkdir(parents=True, exist_ok=False)
    plot_fig1(figure_dir/"fig1_sky_distribution.pdf", normalized, repo_root)
    plot_fig3(figure_dir/"fig3_ts_distribution.pdf", source_rows)
    plot_fig4(figure_dir/"fig4_stacking.pdf", curves)
    return {"source_results": "source_results.csv", "stacking_results": "stacking_results.csv", "workbook_payload": "workbook_payload.json", "fig1": str((figure_dir/"fig1_sky_distribution.pdf").relative_to(repo_root)), "fig3": str((figure_dir/"fig3_ts_distribution.pdf").relative_to(repo_root)), "fig4": str((figure_dir/"fig4_stacking.pdf").relative_to(repo_root))}


def ordered_columns(fixed: list[str], rows: list[dict[str, object]]) -> list[str]:
    extras: list[str] = []
    for row in rows:
        for key in row:
            if key not in fixed and key not in extras:
                extras.append(key)
    return fixed+extras


def write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean_cell(row.get(column)) for column in columns})


def clean_cell(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (integer, floating)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def build_run_information(normalized: NormalizedAnalysis) -> list[list[object]]:
    return [
        ["field", "value"],
        ["analysis_type", normalized.analysis_type],
        ["time_mode", normalized.time_mode],
        ["data_sample", normalized.sample],
        ["n_sources", len(normalized.sources)],
        ["s", ", ".join(str(-value) for value in normalized.spectral_indices)],
        ["background_method", normalized.background_method],
        ["background_trials_requested", normalized.n_trials],
        ["random_seed", normalized.random_seed],
        ["reference", "https://arxiv.org/abs/2103.12813"],
        ["ts_definition", "TS evaluated at the maximum-likelihood estimate of n"],
        ["flux_conversion", "Paper-calibrated ns-to-flux references from legacy_codex_revised/likelihood_v4.py and legacy_codex_revised/ns2flux.py"],
    ]


def plot_fig1(path: Path, normalized: NormalizedAnalysis, repo_root: Path) -> None:
    data = load_backend_data(repo_root, normalized.spectral_indices[0])
    ras = concatenate([values*180./pi for values in data["RAs_nu"]])
    sin_decs = concatenate([sin(values) for values in data["Decs_nu"]])
    hist, _, _ = histogram2d(ras, sin_decs, bins=[72, 36], range=[[0., 360.], [-1., 1.]])
    c = canvas.Canvas(str(path), pagesize=(720., 420.))
    left, bottom, width, height = 70., 60., 610., 310.
    max_log = log1p(hist.max())
    for ix in range(hist.shape[0]):
        for iy in range(hist.shape[1]):
            intensity = log1p(hist[ix, iy])/max_log if max_log > 0. else 0.
            c.setFillColorRGB(0.94-0.62*intensity, 0.97-0.48*intensity, 1.-0.20*intensity)
            x = left+(71-ix)*width/72.
            y = bottom+iy*height/36.
            c.rect(x, y, width/72.+0.2, height/36.+0.2, fill=1, stroke=0)
    c.setFillColor(colors.red)
    for source in normalized.sources:
        x = left+(360.-source.ra_deg)*width/360.
        y = bottom+(sin(source.dec_rad)+1.)*height/2.
        c.circle(x, y, 1.8, fill=1, stroke=0)
    draw_axes(c, left, bottom, width, height, "Right ascension [deg]", "Declination [deg]", "Source catalog and IceCube event density")
    draw_linear_ticks(c, left, bottom, width, [0., 60., 120., 180., 240., 300., 360.], 0., 360., horizontal=True, reverse=True)
    draw_declination_ticks(c, left, bottom, height)
    c.setFillColor(colors.red)
    c.drawString(left+8., bottom+height-16., f"Sources: {len(normalized.sources)}")
    c.setFillColor(colors.black)
    c.drawString(left+8., bottom+height-30., f"IceCube events: {int(hist.sum()):,}")
    c.save()


def plot_fig3(path: Path, rows: list[dict[str, object]]) -> None:
    values = array([math.sqrt(float(row["ts"])) for row in rows if float(row["ns_hat"]) >= 0.], dtype=float)
    bins = arange(0., builtins.max(5.25, (values.max()+0.5) if len(values) else 5.25), 0.25)
    counts, edges = histogram(values, bins=bins)
    centers = (edges[:-1]+edges[1:])/2.
    amplitude = fit_half_normal_amplitude(centers, counts, edges[1]-edges[0])
    c = canvas.Canvas(str(path), pagesize=(540., 540.))
    left, bottom, width, height = 75., 65., 420., 410.
    fitted_peak = amplitude if len(values) >= 20 else 0.
    ymax = builtins.max(float(counts.max())*1.7 if len(counts) else 1., fitted_peak*1.3, 2.)
    ymap = lambda value: bottom+height*(math.log10(builtins.max(value, 0.5))-math.log10(0.5))/(math.log10(ymax)-math.log10(0.5))
    c.setStrokeColor(colors.HexColor("#1F5A94"))
    c.setFillColor(colors.HexColor("#1F5A94"))
    for x_value, count in zip(centers, counts):
        if count <= 0:
            continue
        x = left+width*x_value/edges[-1]
        y = ymap(float(count))
        error = math.sqrt(float(count))
        c.line(x, ymap(builtins.max(count-error, 0.5)), x, ymap(count+error))
        c.circle(x, y, 2.2, fill=1, stroke=0)
    if len(values) >= 20:
        c.setStrokeColor(colors.red)
        previous = None
        for x_value in linspace(0., edges[-1], 300):
            expected = amplitude*math.exp(-0.5*x_value*x_value)
            point = (left+width*x_value/edges[-1], ymap(builtins.max(expected, 0.5)))
            if previous is not None:
                c.line(previous[0], previous[1], point[0], point[1])
            previous = point
    draw_axes(c, left, bottom, width, height, "sqrt(TS)", "Number of sources in each bin", "Catalog-wide single-source analysis")
    draw_linear_ticks(c, left, bottom, width, [0., 1., 2., 3., 4., 5.], 0., edges[-1], horizontal=True)
    draw_log_ticks(c, left, bottom, height, [1., 10., 100., 1000.], 0.5, ymax, horizontal=False)
    c.setFillColor(colors.black)
    c.drawString(left+8., bottom+height-18., f"Sources with n >= 0: {len(values)}")
    if len(values) < 20:
        c.drawString(left+8., bottom+height-34., "Normal fit omitted: fewer than 20 non-negative fits")
    c.save()


def fit_half_normal_amplitude(centers: ndarray, counts: ndarray, bin_width: float) -> float:
    shape = exp(-0.5*centers**2.)
    valid = counts > 0
    if not any(valid):
        return 1.
    weights = 1./maximum(counts[valid], 1.)
    return float(sum(weights*counts[valid]*shape[valid])/sum(weights*shape[valid]**2.))


def plot_fig4(path: Path, curves: list[dict[str, object]]) -> None:
    c = canvas.Canvas(str(path), pagesize=(900., 420.))
    panels = [(65., 65., 355., 300.), (510., 65., 355., 300.)]
    color_map = {"uniform": colors.red, "input_weight": colors.blue}
    dash_map = {-2.0: [], -2.5: [7, 4], -3.0: [2, 3]}
    profile_points = [[(float(x), float(y)) for x, y in zip(curve["flux_100tev"], curve["delta_ts"]) if x is not None and y is not None and isfinite(x) and isfinite(y) and x > 0. and y > -1e90] for curve in curves]
    flux_values = [x for points in profile_points for x, _ in points]
    flux_min = builtins.min(flux_values) if flux_values else 1e-12
    flux_max = builtins.max(flux_values) if flux_values else 1e-7
    delta_values = [y for points in profile_points for _, y in points]
    delta_min = builtins.max(builtins.min(builtins.min(delta_values), -4.5), -12.) if delta_values else -10.
    left, bottom, width, height = panels[0]
    for curve, raw_points in zip(curves, profile_points):
        c.setStrokeColor(color_map.get(str(curve["weighting_scheme"]), colors.black))
        c.setDash(dash_map.get(round(float(curve["spectral_index"]), 2), []))
        points = [(log_map(x, flux_min, flux_max, left, width), linear_map(builtins.max(y, delta_min), delta_min, 0., bottom, height)) for x, y in raw_points]
        draw_polyline(c, points)
    c.setDash([5, 3])
    c.setStrokeColor(colors.black)
    y95 = linear_map(-3.84, delta_min, 0., bottom, height)
    c.line(left, y95, left+width, y95)
    c.setDash([])
    draw_axes(c, left, bottom, width, height, "All-flavor energy flux at 100 TeV", "TS - TS(best fit)", "Stacking likelihood profiles")
    draw_log_ticks(c, left, bottom, width, decade_ticks(flux_min, flux_max), flux_min, flux_max, horizontal=True)
    draw_linear_ticks(c, left, bottom, height, delta_ticks(delta_min), delta_min, 0., horizontal=False)
    if not flux_values:
        c.setFont("Helvetica", 9.)
        c.drawCentredString(left+width/2., bottom+height/2., "Flux conversion unavailable for requested spectral index")
    left, bottom, width, height = panels[1]
    energies = geomspace(1e4, 1e7, 180)
    diffuse = 4.98e-8*(energies/1e5)**(-0.53)
    valid_limit_curves = [curve for curve in curves if isfinite(float(curve["flux_100tev_95"])) and float(curve["flux_100tev_95"]) > 0.]
    right_curve_values = [float(value) for curve in valid_limit_curves for value in float(curve["flux_100tev_95"])*(energies/1e5)**(float(curve["spectral_index"])+2.) if isfinite(value) and value > 0.]
    right_curve_values.extend(float(value) for value in diffuse if value > 0.)
    right_y_min = 10.**math.floor(math.log10(builtins.min(right_curve_values)))
    right_y_max = 10.**math.ceil(math.log10(builtins.max(right_curve_values)))
    for curve in valid_limit_curves:
        gamma = float(curve["spectral_index"])
        flux100 = float(curve["flux_100tev_95"])
        values = flux100*(energies/1e5)**(gamma+2.)
        c.setStrokeColor(color_map.get(str(curve["weighting_scheme"]), colors.black))
        c.setDash(dash_map.get(round(gamma, 2), []))
        points = [(log_map(float(x), 1e4, 1e7, left, width), log_map(float(y), right_y_min, right_y_max, bottom, height)) for x, y in zip(energies, values) if y > 0.]
        draw_polyline(c, points)
    c.setStrokeColor(colors.green)
    c.setDash([])
    draw_polyline(c, [(log_map(float(x), 1e4, 1e7, left, width), log_map(float(y), right_y_min, right_y_max, bottom, height)) for x, y in zip(energies, diffuse)])
    draw_axes(c, left, bottom, width, height, "Neutrino energy [GeV]", "All-flavor energy flux", "95% CL stacking upper limits")
    draw_log_ticks(c, left, bottom, width, [1e4, 1e5, 1e6, 1e7], 1e4, 1e7, horizontal=True)
    draw_log_ticks(c, left, bottom, height, decade_ticks(right_y_min, right_y_max), right_y_min, right_y_max, horizontal=False)
    if not valid_limit_curves:
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9.)
        c.drawCentredString(left+width/2., bottom+height-24., "Flux upper limit unavailable for requested spectral index")
    if builtins.any(str(curve["weighting_scheme"]) == "uniform" for curve in valid_limit_curves):
        c.setFillColor(colors.red)
        c.drawString(225., 24., "Uniform weighting")
    if builtins.any(str(curve["weighting_scheme"]) == "input_weight" for curve in valid_limit_curves):
        c.setFillColor(colors.blue)
        c.drawString(350., 24., "Input weighting")
    c.setFillColor(colors.green)
    c.drawString(465., 24., "Diffuse reference")
    c.save()


def draw_axes(c, left: float, bottom: float, width: float, height: float, xlabel: str, ylabel: str, title: str) -> None:
    c.setStrokeColorRGB(0., 0., 0.)
    c.setFillColorRGB(0., 0., 0.)
    c.setDash([])
    c.rect(left, bottom, width, height, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 12.)
    c.drawCentredString(left+width/2., bottom+height+18., title)
    c.setFont("Helvetica", 10.)
    c.drawCentredString(left+width/2., bottom-28., xlabel)
    c.saveState()
    c.translate(left-42., bottom+height/2.)
    c.rotate(90.)
    c.drawCentredString(0., 0., ylabel)
    c.restoreState()


def draw_polyline(c, points: list[tuple[float, float]]) -> None:
    if len(points) < 2:
        return
    path = c.beginPath()
    path.moveTo(points[0][0], points[0][1])
    for x, y in points[1:]:
        path.lineTo(x, y)
    c.drawPath(path, fill=0, stroke=1)


def linear_map(value: float, low: float, high: float, start: float, length: float) -> float:
    return start+length*(value-low)/(high-low)


def log_map(value: float, low: float, high: float, start: float, length: float) -> float:
    return start+length*(math.log10(value)-math.log10(low))/(math.log10(high)-math.log10(low))


def draw_linear_ticks(c, left: float, bottom: float, length: float, ticks: list[float], low: float, high: float, horizontal: bool, reverse: bool = False) -> None:
    c.setFont("Helvetica", 8.)
    for value in ticks:
        mapped_value = high-value+low if reverse else value
        position = linear_map(mapped_value, low, high, left if horizontal else bottom, length)
        if horizontal:
            c.line(position, bottom, position, bottom-4.)
            c.drawCentredString(position, bottom-14., f"{value:g}")
        else:
            c.line(left-4., position, left, position)
            c.drawRightString(left-7., position-3., f"{value:g}")


def draw_log_ticks(c, left: float, bottom: float, length: float, ticks: list[float], low: float, high: float, horizontal: bool) -> None:
    c.setFont("Helvetica", 8.)
    for value in ticks:
        if value < low or value > high:
            continue
        position = log_map(value, low, high, left if horizontal else bottom, length)
        label = f"{value:.0e}"
        if horizontal:
            c.line(position, bottom, position, bottom-4.)
            c.drawCentredString(position, bottom-14., label)
        else:
            c.line(left-4., position, left, position)
            c.drawRightString(left-7., position-3., label)


def draw_declination_ticks(c, left: float, bottom: float, height: float) -> None:
    c.setFont("Helvetica", 8.)
    for value in [-90., -60., -30., 0., 30., 60., 90.]:
        position = bottom+(math.sin(math.radians(value))+1.)*height/2.
        c.line(left-4., position, left, position)
        c.drawRightString(left-7., position-3., f"{value:g}")


def decade_ticks(low: float, high: float) -> list[float]:
    first = int(math.floor(math.log10(low)))
    last = int(math.ceil(math.log10(high)))
    return [10.**power for power in range(first, last+1)]


def delta_ticks(low: float) -> list[float]:
    step = 2. if low > -12. else 5.
    return arange(math.ceil(low/step)*step, 0.1, step).tolist()
