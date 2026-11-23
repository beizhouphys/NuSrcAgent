# Joint-stack flux limits, intensity measurements and two-stage reporting

New DR2 time-integrated spatial+energy joint-stack tasks report results in two
stages. The primary fit keeps its requested n and s hypotheses, selected sources,
intrinsic weights, event selection, frozen PDFs, bounds and original optimizer.
This workflow applies to `stack` and the joint stack in `scan_and_stack`.
Individual-source scan limits retain their separate opt-in setting. DR1 and
spatial-only tasks retain their existing procedures. Historical tasks are not
silently converted to this workflow.

## Stage 1: maximize and report the likelihood

Create the task through the public wrapper and require `READY`. Run it normally:

```bash
.venv/bin/python run_agent_wrap.py run --task <task_id>
```

The primary result is saved and independently reviewed before any joint-stack
flux profiles or companion fixed-spectrum fits. A passing primary stage returns
`AWAITING_FLUX`. The wrapper's `stacking_stages.primary` contains n, s, TS,
local analytic p-value, one-sided significance, method labels and review status.
The Agent must report these values in a final answer chat bubble, ask whether
the user wants flux upper limits/measurements and figures, and end that turn.
A commentary progress message does not replace this formal first-stage result.
Warnings remain visible and failed primary review blocks valid reporting.
`AWAITING_FLUX` means the requested analysis still has flux work to complete.

## Stage 2: limits, measurements and figures

Continue the same task only after the user replies to the primary final answer:

```bash
.venv/bin/python run_agent_wrap.py run --task <task_id> --stage flux --flux-user-reply "<actual user reply>"
```

The Agent waits at AWAITING_FLUX. After an explicit reply such as "continue" or
"继续", it runs stage 2 in that later turn and sends a separate final answer.
The CLI rejects missing/blank replies before execution and stores the actual
reply on the flux attempt. Do not invent a reply or infer one from the initial
analysis request. Stage 2 checks the original request
hash, sealed primary artifacts, runtime packages, code and scientific-input
hashes before reconstructing the same likelihood. It evaluates the saved primary
parameters to verify TS and does not repeat primary maximization. Primary ns,
spectral index, TS, p-value, significance and optimizer records stay in place.

The default companions are three separate fixed-index fits at s=2, 2.5 and 3,
each with a one-sided 95% profile-likelihood upper limit. Their upper crossings
satisfy `2[ln L(n_hat, s)-ln L(n_upper, s)] = 2.705543454095404` inside
the recorded bounds. `--no-flux-upper-limits` at task creation omits these
companions; the strict measurement gate remains recorded independently.

The default upper-limit spectrum figures (PNG, PDF and SVG) are generated and
reported regardless of primary TS, after successful review. For TS <= 9 they
contain the three fixed-spectrum upper limits and the two diffuse references,
without a measured spectrum or measurement shading. The TS > 9 condition applies
to measurement products, not to upper-limit figures.

Only primary TS > 9 produces a measured primary-spectrum intensity, 68.27%/95%
profile intervals, spectral shading and, for fitted spectral index, joint contours.
TS=9 does not trigger measurement reporting. At each fixed total-flux
normalization, free-index profiling includes its spectral index-dependent detector yield;
it does not freeze the primary spectral index to rescale an interval for n. The existing
maximum-consistency guard, thresholds and bound-truncation checks remain active.
A failed flux stage cannot invalidate the separately preserved primary artifacts,
but its flux numbers must not be reported as valid. No background trials are
started by this workflow.

## Catalog total flux and intensity

The normalized intrinsic model weights satisfy sum_j w_model_j=1. For a common
power law, source j has

`phi_j(E) = w_model_j * phi0_total * (E/E0)^(-s)`.

The expected count is

`n = phi0_total * sum_k sum_j w_model_j * Y_j^k(s, E0)`.

Here Y is the same effective-area/livetime detector yield used in the likelihood.
The acceptance factor is applied once. Both uniform and catalog-column weighting
therefore define a catalog-total flux, rather than an unweighted sum of detector
yields or a flux for one representative source. A duplicated co-located source
with split intrinsic weight leaves the total-flux conversion unchanged.

The displayed quantity is the full-sky average

`dI_catalog/dE = (sum_j phi_j(E))/(4*pi sr)`.

This is an explicit full-sky averaging convention for the selected catalog; it
does not assign isotropic emission or a local solid-angle aperture to each point
source. Differential intensity is in GeV^-1 cm^-2 s^-1 sr^-1; E^2 dI/dE is in
GeV cm^-2 s^-1 sr^-1. The flavor is nu_mu+anti_nu_mu, with no factor of three.
Limits use the 100 TeV pivot; the primary measurement uses 1 TeV and also stores
its 100 TeV normalization. Numeric artifacts retain total flux and explicit
intensity fields, with the exact 4*pi sr conversion recorded.

## Figures, artifacts and review

The joint-stack spectrum has one intensity axis. Current-analysis upper limits
and measured spectra use solid lines; all published reference spectra use dashed
lines. Computed intensity-spectral index contour boundaries also use solid lines. Catalog limits, measured
spectra and their bands are total flux divided by exactly 4*pi sr. The two
published diffuse astrophysical spectra and bands remain in their original
per-steradian intensity units. Only the 9.5-year tracks and 10.3-year starting-track
benchmarks appear; NGC 1068 is excluded from the joint-stack figure. Preserve
the starting-track band's confidence-level qualification. The single-source
figure conventions remain separate.

The spectrum curves describe complete power-law hypotheses over 1 TeV–10 PeV;
that display range is not a measured sensitive range or independent energy-bin
limits. Measurement shading retains the existing confidence-region meaning.
Joint contours display intensity normalization versus spectral index. PNG, vector PDF
and editable SVG are generated under `figures/runs/<run>/stack/`.

Each stage has its own run directory and review. The task record retains both
through `stacking_stages` and the primary/flux run-directory references. Stage 2
writes `flux_upper_limits.csv`, `upper_limit_profiles.csv`,
`spectrum_curves.csv`, `flux_plot_provenance.json`, and applicable
measurement/profile/contour tables. `stacking_stages.flux` provides a compact chat
summary and figure/table paths only after successful review. Review checks each
fixed fit, detector-yield conversion, strict TS gate, statistical intervals,
intensity scaling, reference identities, tables and output hashes.

The exact spatial-PDF and observed-energy interpolation caches remain enabled
where applicable. A new CLI process rebuilds its own fit-local caches; loaded
input templates and validated PDF tables can be reused within the companion-fit
suite. Keep the requested CPU budget for both stages. Source membership, weights
and optimizer settings must never be changed to repair a failed profile.
