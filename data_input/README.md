# External inputs

Run `bash install.sh` from the project's top-level folder to download the
matching IceCube data and precomputed probability-density tables. No manual
placement or PDF calculation is needed. The large files are downloaded
separately rather than included in the Git clone.

Events, observation periods and detector response files are placed here;
precomputed PDFs are placed under `data_output/` at the paths expected by the
likelihood. Do not edit these fixed input files to fix an installation error.
See [installation](../docs/input_installation.md) and
[data descriptions](../docs/data_and_environment.md) for the DR1/DR2 distinction.
