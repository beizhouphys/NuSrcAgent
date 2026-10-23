"""Convert explicitly identified sky coordinates to the backend's ICRS degrees."""
from __future__ import annotations

import math
import re


class CoordinateError(ValueError):
    """Invalid or ambiguous coordinates; never guess a frame or angular unit."""


def coordinate_spec(frame=None, longitude_unit=None, latitude_unit=None, **extra):
    aliases = {"icrs": "icrs", "equatorial": "icrs", "radec": "icrs", "galactic": "galactic"}
    units = {"deg": "deg", "degree": "deg", "degrees": "deg", "rad": "rad",
             "radian": "rad", "radians": "rad", "hourangle": "hourangle", "hour": "hourangle"}
    if frame is None:
        raise CoordinateError("Which coordinate system is intended: ICRS RA/Dec or Galactic l/b?")
    frame = aliases.get(str(frame).lower())
    if frame is None:
        raise CoordinateError("Unsupported coordinate frame; specify ICRS RA/Dec or Galactic l/b (not an unspecified equinox).")
    if longitude_unit is None or latitude_unit is None:
        raise CoordinateError("Which angular units apply to longitude/RA and latitude/Dec? Specify both; do not infer units from numeric ranges.")
    lon_unit, lat_unit = units.get(str(longitude_unit).lower()), units.get(str(latitude_unit).lower())
    if lon_unit is None or lat_unit not in {"deg", "rad"}:
        raise CoordinateError("Use deg or rad for either angle, or hourangle for ICRS RA only.")
    if lon_unit == "hourangle" and frame != "icrs":
        raise CoordinateError("Hourangle is supported for ICRS RA only, not Galactic longitude.")
    return dict(extra, frame=frame, longitude_unit=lon_unit, latitude_unit=lat_unit)


def convert_coordinates(longitude, latitude, **spec):
    spec = coordinate_spec(**spec)
    if longitude is None or latitude is None:
        raise CoordinateError("Provide both sky coordinate values before execution.")
    from astropy import __version__ as astropy_version
    from astropy import units as u
    from astropy.coordinates import Angle, SkyCoord
    try:
        angles = []
        for value, unit in ((longitude, spec["longitude_unit"]), (latitude, spec["latitude_unit"])):
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                numeric = value
            if isinstance(numeric, str) and re.search(r"[a-zA-Z°]", numeric):
                if Angle(value).unit != u.Unit(unit):
                    raise CoordinateError("An embedded angular unit conflicts with the specified unit; clarify the intended units.")
            angles.append(Angle(numeric, unit=u.Unit(unit)))
        lon, lat = angles
        lon_deg, lat_deg = float(lon.degree), float(lat.degree)
    except (TypeError, ValueError, u.UnitsError) as exc:
        raise CoordinateError("Cannot parse the supplied sky coordinates with the specified units: %s" % exc) from exc
    if not math.isfinite(lon_deg):
        raise CoordinateError("Coordinate longitude/RA must be finite.")
    if not math.isfinite(lat_deg) or not -90 <= lat_deg <= 90:
        raise CoordinateError("Coordinate latitude/Dec must be finite and in [-90, 90] degrees (or equivalent units).")
    longitude_period = {"deg": 360., "rad": math.tau, "hourangle": 24.}[spec["longitude_unit"]]
    longitude_native = float(lon.to_value(u.Unit(spec["longitude_unit"])))
    wrapped = not 0 <= longitude_native < longitude_period
    if wrapped:
        lon = Angle(longitude_native % longitude_period, unit=u.Unit(spec["longitude_unit"]))
        lon_deg = float(lon.degree)
    lon_deg %= 360
    if spec["frame"] == "icrs":
        # Preserve explicitly supplied degree RA/Dec without a round trip.
        ra_deg, dec_deg = lon_deg, lat_deg
    else:
        icrs = SkyCoord(l=lon, b=lat, frame="galactic").icrs
        ra_deg, dec_deg = float(icrs.ra.degree), float(icrs.dec.degree)
    provenance = dict(spec, longitude=longitude, latitude=latitude,
                      output_frame="icrs", ra_deg=ra_deg, dec_deg=dec_deg,
                      method="astropy.coordinates", astropy_version=astropy_version)
    if wrapped:
        provenance["longitude_wrapped_deg"] = lon_deg
    return dict(ra_deg=ra_deg, dec_deg=dec_deg, coordinate_input=provenance)


