# Example catalog

`catalog_sources_example.csv` contains TXS 0506+056, PKS 1502+106 and 3C 279
for learning how to run a catalog scan and stack. It is not a complete or
scientifically selected source population. A CSV is an ordinary text table
with columns separated by commas; you can inspect it with a text editor or
spreadsheet program.

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
The three-row scan produces three separate single-source fits. The stack is
one joint fit of the assumed combined source emission, not the sum of those
individual fitted TS values. See the [catalog guide](../../docs/dr2_catalog_workflow.md)
for the distinction and the significance limitations.

The optional built-in RFC catalog is not included in this release copy. These
examples have no dependency on a private catalog or neighboring project.
