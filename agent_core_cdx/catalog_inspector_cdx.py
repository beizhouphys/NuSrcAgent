from __future__ import annotations # cdx

import csv # cdx
import math # cdx
from pathlib import Path # cdx
from typing import Any, Dict, List, Optional # cdx


NAME_ALIASES = ["source_name", "name", "source", "object", "ivs_name", "j2000_name"] # cdx
RA_ALIASES = ["ra_deg", "ra", "raj2000", "ra_j2000", "right_ascension"] # cdx
DEC_ALIASES = ["dec_deg", "dec", "dej2000", "dec_j2000", "declination"] # cdx
WEIGHT_HINTS = ["weight", "flux", "luminosity", "lumin", "radio", "xband"] # cdx


def inspect_catalog(path_value: str, name_column: Optional[str] = None, ra_column: Optional[str] = None, dec_column: Optional[str] = None, weight_column: Optional[str] = None) -> Dict[str, Any]: # cdx
    path = Path(path_value).expanduser().resolve() # cdx
    result: Dict[str, Any] = {"tool": "inspect_catalog", "catalog": str(path), "status": "pass", "errors": [], "warnings": [], "questions": []} # cdx
    if not path.exists(): # cdx
        result["status"] = "fail" # cdx
        result["errors"].append("catalog file does not exist") # cdx
        return result # cdx
    if path.suffix.lower() not in {".csv", ".tsv", ".tab"}: # cdx
        result["status"] = "fail" # cdx
        result["errors"].append("catalog must be a headered CSV or TSV file for the current pipeline") # cdx
        return result # cdx
    rows, columns = read_catalog(path) # cdx
    result["row_count"] = len(rows) # cdx
    result["columns"] = columns # cdx
    if not rows: # cdx
        result["status"] = "fail" # cdx
        result["errors"].append("catalog contains no data rows") # cdx
        return result # cdx
    inferred_name = name_column or infer_column(columns, NAME_ALIASES) # cdx
    inferred_ra = ra_column or infer_column(columns, RA_ALIASES) # cdx
    inferred_dec = dec_column or infer_column(columns, DEC_ALIASES) # cdx
    result["inferred_columns"] = {"name": inferred_name, "ra_deg": inferred_ra, "dec_deg": inferred_dec, "weight": weight_column} # cdx
    for label, column in [("name", inferred_name), ("ra_deg", inferred_ra), ("dec_deg", inferred_dec)]: # cdx
        if column is None: # cdx
            result["errors"].append("could not infer the %s column" % label) # cdx
        elif column not in columns: # cdx
            result["errors"].append("specified %s column is missing: %s" % (label, column)) # cdx
    if result["errors"]: # cdx
        result["status"] = "fail" # cdx
        result["questions"].append("Which columns contain source name, RA in degrees, and Dec in degrees?") # cdx
        return result # cdx
    coordinate_review = inspect_coordinates(rows, inferred_name, inferred_ra, inferred_dec) # cdx
    result["coordinate_review"] = coordinate_review # cdx
    if coordinate_review["invalid_rows"] or coordinate_review["missing_rows"] or coordinate_review["duplicate_coordinate_pairs"]: # cdx
        result["warnings"].append("catalog coordinates require review") # cdx
    candidates = inspect_weight_candidates(rows, columns, {inferred_name, inferred_ra, inferred_dec}) # cdx
    result["weight_candidates"] = candidates # cdx
    if weight_column is not None: # cdx
        if weight_column not in columns: # cdx
            result["errors"].append("specified weight column is missing: %s" % weight_column) # cdx
        else: # cdx
            result["inferred_columns"]["weight"] = weight_column # cdx
            result["selected_weight_review"] = inspect_numeric_column(rows, weight_column) # cdx
    elif candidates: # cdx
        result["questions"].append("Use uniform weights or one of these catalog columns: %s?" % ", ".join(item["column"] for item in candidates)) # cdx
    else: # cdx
        result["questions"].append("Use uniform weights, or provide manual weights?") # cdx
    if result["errors"]: # cdx
        result["status"] = "fail" # cdx
    elif result["warnings"] or result["questions"]: # cdx
        result["status"] = "warning" # cdx
    return result # cdx


