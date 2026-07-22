from __future__ import annotations # Codex

import builtins # Codex
import csv # Codex
import json # Codex
import math # Codex
from pathlib import Path # Codex
from typing import Any # Codex

from numpy import * # Codex

from agent_core_cdx.schemas_cdx import NormalizedAnalysis, to_clean_dict # Codex
from analysis_backend_cdx.single_source_cdx import load_backend_data # Codex


SOURCE_COLUMNS = ["source_number", "source_name", "significance_rank", "ra_deg", "dec_deg", "intrinsic_weight", "ns_hat", "ts", "signed_sqrt_ts", "pre_trial_p", "pre_trial_significance", "post_trial_p", "post_trial_significance", "n_events_in_roi", "fit_status"] # Codex
STACKING_COLUMNS = ["weighting_scheme", "spectral_index", "n_sources", "ns_hat", "ts", "pre_trial_p", "pre_trial_significance", "post_trial_p", "post_trial_significance", "ns_95", "flux_100tev_95", "fraction_of_diffuse_flux_95"] # Codex


def write_catalog_outputs(run_dir: Path, normalized: NormalizedAnalysis, result: dict[str, object], repo_root: Path) -> dict[str, str]: # Codex
    source_rows = list(result.get("_source_results", [])) # Codex
    stacking_rows = list(result.get("_stacking_results", [])) # Codex
    curves = list(result.get("_stacking_curves", [])) # Codex
    source_columns = ordered_columns(SOURCE_COLUMNS, source_rows) # Codex
    stacking_columns = ordered_columns(STACKING_COLUMNS, stacking_rows) # Codex
    write_csv(run_dir/"source_results_cdx.csv", source_columns, source_rows) # Codex
    write_csv(run_dir/"stacking_results_cdx.csv", stacking_columns, stacking_rows) # Codex
    workbook_payload = { # Codex
        "source_columns": source_columns, # Codex
        "source_rows": [[clean_cell(row.get(column)) for column in source_columns] for row in source_rows], # Codex
        "stacking_columns": stacking_columns, # Codex
        "stacking_rows": [[clean_cell(row.get(column)) for column in stacking_columns] for row in stacking_rows], # Codex
        "run_information": build_run_information(normalized), # Codex
    } # Codex
    with (run_dir/"workbook_payload_cdx.json").open("w", encoding="utf-8") as handle: # Codex
        json.dump(workbook_payload, handle, indent=2, allow_nan=False) # Codex
        handle.write("\n") # Codex
    figure_dir = repo_root/"figures/runs_cdx"/run_dir.name # Codex
    figure_dir.mkdir(parents=True, exist_ok=False) # Codex
    plot_fig1(figure_dir/"fig1_sky_distribution_cdx.pdf", normalized, repo_root) # Codex
    plot_fig3(figure_dir/"fig3_ts_distribution_cdx.pdf", source_rows) # Codex
    plot_fig4(figure_dir/"fig4_stacking_cdx.pdf", curves) # Codex
    return {"source_results": "source_results_cdx.csv", "stacking_results": "stacking_results_cdx.csv", "workbook_payload": "workbook_payload_cdx.json", "fig1": str((figure_dir/"fig1_sky_distribution_cdx.pdf").relative_to(repo_root)), "fig3": str((figure_dir/"fig3_ts_distribution_cdx.pdf").relative_to(repo_root)), "fig4": str((figure_dir/"fig4_stacking_cdx.pdf").relative_to(repo_root))} # Codex


def ordered_columns(fixed: list[str], rows: list[dict[str, object]]) -> list[str]: # Codex
    extras: list[str] = [] # Codex
    for row in rows: # Codex
        for key in row: # Codex
            if key not in fixed and key not in extras: # Codex
                extras.append(key) # Codex
    return fixed+extras # Codex


def write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None: # Codex
    with path.open("w", encoding="utf-8", newline="") as handle: # Codex
        writer = csv.DictWriter(handle, fieldnames=columns) # Codex
        writer.writeheader() # Codex
        for row in rows: # Codex
            writer.writerow({column: clean_cell(row.get(column)) for column in columns}) # Codex


