"""Checks for primary-spectrum flux reporting and its numerical artifacts."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from scipy.stats import chi2

from agent_core.file_cache import sha256_file


def review_flux_measurement(review, result, normalized, root):
    from agent_core.review import add_check
    measurement = result.get("flux_measurement", {})
    files = result.get("generated_files", {})
    threshold = normalized["flux_measurement_ts_threshold"]
    close = lambda a, b: math.isclose(float(a), float(b), rel_tol=1e-7, abs_tol=1e-6)
    try:
        valid = (threshold == measurement["ts_threshold"] == 9.0
            and measurement["threshold_operator"] == ">"
            and measurement["reported"] == (result["TS"] > threshold)
            and close(measurement["TS"], result["TS"])
            and measurement["gamma_mode"] == result["gamma_mode"]
            and measurement["gamma"] == result["gamma"]
            and measurement["ns_hat"] == result["ns"]
            and measurement["pivot_energy_gev"] == 1e3
            and measurement["phi0_unit"] == "GeV^-1 cm^-2 s^-1"
            and measurement["flavor"] == "nu_mu+anti_nu_mu"
            and measurement["method"] == "asymptotic_profile_likelihood"
            and measurement["coverage_validated"] is False
            and measurement["systematic_uncertainties_included"] is False)
        yield1 = sum(float(row[0]) for row in result["w_acc_by_dataset"].values())
        valid = valid and math.isfinite(measurement["phi0_hat"]) and measurement["phi0_hat"] >= 0
        valid = valid and math.isclose(measurement["yield_at_best"], yield1, rel_tol=1e-10)
        valid = valid and math.isclose(measurement["phi0_hat"]*yield1, result["ns"], rel_tol=1e-10, abs_tol=1e-10)
        valid = valid and math.isclose(measurement["phi100_hat"], measurement["phi0_hat"]*100**(-result["gamma"]), rel_tol=1e-12, abs_tol=0.)
        valid = valid and all(measurement[k] == result[k] for k in ("event_selection", "event_dec_min_deg", "event_dec_max_deg", "fit_bounds"))
    except (ValueError, TypeError, KeyError):
        valid = False
    add_check(review, "dr2_flux_measurement_gate", "pass" if valid else "fail",
              "strict TS > 9 gate, primary spectrum, flux units and detector yield are consistent" if valid else "missing or inconsistent primary flux estimate or TS gate", False)
    if not valid:
        return
    for warning in measurement.get("warnings", []):
        add_check(review, "dr2_flux_measurement_boundary", "warning", warning, False)
    try:
        intervals = measurement["intervals"]
        expected_parameters = ["phi0", "gamma"] if result["gamma_mode"] == "fitted" else ["phi0"]
        expected_count = 2*len(expected_parameters) if measurement["reported"] else 0
        valid = len(intervals) == expected_count
        for parameter in expected_parameters if measurement["reported"] else []:
            subset = [item for item in intervals if item["parameter"] == parameter]
            valid = valid and [item["confidence_level"] for item in subset] == [0.6826894921370859, 0.95]
            best = measurement["phi0_hat"] if parameter == "phi0" else measurement["gamma"]
            valid = valid and subset[1]["lower"] <= subset[0]["lower"] <= best <= subset[0]["upper"] <= subset[1]["upper"]
            valid = valid and all((item["lower"] < best or item["lower_at_boundary"])
                                  and (item["upper"] > best or item["upper_at_boundary"]) for item in subset)
            for item in subset:
                target = float(chi2.ppf(item["confidence_level"], 1))
                valid = valid and item["dof"] == 1 and close(item["critical_q"], target)
                for side in ("lower", "upper"):
                    valid = valid and (item["q_"+side] <= target+1e-5 if item[side+"_at_boundary"] else close(item["q_"+side], target))
        contours = measurement["contours"]
        expected_contours = 2 if measurement["reported"] and result["gamma_mode"] == "fitted" else 0
        valid = valid and len(contours) == expected_contours
        for contour in contours:
            valid = valid and contour["dof"] == 2 and close(contour["critical_q"], chi2.ppf(contour["confidence_level"], 2))
            for branch in ("lower_branch", "upper_branch"):
                points = contour[branch]
                valid = valid and len(points) >= 33 and all(
                    math.isfinite(p["phi0"]) and p["phi0"] > 0 and 0 < p["ns"] < result["fit_bounds"]["ns"][1]
                    and close(p["q"], contour["critical_q"]) for p in points)
        valid = valid and all(math.isfinite(p["q"]) and p["q"] >= 0 for p in measurement["profiles"])
    except (ValueError, TypeError, KeyError, IndexError):
        valid = False
    add_check(review, "dr2_flux_measurement_profiles", "pass" if valid else "fail",
              "profile intervals and joint contours use their declared confidence levels and degrees of freedom" if valid else "inconsistent flux confidence intervals or contours", False)
    if not valid:
        return
    try:
        def read_table(key):
            with Path(files[key]).open() as handle:
                return list(csv.DictReader(handle))

        table = read_table("flux_measurement")
        valid = len(table) == max(1, len(intervals))
        base = {k: v for k, v in measurement.items() if not isinstance(v, (dict, list))}
        for row, interval in zip(table, intervals or [{}]):
            for key, reference in dict(base, **interval).items():
                if isinstance(reference, bool):
                    valid = valid and row[key] == str(reference)
                elif isinstance(reference, (int, float)):
                    valid = valid and math.isclose(float(row[key]), reference, rel_tol=1e-12, abs_tol=0.)
                else:
                    valid = valid and row[key] == str(reference)
        if measurement["reported"]:
            table = read_table("flux_measurement_profiles")
            valid = valid and len(table) == len(measurement["profiles"])
            for row, point in zip(table, measurement["profiles"]):
                valid = valid and row["parameter"] == point["parameter"]
                valid = valid and all(math.isclose(float(row[k]), point[k], rel_tol=1e-12, abs_tol=0.) for k in ("phi0", "gamma", "ns", "q"))
            provenance = json.loads(Path(files["flux_plot_provenance"]).read_text())
            valid = valid and all(sha256_file(path) == digest for path, digest in provenance["outputs_sha256"].items())
            valid = valid and all(sha256_file(root/path) == digest for path, digest in provenance["reference_sha256"].items())
            with Path(files["spectrum_curves"]).open() as handle:
                all_curves = list(csv.DictReader(handle))
            curves = [row for row in all_curves if row["curve"] == "source_measurement"]
            valid = valid and len(curves) == 401
            for row in curves:
                energy = float(row["energy_gev"])
                expected = energy**2*measurement["phi0_hat"]*(energy/1e3)**(-measurement["gamma"])
                valid = valid and math.isclose(float(row["e2_flux"]), expected, rel_tol=1e-12, abs_tol=0.)
                valid = valid and float(row["display_factor"]) == 1 and row["e2_flux_unit"] == "GeV cm^-2 s^-1"
                if contours:
                    contour = contours[0]
                    spectra = [energy**2*p["phi0"]*(energy/1e3)**(-p["gamma"])
                               for p in contour["lower_branch"]+contour["upper_branch"]]
                    expected_lower, expected_upper = min(spectra), max(spectra)
                else:
                    interval = intervals[0]
                    expected_lower, expected_upper = [expected*interval[k]/measurement["phi0_hat"] for k in ("lower", "upper")]
                valid = valid and math.isclose(float(row["band_lower"]), expected_lower, rel_tol=1e-12, abs_tol=0.)
                valid = valid and math.isclose(float(row["band_upper"]), expected_upper, rel_tol=1e-12, abs_tol=0.)
            for row in all_curves:
                factor = 4*math.pi if row["curve"].startswith("diffuse") else 1.
                valid = valid and float(row["display_factor"]) == factor
                valid = valid and math.isclose(float(row["e2_flux"]), float(row["original_e2_flux"])*factor, rel_tol=1e-12, abs_tol=0.)
                if row["curve"] == "diffuse_starting_tracks":
                    valid = valid and row["band_confidence_level"] == ""
            for suffix in ("png", "pdf", "svg"):
                valid = valid and Path(files["flux_spectrum_"+suffix]).stat().st_size > 100
                if contours:
                    valid = valid and Path(files["flux_contour_"+suffix]).stat().st_size > 100
            if contours:
                table = read_table("flux_measurement_contours")
                points = [dict(confidence_level=c["confidence_level"], **p) for c in contours for branch in ("lower_branch", "upper_branch") for p in c[branch]]
                valid = valid and len(table) == len(points)
                valid = valid and all(math.isclose(float(row[k]), p[k], rel_tol=1e-12, abs_tol=0.) for row, p in zip(table, points) for k in ("confidence_level", "phi0", "gamma", "ns", "q"))
    except (OSError, ValueError, KeyError, TypeError):
        valid = False
    add_check(review, "dr2_flux_measurement_artifacts", "pass" if valid else "fail",
              "flux/profile/contour tables, figures, units and provenance hashes are consistent" if valid else "missing or inconsistent flux measurement artifacts", False)
