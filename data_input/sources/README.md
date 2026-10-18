# Radio-bright AGN source catalogs

These two CSV snapshots contain the same 3386 RFC 2019c sources, in the same
source order, selected with X-band flux density >= 0.15 Jy and
abs(declination) < 87 degrees. The filename's `dec_lt87` denotes this absolute
declination cut. The source selection is already applied; do not apply new cuts
or change membership merely to reproduce an example.

- [Positions-only CSV](radio_bright_agn_rfc2019c_xband_ge_0p15_dec_lt87_3386.csv):
  `source_name`, `ra_deg`, `dec_deg`; coordinates are in degrees and rounded
  to ten decimal places.
- [Enriched CSV](radio_bright_agn_rfc2019c_xband_ge_0p15_dec_lt87_3386_enriched.csv):
  the same sources and order, with full stored coordinate precision,
  `catalog_index`, `raw_line_number`, `ivs_name`, `j2000_name` and `xband_flux_jy`.
  Prefer this table for analysis. `catalog_index` is zero-based; `raw_line_number`
  refers to the original RFC file, not to a row in this CSV.

**X-band flux density**, `xband_flux_jy`, is a radio quantity in Jy. It may be
used as an intrinsic relative source weight when requested; it is not a neutrino
flux or detector acceptance. Uniform weighting is also supported. The
positions-only CSV cannot supply radio-flux weights by itself.

The original catalog is RFC 2019c, created by Leonid Petrov and contributors:
[original catalog and survey references](http://astrogeo.org/vlbi/solutions/rfc_2019c).
These selected snapshots are used in this project's
[arXiv:2103.12813](https://arxiv.org/abs/2103.12813) comparison. Credit the
original RFC observations and survey publications when using these quantities.

Both CSVs are versioned with the code and are available immediately after
cloning; no separate download or PDF precalculation is needed for the catalog.
The IceCube data and probability-density tables still require installation.
Their bytes are preserved from the owner's existing snapshots; SHA-256 values
are recorded in the GitHub copy's `docs/release_file_manifest.json`.

Use the ordinary `create-catalog --catalog <CSV>` workflow. The optional
`--built-in-catalog` reader instead requires the original raw RFC file, which
is not included here; it is not needed to use these CSVs. A full individual scan
requires 3386 fits and can be slow; inspect the table first and start with a
small explicitly selected subset when testing. No analysis or background trials
are started by preparing or inspecting these files.
