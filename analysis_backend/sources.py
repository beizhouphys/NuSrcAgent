"""Source catalogs shared by the 10-year and 14-year analysis backends.

This module owns source coordinates, catalog membership and ordering, model
weight quantities, and conversion to the standard catalog row format used by
the supported runtime.  It deliberately contains no event data, detector
acceptance, likelihood, or flux-conversion code.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np


RADIO_BRIGHT_AGN_RAW_CATALOG = Path("data_input/VLBI_rfc_2019c_cat_BZ.dat")
RADIO_BRIGHT_AGN_EXPECTED_COUNT = 3386
RADIO_BRIGHT_AGN_XBAND_MIN_JY = 0.15
RADIO_BRIGHT_AGN_ABS_DEC_MAX_DEG = 87.0
RADIO_BRIGHT_AGN_BUILTIN_NAME = "radio_bright_agn_rfc2019c_3386"
BUILTIN_CATALOG_NAMES = (RADIO_BRIGHT_AGN_BUILTIN_NAME,)


def resolve_source_path(repo_root, path):
    path = Path(path).expanduser()
    return path if path.is_absolute() else Path(repo_root).resolve() / path


def read_source_catalog(path):
    """Read a headered CSV/TSV catalog without changing its source metadata."""
    path = Path(path)
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [dict(row) for row in reader], list(reader.fieldnames or [])


def standardize_source_rows(
    rows,
    name_column="source_name",
    ra_column="ra_deg",
    dec_column="dec_deg",
    weight_columns=(),
):
    """Validate and standardize source identity, coordinates, index, and weights."""
    standardized = []
    for catalog_index, input_row in enumerate(rows):
        row = dict(input_row)
        source_name = str(row.get(name_column, "")).strip() or f"source_{catalog_index + 1:04d}"
        try:
            ra_deg = float(row[ra_column])
            dec_deg = float(row[dec_column])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"source row {catalog_index} has invalid RA/Dec") from error
        if not math.isfinite(ra_deg) or not 0.0 <= ra_deg < 360.0:
            raise ValueError(f"source row {catalog_index} RA must be finite and in [0, 360) deg")
        if not math.isfinite(dec_deg) or not -90.0 <= dec_deg <= 90.0:
            raise ValueError(f"source row {catalog_index} Dec must be finite and in [-90, 90] deg")
        for column in weight_columns:
            try:
                value = float(row[column])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"source row {catalog_index} has invalid weight column {column!r}") from error
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"source row {catalog_index} weight {column!r} must be finite and non-negative")
            row[column] = value
        row.update(
            {
                "catalog_index": catalog_index,
                "source_name": source_name,
                "ra_deg": ra_deg,
                "dec_deg": dec_deg,
            }
        )
        standardized.append(row)
    if not standardized:
        raise ValueError("source catalog contains no rows")
    for column in weight_columns:
        if sum(float(row[column]) for row in standardized) <= 0.0:
            raise ValueError(f"source weight column {column!r} must have a positive sum")
    return standardized


def load_standard_source_catalog(
    path,
    name_column="source_name",
    ra_column="ra_deg",
    dec_column="dec_deg",
    weight_columns=(),
):
    rows, _ = read_source_catalog(path)
    return standardize_source_rows(rows, name_column, ra_column, dec_column, weight_columns)


def source_specs(rows, model_weight_column=None):
    """Return the source dictionaries consumed by both SkyLLH DR2 backends."""
    return [
        {
            "name": row["source_name"],
            "ra_rad": np.deg2rad(float(row["ra_deg"])),
            "dec_rad": np.deg2rad(float(row["dec_deg"])),
            "w_model": 1.0 if model_weight_column is None else float(row[model_weight_column]),
        }
        for row in rows
    ]


def model_weight_values(rows, weight_column=None, normalize=False):
    """Return uniform or catalog-column intrinsic weights, W_j,model."""
    values = np.ones(len(rows), dtype=np.float64) if weight_column is None else np.asarray(
        [float(row[weight_column]) for row in rows], dtype=np.float64
    )
    if np.any(~np.isfinite(values)) or np.any(values < 0.0) or float(values.sum()) <= 0.0:
        raise ValueError("source model weights must be finite, non-negative, and have a positive sum")
    return values / values.sum() if normalize else values


def _sexagesimal_ra_deg(hour, minute, second):
    return 15.0 * (float(hour) + float(minute) / 60.0 + float(second) / 3600.0)


def _sexagesimal_dec_deg(degree_token, minute, second):
    sign = -1.0 if str(degree_token).startswith("-") else 1.0
    return sign * (abs(float(degree_token)) + float(minute) / 60.0 + float(second) / 3600.0)


def load_radio_bright_agn_catalog(repo_root="."):
    """Load the 3386 RFC 2019c sources selected for arXiv:2103.12813."""
    for i0 in range(1):  # RFC 2019c radio-bright AGN; use range(0) to disable this catalog
        raw_path = resolve_source_path(repo_root, RADIO_BRIGHT_AGN_RAW_CATALOG)
        rows = []
        with raw_path.open(encoding="utf-8", errors="replace") as handle:
            for raw_line_number, line in enumerate(handle, start=1):
                fields = line.split()
                if len(fields) < 25 or fields[0].startswith("#"):
                    continue
                try:
                    xband_flux_jy = float(fields[17])
                    ra_deg = _sexagesimal_ra_deg(fields[3], fields[4], fields[5])
                    dec_deg = _sexagesimal_dec_deg(fields[6], fields[7], fields[8])
                except ValueError:
                    continue
                if xband_flux_jy < RADIO_BRIGHT_AGN_XBAND_MIN_JY:
                    continue
                if abs(dec_deg) >= RADIO_BRIGHT_AGN_ABS_DEC_MAX_DEG:
                    continue
                rows.append(
                    {
                        "raw_line_number": raw_line_number,
                        "ivs_name": fields[1],
                        "j2000_name": fields[2],
                        "source_name": fields[1],
                        "ra_deg": ra_deg,
                        "dec_deg": dec_deg,
                        "xband_flux_jy": xband_flux_jy,
                    }
                )
        rows = standardize_source_rows(rows, weight_columns=("xband_flux_jy",))
        if len(rows) != RADIO_BRIGHT_AGN_EXPECTED_COUNT:
            raise RuntimeError(
                f"Expected {RADIO_BRIGHT_AGN_EXPECTED_COUNT} selected RFC 2019c sources, found {len(rows)}"
            )
        return rows
    raise RuntimeError("RFC 2019c radio-bright AGN catalog is disabled in sources.py")


def load_builtin_catalog(name, repo_root="."):
    """Load one explicitly named built-in source catalog for either data sample."""
    if str(name) == RADIO_BRIGHT_AGN_BUILTIN_NAME:
        return load_radio_bright_agn_catalog(repo_root)
    raise ValueError(f"unknown built-in source catalog: {name}")