def clean_cell(value: object) -> object: # Codex
    if value is None: # Codex
        return None # Codex
    if isinstance(value, (integer, floating)): # Codex
        value = value.item() # Codex
    if isinstance(value, float) and not math.isfinite(value): # Codex
        return None # Codex
    return value # Codex


def build_run_information(normalized: NormalizedAnalysis) -> list[list[object]]: # Codex
    return [ # Codex
        ["field", "value"], # Codex
        ["analysis_type", normalized.analysis_type], # Codex
        ["time_mode", normalized.time_mode], # Codex
        ["data_sample", normalized.sample], # Codex
        ["n_sources", len(normalized.sources)], # Codex
        ["spectral_indices", ", ".join(str(value) for value in normalized.spectral_indices)], # Codex
        ["background_method", normalized.background_method], # Codex
        ["background_trials_requested", normalized.n_trials], # Codex
        ["random_seed", normalized.random_seed], # Codex
        ["reference", "https://arxiv.org/abs/2103.12813"], # Codex
        ["ts_definition", "TS evaluated at the maximum-likelihood estimate ns_hat"], # Codex
        ["flux_conversion", "Paper-calibrated ns-to-flux references from legacy_cdx/likelihood_v4.py and legacy_cdx/ns2flux.py"], # Codex
    ] # Codex


def plot_fig1(path: Path, normalized: NormalizedAnalysis, repo_root: Path) -> None: # Codex
    canvas_module, colors = reportlab_modules() # Codex
    data = load_backend_data(repo_root, normalized.spectral_indices[0]) # Codex
    ras = concatenate([values*180./pi for values in data["RAs_nu"]]) # Codex
    sin_decs = concatenate([sin(values) for values in data["Decs_nu"]]) # Codex
    hist, _, _ = histogram2d(ras, sin_decs, bins=[72, 36], range=[[0., 360.], [-1., 1.]]) # Codex
    c = canvas_module.Canvas(str(path), pagesize=(720., 420.)) # Codex
    left, bottom, width, height = 70., 60., 610., 310. # Codex
    max_log = log1p(hist.max()) # Codex
    for ix in range(hist.shape[0]): # Codex
        for iy in range(hist.shape[1]): # Codex
            intensity = log1p(hist[ix, iy])/max_log if max_log > 0. else 0. # Codex
            c.setFillColorRGB(0.94-0.62*intensity, 0.97-0.48*intensity, 1.-0.20*intensity) # Codex
            x = left+(71-ix)*width/72. # Codex
            y = bottom+iy*height/36. # Codex
            c.rect(x, y, width/72.+0.2, height/36.+0.2, fill=1, stroke=0) # Codex
    c.setFillColor(colors.red) # Codex
    for source in normalized.sources: # Codex
        x = left+(360.-source.ra_deg)*width/360. # Codex
        y = bottom+(sin(source.dec_rad)+1.)*height/2. # Codex
        c.circle(x, y, 1.8, fill=1, stroke=0) # Codex
    draw_axes(c, left, bottom, width, height, "Right ascension [deg]", "Declination [deg]", "Source catalog and IceCube event density") # Codex
    draw_linear_ticks(c, left, bottom, width, [0., 60., 120., 180., 240., 300., 360.], 0., 360., horizontal=True, reverse=True) # Codex
    draw_declination_ticks(c, left, bottom, height) # Codex
    c.setFillColor(colors.red) # Codex
    c.drawString(left+8., bottom+height-16., f"Sources: {len(normalized.sources)}") # Codex
    c.setFillColor(colors.black) # Codex
    c.drawString(left+8., bottom+height-30., f"IceCube events: {int(hist.sum()):,}") # Codex
    c.save() # Codex


