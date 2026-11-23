# Linear spectral-index interpolation for single-source analysis

New DR2 time-integrated spatial+energy single-source tasks record
`signal_energy_gamma_interpolation=linear_v1`. The primary fit, primary-spectrum
flux profiling, and the separate fixed-spectrum upper-limit fits all use that
same method. One-row catalogs classified as single-source tasks follow this rule.
Catalog individual-source scans and joint stacking retain their existing
three-point quadratic default (`parabola_v1`). DR1 and spatial-only definitions
are unchanged.

## Numerical definition

For a spectral index between neighboring table nodes s_a and s_b, the signal
energy PDF is the convex combination

\[
S_{\rm energy}(\log_{10}E_{\rm reco},\delta;s)
= \frac{s_b-s}{s_b-s_a}
S_{\rm energy}(\log_{10}E_{\rm reco},\delta;s_a)
+ \frac{s-s_a}{s_b-s_a}
S_{\rm energy}(\log_{10}E_{\rm reco},\delta;s_b).
\]

Its spectral index derivative is the difference of these two node PDF values divided
by `s_b - s_a`. At an internal grid node the right-hand interval defines
the derivative; the PDF value is continuous. Both source-declination and
event-declination lookup modes use the same method. Energy-axis interpolation
remains the original linear `np.interp`, including its valid-range and zero-value
rules. The existing 0.1 spectral-index grid and frozen numerical tables stay in place.
A convex combination preserves nonnegativity and normalization of normalized
node PDFs; no tables are regenerated or renormalized.

The previous method selected the nearest spectral index node and its two neighbors.
Its three-point parabola could change at half-grid positions, such as s=3.05,
without the two parabolas sharing a value there. The linear method removes that
finite value jump. Slopes can change at spectral index nodes.

## Execution and provenance

The shared implementation selects its interpolation from the recorded method;
source count alone never selects it, because a catalog scan also fits one
source at a time. Wrapper defaults select linear only for standalone single-source
workflow tasks. Catalog request defaults and the original quadratic arithmetic
are retained. An existing task without the method setting retains its historical
quadratic definition rather than silently switching to linear. Explicitly
recorded methods remain authoritative for historical experimental requests.

Task parameters, the analysis request, normalized settings, numerical results
and per-dataset working-set records identify the method. Review checks their
agreement, including companion fits. A primary checkpoint recorded with a
different method is rejected before loading the flux analysis; saved artifacts
and code/input hashes also protect continuation. No historical task or ensemble
is relabeled. No background trials are launched by this change.

The original SkyLLH optimizer, bounds, seeds, tolerances, detector yields,
event selections and maximum-consistency guard are unchanged. Linear
interpolation does not guarantee a global maximum. Do not replace the saved
primary fit or relax the guard to accept a higher flux-profile value.

The existing conversation boundary also remains: report reviewed primary
results in the first final-answer bubble, then await the user's affirmative
reply before the interactive flux stage. Implementation regression checks may
exercise the underlying flux code directly and must be recorded as code
verification, rather than as an invented user continuation reply.

## Verification

Owner-only numerical tests cover
agreement with the pinned native SkyLLH linear interpolator, continuity,
nonnegativity/normalization, analytic derivatives including spectral index-dependent
source weights, both declination lookup modes, cache/chunk equivalence,
new-trial cache invalidation, supported range, method metadata and scope,
historical requests, checkpoint rejection and the unchanged consistency guard.
The original stacking cache regression checks compare quadratic PDF ratios and
spectral index derivatives bit for bit. These tests and generated validation products
are excluded from GitHub synchronization.


Validated on 2026-10-20: 307 development unit tests and 20 golden cases passed.
The 13 focused single-source interpolation/scope tests passed; 14 focused tests
passed in the test checkout, including its existing empirical-request checks.
Real NGC 1068 primary fits passed review in all three copies and gave identical
n, s, TS, local p-value and significance. The complete NGC 1068 flux-code
regression passed the unchanged guard and review, produced all three limits,
normalization/spectral index profile intervals, spectrum figures and two joint contours,
and retained the exact primary fit and optimizer records. This was an internal
implementation regression, with no fabricated interactive continuation reply.
A real two-source individual scan plus joint stack before/after comparison gave
signed relative difference 0 (for nonzero references), then signed absolute
difference 0 for every checked quantity; optimizer records were identical.
The quadratic PDF-ratio/gradient cache regressions were bitwise identical.
