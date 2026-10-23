# Source coordinates

Under the default analysis settings, the minimum information a researcher
needs to provide is the sky coordinates or a resolvable name of each source.
The natural-language agent may look up a name, recording its source; it asks
when the object identification, coordinate system or angular units are unclear.
The Python wrapper does not include a network name resolver.

The shared input layer accepts ICRS equatorial RA/Dec and Galactic longitude
and latitude (l/b). It converts both to ICRS RA/Dec in degrees before the
existing backend converts degrees to radians. This applies to all currently
supported single-source analyses, catalog-wide single-source analyses and
stacking analyses, for both data samples and likelihood modes. It does not
implement the planned time-dependent analyses.

Degrees and radians are supported for either axis; ICRS RA additionally
supports hourangle, including sexagesimal strings. Specify both angular
units. A numeric range alone never determines a coordinate system or unit.
Equatorial here means ICRS, not an arbitrary equinox: FK4/B1950 or FK5
coordinates require a separately specified and validated transformation.
Input longitude/RA must lie in [0,360) degrees, and latitude/Dec in [-90,90]
degrees, or the equivalent ranges in the chosen units.

## Single source and inline source lists

Existing `--ra-deg`/`--dec-deg` arguments remain explicitly ICRS degrees and
retain their numerical values without a coordinate transformation.
Do not combine them with the generic coordinate arguments.

```bash
.venv/bin/python run_agent_wrap.py create-single \
  --request "Analyze this Galactic position" --name example \
  --longitude 0 --latitude 0 --coordinate-frame galactic \
  --longitude-unit deg --latitude-unit deg

.venv/bin/python run_agent_wrap.py create-single \
  --request "Analyze this equatorial position" --name example \
  --longitude '12:30:00' --latitude=-45:15:00 --coordinate-frame icrs \
  --longitude-unit hourangle --latitude-unit deg

.venv/bin/python run_agent_wrap.py create-catalog \
  --request "Scan and stack these Galactic positions with uniform weights" \
  --source 'first,0,0' --source 'second,180,30' \
  --coordinate-frame galactic --longitude-unit deg --latitude-unit deg \
  --catalog-operation scan_and_stack --weight-mode uniform
```

With coordinate options, repeated `--source` values mean
`name,longitude,latitude` in the specified frame and units. Without those
options, the existing `name,ra_deg,dec_deg` interface retains its degree contract.

## Catalogs

Source names are optional when coordinates are supplied. Without a name
column, generated identifiers `source_0001`, `source_0002`, etc. preserve row order.

Headers such as `ra_deg,dec_deg`, `ra_rad,dec_rad`, `l_deg,b_deg` or
`glon_deg,glat_deg` identify their coordinate system and units. Bare `ra,dec`
or `l,b` identify axes but do not identify angular units; ask before execution.
If both coordinate pairs are present, select the intended pair explicitly.
For arbitrary column names, identify the frame, units and both columns:

```bash
.venv/bin/python run_agent_wrap.py create-catalog \
  --request "Scan and stack my Galactic catalog with uniform weights" \
  --catalog catalog.csv --name-column name \
  --longitude-column x --latitude-column y --coordinate-frame galactic \
  --longitude-unit deg --latitude-unit deg \
  --catalog-operation scan_and_stack --weight-mode uniform
```

The same coordinate options are accepted by `inspect-catalog` and `confirm`.
Legacy explicit `--ra-column`/`--dec-column` options retain their documented
RA/Dec degree contract when generic coordinate options are absent. A header
with an explicit unit takes precedence over that legacy fallback; conflicting
explicit units require clarification. Built-in catalogs already specify
ICRS degrees and cannot be relabelled with another frame.

Missing or ambiguous coordinate information leaves the persistent task in
`AWAITING_CONFIRMATION`, with a question explaining what is missing. Supply
the actual user clarification with, for example:

```bash
.venv/bin/python run_agent_wrap.py confirm --task <task_id> \
  --coordinate-frame galactic --longitude-unit deg --latitude-unit deg
```

The original coordinates, frame, units, column mapping, Astropy version and
converted RA/Dec are retained in task/request and normalized-source provenance.
Source order, membership, intrinsic weights and scientific settings do not
change. Conversion uses
[Astropy coordinate transformations](https://docs.astropy.org/en/stable/coordinates/transforming.html).

## Structured requests

A source mapping may contain `coordinates` with `longitude`, `latitude`,
`frame`, `longitude_unit` and `latitude_unit`, instead of `ra_deg,dec_deg`.
A catalog mapping may contain `coordinates` with `frame`, both units,
`longitude_column` and `latitude_column`. The same converter is used before
normalization. Historical degree-only request files retain their definitions.
