# Requested spectra

`--gamma` is the signed exponent in `dN/dE proportional to (E/E0)^gamma`.
Bare natural-language `Gamma=+2.5` remains ambiguous unless a formula defines
its convention. An explicit E^+2.5, E^0, E^-0.2 or E^-8 is accepted unchanged.
A supplied exponent defaults to fixed mode. Fitted PLs keep the default bounds
unless the user specifies another interval with `--gamma-bounds EXP_MIN EXP_MAX`;
do not widen a search automatically because a seed lies outside the default.

For a fixed non-PL spectrum (including realistic modeling), supply a text file
with two numeric columns, energy and value, plus all three interpretation options:

```bash
.venv/bin/python run_agent_wrap.py create-single --request "Use the supplied model" --name source --ra-deg 40 --dec-deg 20 --spectrum-file model.txt --spectrum-kind dnde --spectrum-energy-unit GeV --spectrum-outside-support zero
```

The same options work on `create-catalog` with `scan`, `stack` or `scan_and_stack`.
`--spectrum-kind` is `dnde`, `ednde` or `e2dnde`; energy unit is `GeV` or `TeV`.
`--spectrum-outside-support` is `zero` or `extrapolate`. Infer these choices only
when the supplied model/metadata specifies them; otherwise ask because they
change the physical model. Arbitrary executable expressions are not evaluated.
A modeled analytic spectrum can be supplied as a sufficiently resolved table;
record the model and sampled energy range. Do not replace it with a PL fit.

Positive nodes use log-log interpolation. Segments touching a zero use linear
interpolation in energy; values must be finite/nonnegative, with positive unique
energies and nonzero emission. Extrapolation requires positive nodes. The
normalization of the supplied table cancels in the shape; ns is fitted. A
common shape applies to the selected sources; distinct per-source spectra or
free parameters of a non-PL model are not implemented and require a separate
explicit scientific extension. Existing PL-reference flux upper limits remain
separate hypotheses. The current primary-spectrum flux-measurement figures are
PL-specific and are not relabeled as measurements of a supplied non-PL shape.

```bash
.venv/bin/python run_agent_wrap.py prepare-spectrum --task <id> --estimate-only
.venv/bin/python run_agent_wrap.py prepare-spectrum --task <id>
.venv/bin/python run_agent_wrap.py run --task <id>
```

Announce the need for preparation before the first command. Quote the measured
ETA from the first command before the remaining preparation/fit. It covers the
current dataset only; other detector configurations, loading, saving and fits
remain separate. Restored intervals do not count as newly measured units.
The runtime uses SkyLLH's existing signal-energy construction and acceptance
integration, checks normalization/nonnegativity and interpolation against direct
PDF evaluation, then loads the prepared tables for fitting. All intervals use
the same supplied spectrum and its explicit support convention. Frozen PDFs are
untouched; derived responses are cached under `data_output/spectrum_responses/`
with IRF, spectrum and implementation hashes. Treat changed inputs or failed
checks as blocking, not as permission to change the spectrum. Prepare a response
on one host; do not write the same Dropbox cache directory from multiple hosts.

DR1 remains spatial-only and uses its original acceptance integration with the
requested shape; no energy-PDF term is introduced. DR2 time-dependent
single-source analysis and catalog scans use the same spectrum response with
temporal acceptance; time-dependent stacking and flux/fluence remain pending. Any corresponding trials must retain the same
spectrum/response and observed fit procedure; this feature never starts trials.