def read_catalog(path: Path) -> tuple[List[Dict[str, str]], List[str]]: # cdx
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else "," # cdx
    with path.open("r", encoding="utf-8", newline="") as handle: # cdx
        reader = csv.DictReader(handle, delimiter=delimiter) # cdx
        return [dict(row) for row in reader], list(reader.fieldnames or []) # cdx


def infer_column(columns: List[str], aliases: List[str]) -> Optional[str]: # cdx
    normalized = {normalize_name(column): column for column in columns} # cdx
    for alias in aliases: # cdx
        if normalize_name(alias) in normalized: # cdx
            return normalized[normalize_name(alias)] # cdx
    return None # cdx


def normalize_name(value: str) -> str: # cdx
    return "".join(character.lower() for character in value if character.isalnum()) # cdx


def inspect_coordinates(rows: List[Dict[str, str]], name_column: str, ra_column: str, dec_column: str) -> Dict[str, Any]: # cdx
    missing_rows: List[int] = [] # cdx
    invalid_rows: List[int] = [] # cdx
    unnamed_rows: List[int] = [] # cdx
    coordinates = [] # cdx
    ra_values = [] # cdx
    dec_values = [] # cdx
    for index, row in enumerate(rows, start=1): # cdx
        if not str(row.get(name_column, "")).strip(): # cdx
            unnamed_rows.append(index) # cdx
        if not str(row.get(ra_column, "")).strip() or not str(row.get(dec_column, "")).strip(): # cdx
            missing_rows.append(index) # cdx
            continue # cdx
        try: # cdx
            ra_value = float(row[ra_column]) # cdx
            dec_value = float(row[dec_column]) # cdx
        except (TypeError, ValueError): # cdx
            invalid_rows.append(index) # cdx
            continue # cdx
        if not math.isfinite(ra_value) or not math.isfinite(dec_value) or not 0.0 <= ra_value < 360.0 or not -90.0 <= dec_value <= 90.0: # cdx
            invalid_rows.append(index) # cdx
            continue # cdx
        coordinates.append((round(ra_value, 10), round(dec_value, 10))) # cdx
        ra_values.append(ra_value) # cdx
        dec_values.append(dec_value) # cdx
    return {"missing_rows": missing_rows[:20], "invalid_rows": invalid_rows[:20], "unnamed_rows": unnamed_rows[:20], "duplicate_coordinate_pairs": len(coordinates) - len(set(coordinates)), "ra_range_deg": value_range(ra_values), "dec_range_deg": value_range(dec_values)} # cdx


def inspect_weight_candidates(rows: List[Dict[str, str]], columns: List[str], excluded: set) -> List[Dict[str, Any]]: # cdx
    candidates = [] # cdx
    for column in columns: # cdx
        if column in excluded or not any(hint in normalize_name(column) for hint in WEIGHT_HINTS): # cdx
            continue # cdx
        review = inspect_numeric_column(rows, column) # cdx
        if review["numeric_rows"] == len(rows) and review["negative_rows"] == 0 and review["sum"] > 0.0: # cdx
            review["column"] = column # cdx
            candidates.append(review) # cdx
    return candidates # cdx


def inspect_numeric_column(rows: List[Dict[str, str]], column: str) -> Dict[str, Any]: # cdx
    values = [] # cdx
    missing_rows = 0 # cdx
    invalid_rows = 0 # cdx
    for row in rows: # cdx
        raw = str(row.get(column, "")).strip() # cdx
        if not raw: # cdx
            missing_rows += 1 # cdx
            continue # cdx
        try: # cdx
            value = float(raw) # cdx
        except ValueError: # cdx
            invalid_rows += 1 # cdx
            continue # cdx
        if not math.isfinite(value): # cdx
            invalid_rows += 1 # cdx
            continue # cdx
        values.append(value) # cdx
    total = sum(values) # cdx
    sum_squares = sum(value * value for value in values) # cdx
    return {"numeric_rows": len(values), "missing_rows": missing_rows, "invalid_rows": invalid_rows, "negative_rows": sum(value < 0.0 for value in values), "zero_rows": sum(value == 0.0 for value in values), "min": min(values) if values else None, "max": max(values) if values else None, "sum": total, "max_normalized_fraction": max(values) / total if values and total > 0.0 else None, "effective_source_count": total * total / sum_squares if sum_squares > 0.0 else 0.0} # cdx


def value_range(values: List[float]) -> Optional[List[float]]: # cdx
    return [min(values), max(values)] if values else None # cdx