def plot_fig3(path: Path, rows: list[dict[str, object]]) -> None: # Codex
    canvas_module, colors = reportlab_modules() # Codex
    values = array([math.sqrt(float(row["ts"])) for row in rows if float(row["ns_hat"]) >= 0.], dtype=float) # Codex
    bins = arange(0., builtins.max(5.25, (values.max()+0.5) if len(values) else 5.25), 0.25) # Codex
    counts, edges = histogram(values, bins=bins) # Codex
    centers = (edges[:-1]+edges[1:])/2. # Codex
    amplitude = fit_half_normal_amplitude(centers, counts, edges[1]-edges[0]) # Codex
    c = canvas_module.Canvas(str(path), pagesize=(540., 540.)) # Codex
    left, bottom, width, height = 75., 65., 420., 410. # Codex
    fitted_peak = amplitude if len(values) >= 20 else 0. # Codex
    ymax = builtins.max(float(counts.max())*1.7 if len(counts) else 1., fitted_peak*1.3, 2.) # Codex
    ymap = lambda value: bottom+height*(math.log10(builtins.max(value, 0.5))-math.log10(0.5))/(math.log10(ymax)-math.log10(0.5)) # Codex
    c.setStrokeColor(colors.HexColor("#1F5A94")) # Codex
    c.setFillColor(colors.HexColor("#1F5A94")) # Codex
    for x_value, count in zip(centers, counts): # Codex
        if count <= 0: # Codex
            continue # Codex
        x = left+width*x_value/edges[-1] # Codex
        y = ymap(float(count)) # Codex
        error = math.sqrt(float(count)) # Codex
        c.line(x, ymap(builtins.max(count-error, 0.5)), x, ymap(count+error)) # Codex
        c.circle(x, y, 2.2, fill=1, stroke=0) # Codex
    if len(values) >= 20: # Codex
        c.setStrokeColor(colors.red) # Codex
        previous = None # Codex
        for x_value in linspace(0., edges[-1], 300): # Codex
            expected = amplitude*math.exp(-0.5*x_value*x_value) # Codex
            point = (left+width*x_value/edges[-1], ymap(builtins.max(expected, 0.5))) # Codex
            if previous is not None: # Codex
                c.line(previous[0], previous[1], point[0], point[1]) # Codex
            previous = point # Codex
    draw_axes(c, left, bottom, width, height, "sqrt(TS)", "Number of sources in each bin", "Catalog-wide single-source analysis") # Codex
    draw_linear_ticks(c, left, bottom, width, [0., 1., 2., 3., 4., 5.], 0., edges[-1], horizontal=True) # Codex
    draw_log_ticks(c, left, bottom, height, [1., 10., 100., 1000.], 0.5, ymax, horizontal=False) # Codex
    c.setFillColor(colors.black) # Codex
    c.drawString(left+8., bottom+height-18., f"Sources with ns_hat >= 0: {len(values)}") # Codex
    if len(values) < 20: # Codex
        c.drawString(left+8., bottom+height-34., "Normal fit omitted: fewer than 20 non-negative fits") # Codex
    c.save() # Codex


def fit_half_normal_amplitude(centers: ndarray, counts: ndarray, bin_width: float) -> float: # Codex
    shape = exp(-0.5*centers**2.) # Codex
    valid = counts > 0 # Codex
    if not any(valid): # Codex
        return 1. # Codex
    weights = 1./maximum(counts[valid], 1.) # Codex
    return float(sum(weights*counts[valid]*shape[valid])/sum(weights*shape[valid]**2.)) # Codex