def canonical_source(source, spec=None):
    """Return canonical coordinates, retaining original user values for review."""
    result = dict(source)
    coordinates = source.get("coordinates")
    if coordinates is not None:
        settings = dict(coordinates)
        longitude, latitude = settings.pop("longitude", None), settings.pop("latitude", None)
        settings.update(spec or {})
        result.update(convert_coordinates(longitude, latitude, **settings))
    elif spec:
        raise CoordinateError("Generic coordinate settings require longitude/latitude values; do not combine them with --ra-deg/--dec-deg.")
    return result


def column_unit(column):
    name = re.sub(r"[^a-z0-9]", "", str(column).lower())
    for ending, unit in (("deg", "deg"), ("rad", "rad"), ("hourangle", "hourangle"), ("hours", "hourangle")):
        if name.endswith(ending):
            return unit
    return None


def resolve_catalog_coordinates(columns, ra_column=None, dec_column=None, spec=None):
    """Recognize named axes, but require units unless the headers state them."""
    spec = dict(spec or {})
    def key(value):
        return re.sub(r"[^a-z0-9]", "", str(value).lower())
    lookup = {key(c): c for c in columns}
    def find(names):
        return next((lookup[key(n)] for n in names if key(n) in lookup), None)
    ra = find(["ra_deg", "ra_rad", "ra_hourangle", "ra_hours", "ra", "raj2000", "ra_j2000", "right_ascension"])
    dec = find(["dec_deg", "dec_rad", "dec", "dej2000", "dec_j2000", "declination"])
    glon = find(["l_deg", "l_rad", "glon_deg", "glon_rad", "galactic_longitude_deg", "glon", "l", "galactic_longitude"])
    glat = find(["b_deg", "b_rad", "glat_deg", "glat_rad", "galactic_latitude_deg", "glat", "b", "galactic_latitude"])
    frame = spec.get("frame")
    lon_column = spec.get("longitude_column") or ra_column
    lat_column = spec.get("latitude_column") or dec_column
    if frame is None:
        if lon_column or lat_column:
            if (lon_column in {ra, None} and lat_column in {dec, None}) and (ra or dec):
                frame = "icrs"
            elif (lon_column in {glon, None} and lat_column in {glat, None}) and (glon or glat):
                frame = "galactic"
        elif ra and dec and glon and glat:
            raise CoordinateError("The catalog has both RA/Dec and Galactic l/b; which coordinate pair should be used?")
        elif ra and dec:
            frame = "icrs"
        elif glon and glat:
            frame = "galactic"
    if frame is None:
        raise CoordinateError("Identify the coordinate frame and longitude/latitude catalog columns before execution.")
    if str(frame).lower() in {"icrs", "equatorial", "radec"}:
        lon_column, lat_column = lon_column or ra, lat_column or dec
    else:
        lon_column, lat_column = lon_column or glon, lat_column or glat
    if lon_column not in columns or lat_column not in columns:
        raise CoordinateError("Identify existing longitude/RA and latitude/Dec catalog columns.")
    if (str(frame).lower() == "galactic" and ((ra and lon_column == ra) or (dec and lat_column == dec))) or (str(frame).lower() in {"icrs", "equatorial", "radec"} and ((glon and lon_column == glon) or (glat and lat_column == glat))):
        raise CoordinateError("Coordinate frame conflicts with the catalog axis labels; clarify the intended coordinate pair.")
    # Old explicit --ra-column/--dec-column retain their documented degree contract.
    legacy_degrees = bool(ra_column and dec_column and not spec)
    lon_unit = spec.get("longitude_unit") or column_unit(lon_column) or ("deg" if legacy_degrees else None)
    lat_unit = spec.get("latitude_unit") or column_unit(lat_column) or ("deg" if legacy_degrees else None)
    settings = coordinate_spec(frame, lon_unit, lat_unit, longitude_column=lon_column, latitude_column=lat_column)
    if column_unit(lon_column) and spec.get("longitude_unit") and column_unit(lon_column) != settings["longitude_unit"]:
        raise CoordinateError("Longitude unit conflicts with its catalog header; clarify the intended units.")
    if column_unit(lat_column) and spec.get("latitude_unit") and column_unit(lat_column) != settings["latitude_unit"]:
        raise CoordinateError("Latitude unit conflicts with its catalog header; clarify the intended units.")
    return settings


def catalog_source(row, name, spec):
    return dict(name=name, **convert_coordinates(row[spec["longitude_column"]], row[spec["latitude_column"]], **spec))
