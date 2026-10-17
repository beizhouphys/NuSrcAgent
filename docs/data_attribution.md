# IceCube input attribution

The project provides copies of its fixed analysis inputs as GitHub Release
downloads. `bash install.sh` retrieves them; users do not need to select files
or download them manually from IceCube. The original sources below identify
the data authors and scientific references, not additional installation steps.
Please distinguish credit for the IceCube observations from credit for this
analysis software and its derived PDF tables.

## IceTracks-DR2

IceCube Collaboration, *IceCube Second Track Data Release IceTracks-DR2: Data
from 2008–2022 for Neutrino Source Searches*.

- Dataset DOI: https://doi.org/10.7910/DVN/MMIIZA
- Official description: https://icecube.wisc.edu/data-releases/2026/05/icecube-second-track-data-release-icetracks-dr2-data-from-2008-2022-for-neutrino-source-searches/
- Companion publication: https://arxiv.org/abs/2605.19040
- The official Dataverse metadata inspected on 2026-10-16 identifies CC0 1.0
  (https://creativecommons.org/publicdomain/zero/1.0/) and dataset version 3.1.
  That is the inspected upstream metadata version, not a claim that this project's
  previously frozen local snapshot was replaced or equals every upstream version.

The bundle contains the exact 37 runtime raw files: original DR2 README, 14 event
CSVs, 14 uptime CSVs, four effective-area CSVs and four smearing CSVs. The original
README and scientific attribution are retained. Per-file SHA-256 values define
the project snapshot. No official illustration files or unrelated analyses are needed.

## DR1 supported inputs

IceCube Collaboration, *IceCube Data for Neutrino Point-Source Searches:
Years 2008–2018*, https://doi.org/10.7910/DVN/VKL316.
Official Dataverse metadata inspected on 2026-10-16 identifies CC0 1.0 and
version 2.0. The optional project bundle contains the existing supported subset,
including historical pooled/prepared products and the five associated background
tables. These prepared products are identified as project inputs, not new official
IceCube data releases; they are not interchangeable with DR2 events or v3 PDFs.

## Project-derived PDFs

Frozen v3 background models/tables and frozen SEpdf tables are derived inputs
with their own provenance and hashes. They are distributed separately from raw
IceCube inputs. CC0 attribution of the raw data does not itself grant a license
for NuSrcAgent software. Project license/authorship/citation metadata remains
part of final release preparation.
