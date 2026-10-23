from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from analysis_backend.sources import read_source_catalog
from agent_core.coordinates import CoordinateError, convert_coordinates, resolve_catalog_coordinates


NAME_ALIASES = ["source_name", "name", "source", "object", "ivs_name", "j2000_name"]
RA_ALIASES = ["ra_deg", "ra", "raj2000", "ra_j2000", "right_ascension"]
DEC_ALIASES = ["dec_deg", "dec", "dej2000", "dec_j2000", "declination"]
WEIGHT_HINTS = ["weight", "flux", "luminosity", "lumin", "radio", "xband"]


def inspect_catalog(path_value: str, name_column: Optional[str] = None, ra_column: Optional[str] = None, dec_column: Optional[str] = None, weight_column: Optional[str] = None, coordinates=None) -> Dict[str, Any]:
    path = Path(path_value).expanduser().resolve()
    result: Dict[str, Any] = {"tool": "inspect_catalog", "catalog": str(path), "status": "pass", "errors": [], "warnings": [], "questions": []}
    if not path.exists():
        result["status"] = "fail"
        result["errors"].append("catalog file does not exist")
        return result
    if path.suffix.lower() not in {".csv", ".tsv", ".tab"}:
        result["status"] = "fail"
        result["errors"].append("catalog must be a headered CSV or TSV file for the current pipeline")
        return result
    rows, columns = read_catalog(path)
    result["row_count"] = len(rows)
    result["columns"] = columns
    if not rows:
        result["status"] = "fail"
        result["errors"].append("catalog contains no data rows")
        return result
    inferred_name = name_column or infer_column(columns, NAME_ALIASES)
    try:
        coordinate_settings = resolve_catalog_coordinates(columns, ra_column, dec_column, coordinates)
    except CoordinateError as exc:
        result["errors"].append(str(exc))
        result["questions"].append(str(exc))
        result["status"] = "fail"
        return result
    result["coordinates"] = coordinate_settings
    inferred_ra = coordinate_settings["longitude_column"]
    inferred_dec = coordinate_settings["latitude_column"]
    result["inferred_columns"] = {"name": inferred_name, "ra_deg": inferred_ra, "dec_deg": inferred_dec, "weight": weight_column}
    for label, column in [("name", inferred_name), ("ra_deg", inferred_ra), ("dec_deg", inferred_dec)]:
        if column is None:
            if label != "name":
                result["errors"].append("could not infer the %s column" % label)
        elif column not in columns:
            result["errors"].append("specified %s column is missing: %s" % (label, column))
    if result["errors"]:
        result["status"] = "fail"
        result["questions"].append("Identify the source-name and coordinate columns, with coordinate frame and angular units.")
        return result
    coordinate_review = inspect_coordinates(rows, inferred_name, inferred_ra, inferred_dec, coordinate_settings)
    result["coordinate_review"] = coordinate_review
    if coordinate_review["invalid_rows"] or coordinate_review["missing_rows"] or coordinate_review["duplicate_coordinate_pairs"]:
        result["warnings"].append("catalog coordinates require review")
    candidates = inspect_weight_candidates(rows, columns, {inferred_name, inferred_ra, inferred_dec})
    result["weight_candidates"] = candidates
    if weight_column is not None:
        if weight_column not in columns:
            result["errors"].append("specified weight column is missing: %s" % weight_column)
        else:
            result["inferred_columns"]["weight"] = weight_column
            result["selected_weight_review"] = inspect_numeric_column(rows, weight_column)
    elif candidates:
        result["questions"].append("Use uniform weights or one of these catalog columns: %s?" % ", ".join(item["column"] for item in candidates))
    else:
        result["questions"].append("Use uniform weights, or provide manual weights?")
    if result["errors"]:
        result["status"] = "fail"
    elif result["warnings"] or result["questions"]:
        result["status"] = "warning"
    return result


def read_catalog(path: Path) -> tuple[List[Dict[str, str]], List[str]]:
    return read_source_catalog(path)


def infer_column(columns: List[str], aliases: List[str]) -> Optional[str]:
    normalized = {normalize_name(column): column for column in columns}
    for alias in aliases:
        if normalize_name(alias) in normalized:
            return normalized[normalize_name(alias)]
    return None


def normalize_name(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def inspect_coordinates(rows: List[Dict[str, str]], name_column: str, ra_column: str, dec_column: str, settings=None) -> Dict[str, Any]:
    missing_rows: List[int] = []
    invalid_rows: List[int] = []
    unnamed_rows: List[int] = []
    coordinates = []
    ra_values = []
    dec_values = []
    for index, row in enumerate(rows, start=1):
        if not str(row.get(name_column, "")).strip():
            unnamed_rows.append(index)
        if not str(row.get(ra_column, "")).strip() or not str(row.get(dec_column, "")).strip():
            missing_rows.append(index)
            continue
        try:
            if settings:
                converted = convert_coordinates(row[ra_column], row[dec_column], **settings)
                ra_value, dec_value = converted["ra_deg"], converted["dec_deg"]
            else:
                ra_value = float(row[ra_column])
                dec_value = float(row[dec_column])
        except (TypeError, ValueError):
            invalid_rows.append(index)
            continue
        if not math.isfinite(ra_value) or not math.isfinite(dec_value) or not 0.0 <= ra_value < 360.0 or not -90.0 <= dec_value <= 90.0:
            invalid_rows.append(index)
            continue
        coordinates.append((round(ra_value, 10), round(dec_value, 10)))
        ra_values.append(ra_value)
        dec_values.append(dec_value)
    return {"missing_rows": missing_rows[:20], "invalid_rows": invalid_rows[:20], "unnamed_rows": unnamed_rows[:20], "duplicate_coordinate_pairs": len(coordinates) - len(set(coordinates)), "ra_range_deg": value_range(ra_values), "dec_range_deg": value_range(dec_values)}


def inspect_weight_candidates(rows: List[Dict[str, str]], columns: List[str], excluded: set) -> List[Dict[str, Any]]:
    candidates = []
    for column in columns:
        if column in excluded or not any(hint in normalize_name(column) for hint in WEIGHT_HINTS):
            continue
        review = inspect_numeric_column(rows, column)
        if review["numeric_rows"] == len(rows) and review["negative_rows"] == 0 and review["sum"] > 0.0:
            review["column"] = column
            candidates.append(review)
    return candidates


def inspect_numeric_column(rows: List[Dict[str, str]], column: str) -> Dict[str, Any]:
    values = []
    missing_rows = 0
    invalid_rows = 0
    for row in rows:
        raw = str(row.get(column, "")).strip()
        if not raw:
            missing_rows += 1
            continue
        try:
            value = float(raw)
        except ValueError:
            invalid_rows += 1
            continue
        if not math.isfinite(value):
            invalid_rows += 1
            continue
        values.append(value)
    total = sum(values)
    sum_squares = sum(value * value for value in values)
    return {"numeric_rows": len(values), "missing_rows": missing_rows, "invalid_rows": invalid_rows, "negative_rows": sum(value < 0.0 for value in values), "zero_rows": sum(value == 0.0 for value in values), "min": min(values) if values else None, "max": max(values) if values else None, "sum": total, "max_normalized_fraction": max(values) / total if values and total > 0.0 else None, "effective_source_count": total * total / sum_squares if sum_squares > 0.0 else 0.0}


def value_range(values: List[float]) -> Optional[List[float]]:
    return [min(values), max(values)] if values else None
