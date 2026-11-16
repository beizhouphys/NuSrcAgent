"""Spectrum input contract shared by every analysis workflow.

Command Gamma is the signed exponent in (E/E0)^Gamma. Tabulated spectra
are fixed shapes; their normalization is fitted through the signal count.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path


def tabulated_spectrum(path, kind, energy_unit, outside_support, root="."):
    path = Path(path).expanduser()
    path = (Path(root) / path).resolve() if not path.is_absolute() else path.resolve()
    if kind not in {"dnde", "ednde", "e2dnde"}:
        raise ValueError("Specify spectrum kind: dnde, ednde or e2dnde")
    if energy_unit not in {"GeV", "TeV"}:
        raise ValueError("Specify spectrum energy unit: GeV or TeV")
    if outside_support not in {"zero", "extrapolate"}:
        raise ValueError("Specify the spectrum outside-support rule: zero or extrapolate")
    rows = []
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        fields = line.replace(",", " ").split()
        if len(fields) != 2:
            raise ValueError("Spectrum requires two columns: energy and spectrum value")
        energy, value = map(float, fields)
        if not math.isfinite(energy) or energy <= 0 or not math.isfinite(value) or value < 0:
            raise ValueError("Spectrum requires finite positive energies and nonnegative values")
        energy *= 1000. if energy_unit == "TeV" else 1.
        value /= energy ** {"dnde": 0, "ednde": 1, "e2dnde": 2}[kind]
        if not math.isfinite(value):
            raise ValueError("Non-finite dN/dE after spectrum conversion")
        rows.append((energy, value))
    rows.sort()
    if len(rows) < 2 or any(b[0] <= a[0] for a, b in zip(rows, rows[1:])) or max(v for _, v in rows) <= 0:
        raise ValueError("Spectrum needs at least two unique energies and nonzero emission")
    if outside_support == "extrapolate" and any(value <= 0 for _, value in rows):
        raise ValueError("Power-law extrapolation requires strictly positive spectrum values")
    scale = max(v for _, v in rows)
    return dict(kind="tabulated", file=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                input_kind=kind, energy_unit=energy_unit, outside_support=outside_support,
                energy_gev=[e for e, _ in rows], shape=[v / scale for _, v in rows],
                normalization="dimensionless dN/dE shape divided by its maximum tabulated value")


def validate_spectrum(spectrum, gamma, gamma_mode, bounds=None, root="."):
    errors = []
    if spectrum:
        try:
            if spectrum.get("kind") != "tabulated":
                raise ValueError("Only tabulated non-power-law spectra are accepted")
            current = tabulated_spectrum(spectrum["file"], spectrum["input_kind"], spectrum["energy_unit"],
                                         spectrum["outside_support"], root)
            if current != spectrum:
                raise ValueError("Spectrum file or its recorded shape changed; create a new request")
        except (ValueError, OSError, KeyError, TypeError) as exc:
            errors.append(str(exc))
        if gamma != 0.:
            errors.append("A non-PL spectrum uses a fixed internal mapper coordinate, not a supplied PL index")
        if gamma_mode != "fixed" or bounds is not None:
            errors.append("A supplied non-power-law spectrum fixes its shape; no power-law Gamma is fitted")
    elif gamma is None or not math.isfinite(float(gamma)):
        errors.append("Power-law exponent must be finite")
    if bounds is not None:
        if (not isinstance(bounds, (list, tuple)) or len(bounds) != 2
                or not all(math.isfinite(float(v)) for v in bounds) or bounds[0] >= bounds[1]
                or gamma_mode != "fitted" or gamma is None or not bounds[0] <= gamma <= bounds[1]):
            errors.append("Gamma bounds require an ordered finite exponent interval, fitted mode and a seed inside it")
    return errors


def response_required(gamma, spectrum=None, bounds=None):
    if spectrum:
        return True
    if bounds is not None:
        return bounds[0] < -6. or bounds[1] > -1.
    return gamma is not None and not -6. <= float(gamma) <= -1.


def response_notice(gamma, spectrum=None, bounds=None, likelihood_mode="spatial_energy"):
    required = response_required(gamma, spectrum, bounds)
    return dict(required=required,
        message=(("Calculate signal-energy PDFs and detector acceptance for the requested spectrum before interpolation and LLH fitting. "
                  if likelihood_mode == "spatial_energy" else "Calculate detector acceptance for the requested spectrum; spatial-only fitting uses no energy PDFs. ")
                 + "Measure a preparation unit in this invocation to estimate remaining preparation time; fitting time is separate."
                 if required else "Use the existing signal-energy PDFs and the conventional detector-acceptance calculation."),
        remaining_seconds=None, estimate_basis="pending_current_preparation_pilot" if required else "existing_tables")