def plot_fig4(path: Path, curves: list[dict[str, object]]) -> None: # Codex
    canvas_module, colors = reportlab_modules() # Codex
    c = canvas_module.Canvas(str(path), pagesize=(900., 420.)) # Codex
    panels = [(65., 65., 355., 300.), (510., 65., 355., 300.)] # Codex
    color_map = {"uniform": colors.red, "input_weight": colors.blue} # Codex
    dash_map = {-2.0: [], -2.53: [7, 4], -3.0: [2, 3]} # Codex
    flux_values = [value for curve in curves for value in curve["flux_100tev"] if value is not None and value > 0.] # Codex
    flux_min = builtins.min(flux_values) if flux_values else 1e-12 # Codex
    flux_max = builtins.max(flux_values) if flux_values else 1e-7 # Codex
    delta_values = [value for curve in curves for value in curve["delta_ts"] if value is not None] # Codex
    delta_min = builtins.min(delta_values) if delta_values else -10. # Codex
    left, bottom, width, height = panels[0] # Codex
    for curve in curves: # Codex
        c.setStrokeColor(color_map.get(str(curve["weighting_scheme"]), colors.black)) # Codex
        c.setDash(dash_map.get(round(float(curve["spectral_index"]), 2), [])) # Codex
        points = [(log_map(float(x), flux_min, flux_max, left, width), linear_map(float(y), delta_min, 0., bottom, height)) for x, y in zip(curve["flux_100tev"], curve["delta_ts"]) if x is not None and x > 0.] # Codex
        draw_polyline(c, points) # Codex
    c.setDash([5, 3]) # Codex
    c.setStrokeColor(colors.black) # Codex
    y95 = linear_map(-3.84, delta_min, 0., bottom, height) # Codex
    c.line(left, y95, left+width, y95) # Codex
    c.setDash([]) # Codex
    draw_axes(c, left, bottom, width, height, "All-flavor energy flux at 100 TeV", "TS - TS(best fit)", "Stacking likelihood profiles") # Codex
    draw_log_ticks(c, left, bottom, width, decade_ticks(flux_min, flux_max), flux_min, flux_max, horizontal=True) # Codex
    draw_linear_ticks(c, left, bottom, height, delta_ticks(delta_min), delta_min, 0., horizontal=False) # Codex
    left, bottom, width, height = panels[1] # Codex
    energies = geomspace(1e4, 1e7, 180) # Codex
    diffuse = 4.98e-8*(energies/1e5)**(-0.53) # Codex
    right_curve_values = [float(value) for curve in curves for value in float(curve["flux_100tev_95"])*(energies/1e5)**(float(curve["spectral_index"])+2.) if isfinite(value) and value > 0.] # Codex
    right_curve_values.extend(float(value) for value in diffuse if value > 0.) # Codex
    right_y_min = 10.**math.floor(math.log10(builtins.min(right_curve_values))) # Codex
    right_y_max = 10.**math.ceil(math.log10(builtins.max(right_curve_values))) # Codex
    for curve in curves: # Codex
        gamma = float(curve["spectral_index"]) # Codex
        flux100 = float(curve["flux_100tev_95"]) # Codex
        values = flux100*(energies/1e5)**(gamma+2.) # Codex
        c.setStrokeColor(color_map.get(str(curve["weighting_scheme"]), colors.black)) # Codex
        c.setDash(dash_map.get(round(gamma, 2), [])) # Codex
        points = [(log_map(float(x), 1e4, 1e7, left, width), log_map(float(y), right_y_min, right_y_max, bottom, height)) for x, y in zip(energies, values) if y > 0.] # Codex
        draw_polyline(c, points) # Codex
    c.setStrokeColor(colors.green) # Codex
    c.setDash([]) # Codex
    draw_polyline(c, [(log_map(float(x), 1e4, 1e7, left, width), log_map(float(y), right_y_min, right_y_max, bottom, height)) for x, y in zip(energies, diffuse)]) # Codex
    draw_axes(c, left, bottom, width, height, "Neutrino energy [GeV]", "All-flavor energy flux", "95% CL stacking upper limits") # Codex
    draw_log_ticks(c, left, bottom, width, [1e4, 1e5, 1e6, 1e7], 1e4, 1e7, horizontal=True) # Codex
    draw_log_ticks(c, left, bottom, height, decade_ticks(right_y_min, right_y_max), right_y_min, right_y_max, horizontal=False) # Codex
    c.setFillColor(colors.red) # Codex
    c.drawString(225., 24., "Uniform weighting") # Codex
    c.setFillColor(colors.blue) # Codex
    c.drawString(350., 24., "Input weighting") # Codex
    c.setFillColor(colors.green) # Codex
    c.drawString(465., 24., "Diffuse reference") # Codex
    c.save() # Codex


def reportlab_modules(): # Codex
    try: # Codex
        from reportlab.pdfgen import canvas # Codex
        from reportlab.lib import colors # Codex
        return canvas, colors # Codex
    except ModuleNotFoundError: # Codex
        from agent_core_cdx.minimal_pdf_cdx import canvas, colors # Codex
        return canvas, colors # Codex


