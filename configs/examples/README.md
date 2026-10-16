# Example catalog

`catalog_sources_example.csv` is a three-source interface/reproducibility
example, not a complete or scientifically selected source population.

| Column | Meaning |
| --- | --- |
| `name` | Source label, preserved in output tables |
| `ra_deg` | Right ascension in degrees, required range `[0, 360)` |
| `dec_deg` | Declination in degrees, required range `[-90, 90]` |
| `radio_weight` | Illustrative relative proxy; not a measured flux or calibrated catalog quantity |

The [quickstart](../../docs/quickstart.md) explicitly uses uniform intrinsic
weights and ignores `radio_weight`. Do not infer radio-flux measurements or
physical units from its illustrative numbers. Detector acceptance is applied
separately by the backend.

For your own CSV, specify the name/coordinate columns. State whether stacking
uses uniform weights or a particular physical column. Do not choose a column
just because it is numeric; ambiguous quantities require clarification. The
loader normalizes relative weights and records the selection and input identity.
Scan-only performs independent fits and does not need stacking weights.

The optional built-in RFC catalog is not included in this release copy. These
examples have no dependency on a private catalog or neighboring project.
