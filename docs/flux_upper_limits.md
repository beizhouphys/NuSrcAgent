# Point-source flux upper limits and reference spectra

New DR2 spatial+energy single-source tasks report the requested primary fit and,
by default, three additional fits at fixed spectra E^-2, E^-2.5 and E^-3. Each
additional fit gives a one-sided 95% flux upper limit. The positive index Gamma
in E^-Gamma corresponds to wrapper exponents -2, -2.5 and -3. These hypotheses
are separate from a freely fitted Gamma in the primary analysis.

Use `--no-flux-upper-limits` with `create-single` to omit these additional fits
and figures. Catalog scans omit them by default; add `--flux-upper-limits` to
`create-catalog --catalog-operation scan` or `scan_and_stack` to calculate limits
and generate one figure for each catalog source. This can take substantial time
and produce many figures for a large catalog. The joint stacking result has its
own likelihood and is unaffected by the individual-source limit option.
Spatial-only and DR1 analyses do not use this new calculation. Existing task
records retain their original settings; new defaults are recorded at creation.

## Statistical and flux definitions

At each fixed Gamma the existing likelihood is maximized over nonnegative ns.
The upper crossing satisfies

`2 [ln L(ns_hat, Gamma) - ln L(ns_upper, Gamma)] = Phi^-1(0.95)^2 = 2.705543454095404`.

The code brackets this crossing above ns_hat inside the recorded fit bounds.
An absent crossing, non-finite likelihood, unconverged fit or inconsistency with
the fixed-Gamma maximum is a failure, never a substituted flux limit. Profiles
save the evaluated points. A zero-signal best fit is explicitly marked in review.

The reported point-source flux is

`dPhi_(nu_mu+anti_nu_mu)/dE = phi100 (E / 100 TeV)^(-Gamma)`.

`phi100` has units GeV^-1 cm^-2 s^-1. The detector yield uses the same public
DR2 effective areas, livetimes and declination interpolation as the fit. With
the fit's unit-normalization yield Y1 at 1 TeV, the yield for phi100 is
`Y100 = Y1 * 100^Gamma`, and `phi100_upper = ns_upper / Y100`.
At 100 TeV, the energy flux is `1e10 * phi100_upper` in GeV cm^-2 s^-1, or
`1e7 * phi100_upper` in TeV cm^-2 s^-1. There is no factor of three or sr^-1.

These are preliminary asymptotic limits. Actual 95% coverage, especially near
the physical ns=0 boundary, has not been established. Detector and PDF systematic
uncertainties are excluded. The three hypotheses do not establish a joint
confidence band or a calibrated test across spectral hypotheses. No background
trials are added by this feature. Existing declination windows and frozen PDFs
are used for every companion fit, while complete loaded data and PDF tables
are reused between fits.

## Figure and files

The single-panel logarithmic spectrum figure follows the owner-approved final
figure in the `Single` chat: red dashed Gamma=2, blue solid Gamma=2.5 and green
dash-dot Gamma=3 upper-limit curves with downward arrows; NGC 1068 in black;
two diffuse benchmarks in purple and cyan with their published uncertainty bands.
Source curves display complete power-law hypotheses from 1 TeV to 10 PeV;
this display interval is not a measured sensitive range or a set of independent
energy-bin limits. Reference curves are restricted to their published energy ranges.

The y axis is E^2 dF/dE [GeV cm^-2 s^-1], for nu_mu+anti_nu_mu. Diffuse intensity
is multiplied by exactly 4*pi sr to show the full-sky integrated isotropic flux.
This is an explicit integration convention; it does not describe a point-source
aperture or directly compare emission per solid angle.

Reference parameters and extracted vector-band data are distributed in
`data_input/references/neutrino_spectra/`, with portable provenance and SHA-256
verification. Runtime does not download papers, extract figures or depend on
owner tests. The reference data were adopted byte-identically from the reviewed
plotting workflow, rather than estimated by combining marginal parameter errors.

- [NGC 1068](https://arxiv.org/abs/2406.06684), Table 2 and Fig. 2: Gamma=3.1,
  phi1TeV=4.02e-11 TeV^-1 cm^-2 s^-1, 0.7–15 TeV; published 68% statistical band.
- [9.5-year diffuse tracks](https://arxiv.org/abs/2111.10299), Fig. 4:
  phi100TeV=1.44e-18 GeV^-1 cm^-2 s^-1 sr^-1, Gamma=2.37, 15 TeV–5 PeV;
  published 68% single-power-law band.
- [10.3-year starting tracks](https://arxiv.org/abs/2402.18026), Fig. 17:
  per-flavor phi100TeV=1.68e-18 GeV^-1 cm^-2 s^-1 sr^-1, Gamma=2.58,
  3–550 TeV. Under the stated equal-flavor assumption this supplies the muon
  flavor. The band confidence level is not explicit in that figure caption;
  the plot preserves that qualification.

Each run writes `flux_upper_limits.csv`, `upper_limit_profiles.csv`,
`spectrum_curves.csv` and `flux_plot_provenance.json`. PNG, vector PDF
and editable SVG are stored under `figures/runs/<run>/source_<number>/`.
Catalog numeric artifacts have separate `source_<number>/` subdirectories.
The main numeric report retains all three fixed fits, their detector yields,
fit bounds, event selections and upper-limit profiles. Review checks those fits,
CSV contents, file hashes, plotted spectra, common units and diffuse conversion.
