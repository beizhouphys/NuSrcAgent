# Single-source flux measurements

New DR2 time-integrated spatial+energy single-source tasks save the best-fit
primary-spectrum flux normalization. When the primary fit has **TS > 9**, the
report also gives a flux measurement with 68.27% and 95% profile-likelihood
intervals and an updated spectrum figure. TS = 9 does not trigger this output.
This is a reporting criterion; the p-value and significance are reported
separately using the fit's existing Gamma-dependent analytic estimate.

This feature applies to single-source analysis. Catalog scans retain their
current fits and optional fixed-spectrum upper limits; they do not enable the
new measurement profiles or contours. Joint stacks use the separately recorded intensity workflow described below.
DR1 and spatial-only analyses retain their current procedures. Existing tasks retain their recorded settings.

## Flux normalization and intervals

The primary-spectrum normalization is

`dPhi_(nu_mu+anti_nu_mu)/dE = phi1TeV (E / 1 TeV)^(-Gamma)`.

`phi1TeV` is reported in GeV^-1 cm^-2 s^-1; multiply its numeric value by 1000
to express the same differential flux in TeV^-1 cm^-2 s^-1. The 1 TeV pivot
follows the approved reference workflow. For comparison with the separate
fixed-spectrum upper limits, the numeric report also saves
`phi100_hat = phi1TeV_hat * 100^(-Gamma_hat)`.

At each fixed phi1TeV, ns is `phi1TeV * Y1(Gamma)`, where Y1 is the same DR2
effective-area/livetime yield used in the fit. For free Gamma, maximize the
existing likelihood over Gamma at every flux value. For a Gamma interval,
maximize over ns. The flux uncertainty therefore includes normalization-spectrum
correlation; it is not an ns interval rescaled at a fixed best-fit Gamma.
Fixed-Gamma primary fits provide the normalization interval at that spectrum.

One parameter of interest uses two-sided profile thresholds 1 and 3.841458821
for 68.27% and 95%. Joint flux-Gamma regions use two degrees of freedom and
thresholds 2.295748929 and 5.991464547. The existing one-sided 95% upper limits
retain threshold 2.705543454 and their fixed E^-2, E^-2.5 and E^-3 hypotheses.

All new fits record `skyllh_lbfgs_v1`, the original SkyLLH optimizer.
The likelihood, interpolation, PDFs, selection and fit bounds are retained.
No additional Gamma-interval or interpolation-switch maximum search is performed.
Existing task records and numerical results retain their original procedure;
requests naming an unsupported procedure must be recreated explicitly before execution.
Corresponding observed and background-trial fits must use the same procedure.
This change does not launch trials or alter existing ensembles.

A likelihood profile above the recorded maximum, an unavailable crossing,
non-finite evaluation or unconverged fit is an error. Bounds are never widened.
Intervals reaching a recorded bound are marked as truncated. Other substantive
fit, input and artifact checks remain active.


Current regression limitation (2026-10-19): the fitted-Gamma NGC 1068
measurement is rejected because a flux-profile evaluation exceeds the primary
SkyLLH fit by `2 Delta ln L = 0.000660066263105`. No valid measurement intervals
are reported for that task. The original optimizer and the existing consistency
tolerance are retained. The fixed-Gamma NGC 1068 measurement and the two-source
fitted-Gamma scan plus stacking regressions pass review; this does not establish
that every free-Gamma flux measurement will succeed.

## Spectrum and files

The spectrum figure retains the three fixed-spectrum upper limits, NGC 1068
and both diffuse benchmarks with published bands. For TS > 9, it adds the
primary best-fit spectrum and the sampled envelope of the 68.27% joint
flux-Gamma region. Fixed-Gamma shading uses its one-dimensional normalization
interval. Joint regions also have their own contour figure. PNG, vector PDF
and editable SVG are written under `figures/runs/<run>/source_00001/`.

The source curves are complete power-law hypotheses over 1 TeV–10 PeV;
that display range is not a measured sensitive range. The region envelope
is not an independent measurement in each energy bin or a simultaneous
confidence band. Common flux units and the 4*pi sr diffuse integration
follow [the reference-spectrum definitions](flux_upper_limits.md).

`flux_measurement.csv` saves the estimate even below the reporting
threshold. For TS > 9, `flux_measurement_profiles.csv` and, for free Gamma,
`flux_measurement_contours.csv` preserve the evaluated profile and contour
points. The numeric report and plot provenance retain method settings and
hashes. Review checks the TS gate, primary detector yield, confidence thresholds,
table contents, plotted spectrum, reference inputs and output hashes.

Default user reports and captions focus on fit results and statistical intervals.
The three methodological details identified in the owner's 2026-10-19 reporting
policy remain available in numerical metadata and are discussed when requested;
they alone do not generate warnings or prevent COMPLETED. This policy does not
suppress genuine fit, input or artifact failures.

## Joint-stack measurements

The same profile construction now supports a joint stack using the sum of the
intrinsic-weighted detector yields. New stack tasks report the primary fit first,
then calculate measured catalog intensity only for strict TS > 9, together with
the three default fixed-spectrum limits. Catalog intensity is total flux divided
by 4*pi sr; its figure contains only the two diffuse benchmarks. See
[stacking flux definitions](stacking_flux.md).

New standalone DR2 spatial+energy single-source tasks record linear_v1 for the
signal-energy Gamma interpolation. Primary and flux calculations share it;
continuation with a different recorded method is rejected. See
[single-source interpolation](single_source_linear_interpolation.md).

## Line styles

In single-source and joint-stack flux/intensity figures, current-analysis
upper limits, measured spectra and profile-contour boundaries use solid lines.
All published reference spectra (IceCube or other authors) use dashed lines.
Colors, markers, uncertainty shading and flux/intensity units are unchanged.