def draw_axes(c, left: float, bottom: float, width: float, height: float, xlabel: str, ylabel: str, title: str) -> None: # Codex
    c.setStrokeColorRGB(0., 0., 0.) # Codex
    c.setFillColorRGB(0., 0., 0.) # Codex
    c.setDash([]) # Codex
    c.rect(left, bottom, width, height, fill=0, stroke=1) # Codex
    c.setFont("Helvetica-Bold", 12.) # Codex
    c.drawCentredString(left+width/2., bottom+height+18., title) # Codex
    c.setFont("Helvetica", 10.) # Codex
    c.drawCentredString(left+width/2., bottom-28., xlabel) # Codex
    c.saveState() # Codex
    c.translate(left-42., bottom+height/2.) # Codex
    c.rotate(90.) # Codex
    c.drawCentredString(0., 0., ylabel) # Codex
    c.restoreState() # Codex


def draw_polyline(c, points: list[tuple[float, float]]) -> None: # Codex
    if len(points) < 2: # Codex
        return # Codex
    path = c.beginPath() # Codex
    path.moveTo(points[0][0], points[0][1]) # Codex
    for x, y in points[1:]: # Codex
        path.lineTo(x, y) # Codex
    c.drawPath(path, fill=0, stroke=1) # Codex


def linear_map(value: float, low: float, high: float, start: float, length: float) -> float: # Codex
    return start+length*(value-low)/(high-low) # Codex


def log_map(value: float, low: float, high: float, start: float, length: float) -> float: # Codex
    return start+length*(math.log10(value)-math.log10(low))/(math.log10(high)-math.log10(low)) # Codex


def draw_linear_ticks(c, left: float, bottom: float, length: float, ticks: list[float], low: float, high: float, horizontal: bool, reverse: bool = False) -> None: # Codex
    c.setFont("Helvetica", 8.) # Codex
    for value in ticks: # Codex
        mapped_value = high-value+low if reverse else value # Codex
        position = linear_map(mapped_value, low, high, left if horizontal else bottom, length) # Codex
        if horizontal: # Codex
            c.line(position, bottom, position, bottom-4.) # Codex
            c.drawCentredString(position, bottom-14., f"{value:g}") # Codex
        else: # Codex
            c.line(left-4., position, left, position) # Codex
            c.drawRightString(left-7., position-3., f"{value:g}") # Codex


def draw_log_ticks(c, left: float, bottom: float, length: float, ticks: list[float], low: float, high: float, horizontal: bool) -> None: # Codex
    c.setFont("Helvetica", 8.) # Codex
    for value in ticks: # Codex
        if value < low or value > high: # Codex
            continue # Codex
        position = log_map(value, low, high, left if horizontal else bottom, length) # Codex
        label = f"{value:.0e}" # Codex
        if horizontal: # Codex
            c.line(position, bottom, position, bottom-4.) # Codex
            c.drawCentredString(position, bottom-14., label) # Codex
        else: # Codex
            c.line(left-4., position, left, position) # Codex
            c.drawRightString(left-7., position-3., label) # Codex


def draw_declination_ticks(c, left: float, bottom: float, height: float) -> None: # Codex
    c.setFont("Helvetica", 8.) # Codex
    for value in [-90., -60., -30., 0., 30., 60., 90.]: # Codex
        position = bottom+(math.sin(math.radians(value))+1.)*height/2. # Codex
        c.line(left-4., position, left, position) # Codex
        c.drawRightString(left-7., position-3., f"{value:g}") # Codex


def decade_ticks(low: float, high: float) -> list[float]: # Codex
    first = int(math.floor(math.log10(low))) # Codex
    last = int(math.ceil(math.log10(high))) # Codex
    return [10.**power for power in range(first, last+1)] # Codex


def delta_ticks(low: float) -> list[float]: # Codex
    step = 2. if low > -12. else 5. # Codex
    return arange(math.ceil(low/step)*step, 0.1, step).tolist() # Codex
