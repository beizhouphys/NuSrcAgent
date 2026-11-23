# Requested spectra and response preparation

For a power law, set the spectral index using `--s`. The option takes s in E^(-s).
In a structured request, `stacking.s` is a list of spectral indices,
`stacking.s_mode` selects fitted or fixed, and `analysis.s_bounds`
uses increasing spectral-index order. The optional list `analysis.flux_upper_limit_s`
sets the fixed indices for upper limits. Existing signed-exponent settings still work.

The common spectrum interface supports all current time-integrated analysis
operations. A conventional PL uses existing frozen SEpdfs; when its required
interpolation nodes are absent, the runtime prepares a separate signal response.
An explicit positive command exponent means a rising dN/dE; no sign is reversed.
A supplied non-PL spectrum is treated as a fixed shape. Signal-energy PDFs and
detector acceptance use that same shape, including its specified energy support.

To test a turbulent corona model, generate a neutrino spectrum with the model
code and supply the energy and flux values as a table. Each table specifies
one spectral shape for the likelihood fit.

See the maintained [input and workflow reference](../.agents/skills/nusrcagent/references/requested-spectra.md)
for commands, file format, ETA scope and limitations. A `prepare-spectrum`
command never executes a fit or background trials. After the pilot the agent
reports the returned measured preparation ETA before proceeding. A cached
complete response is verified and used without reconstruction. The ordinary
primary/flux reporting and review gates remain in force.

## Numerical definition and provenance

Construction retains SkyLLH v26 `PDSignalEnergyPDFSet`, its Aeff weighting,
smearing-matrix marginalization and normalization, plus the existing detector
signal-yield calculation. The new `spectrum_response.py` copies the numerical
construction block from the existing offline signal-PDF tool; no independent
likelihood is introduced. Native declination intervals, reconstructed-energy
spacing 0.0025 dex, PL interpolation and the optimizer remain unchanged. The
runtime grid contains the nodes needed by the requested fixed exponent or
explicit fitted interval, with interpolation margins. An arbitrary fixed shape
has identical passive mapper nodes; those nodes are never reported as spectral index.

Each response has a content-derived directory under
`data_output/spectrum_responses/`. Its identity records the supplied spectrum
and interpretation, IRF hashes, numerical implementation and interpolation grid.
Its manifest hashes all prepared tables, including detector-acceptance integrals;
loading and review verify the hashes. The likelihood's detector-yield service
adds the recorded livetimes and interpolates the same profile's acceptance.
SEpdfs must be finite, nonnegative and normalized to within 0.005; dense-energy
interpolation must agree with direct SkyLLH evaluation within L1 error 0.001.
Failed checks block fitting rather than changing a scientific input.

Only completed calculations in the current invocation set an ETA. Pilot ETA is
for the current dataset's remaining construction; later datasets, loading,
saving and LLH fitting are explicitly excluded. Cached intervals do not supply
new timing samples. Do not infer an all-analysis ETA from this preparation rate.

DR1 is still spatial-only. Its existing effective-area integration accepts the
supplied shape; its spatial likelihood and event selection are retained. No new
DR1 energy likelihood is claimed. DR2 time-dependent single-source analysis and
catalog scans use this same fixed-shape interface, including temporal detector
acceptance; time-dependent flux/fluence products remain unavailable. Non-PL shapes
have no fitted PL spectral index. Model-specific shape-parameter fits and per-source
spectra are outside this fixed-shape interface. Existing PL-reference upper
limits are distinct hypotheses; PL-specific primary flux-measurement figures
are not silently applied to a non-PL shape.

## Validation

The owner development checkout checks signed exponents, direct PL/tabulated
spectrum-integral agreement, units, zero-valued spectrum nodes, support rules,
input mutations and artifact hashes. Release verification also executes real
single-source and small catalog scan/stacking requests. These are numerical and
provenance checks, not empirical significance or parameter-coverage calibration.

## DR1 requested-spectrum maximization

Conventional DR1 requests retain the existing NumPy compatibility procedure.
For a newly requested spectrum, single-source maximization copies the original
likelihood code's `minimize(..., x0=0, method="SLSQP", bounds=...)` block;
stacking copies its seeded `minimize` block. This prevents a new acceptance
distribution from leaving the compatibility golden-section search entirely in
an invalid-mixture plateau. The spatial likelihood, event selection and current
runtime n bounds are unchanged (single: [-10, selected event count]; stack:
[0, selected event count]). The selected procedure is recorded in the result.
The untouched baseline `likelihood_v4.py` was inspected, not modified. An earlier
failed development task is retained; its numerical output is not a valid result.

The requested-spectrum DR1 stack evaluates the same log likelihood ratio as
`sum(log1p(n*f_k/N_k*(S/B-1)))` and supplies its analytic derivative with respect to n to
the original bounded minimizer. This avoids cancellation of large background
log likelihoods; it changes no PDF, hypothesis, parameter bound or trial scope.
An independent scalar-score root and direct original-formula comparison check
the returned maximum in the owner tests.
