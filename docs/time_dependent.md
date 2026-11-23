# DR2 time-dependent single-source analysis and catalog scans

Time-dependent analysis tests a source's emission with an explicit Gaussian
or box arrival-time profile. A catalog scan fits every selected source
independently, with its own n, spectral index and temporal parameters. Time-dependent
stacking awaits collaborator-provided code. DR1 remains unchanged.

## Scientific definition

The existing full14 DR2 SkyLLH likelihood supplies the spatial PDF, optional
energy PDF, detector acceptance, event selection and n and s maximization.
For dataset k, the temporal signal PDF is

`S_time^k(t) = I_k(t) g(t) / integral I_k(t') g(t') dt'`,

where I_k is the published good-run indicator. Gaussian g is
`exp[-(t-t0)^2/(2 sigma_t^2)]`; box g is one on
`[t0-duration/2, t0+duration/2)` and zero elsewhere. The width is Gaussian
sigma_t or the **full** box duration, both in days. Times explicitly use the
public event files' MJD/UT1 convention.

The supported background model is explicitly selected as `uniform_livetime`:
`B_time^k(t) = I_k(t) / T_k`, where T_k is integrated detector livetime.
This assumes a constant background rate within each grouped dataset and the
usual separation of time from the supplied spatial/energy distributions.
Selecting this model is a scientific input; the Agent must not infer it.
It does not model seasonal background-rate variations or sub-day azimuthal
response. The grouped IC86_I-XI detector response retains the public dataset's
existing definition.

The time-dependent yield is the steady detector yield multiplied by
`integral I_k(t) g(t) dt / T_k`. Dataset signal fractions normalize these
yields across all four datasets, with their spectral index derivatives included.
A profile wholly outside a season or within a detector downtime gap has
zero acceptance there. Its event time ratios and dataset fraction are zero;
other seasons still contribute normally. One released IC59 event equals a
published run stop exactly at the CSV precision. PDF support includes exact
run-stop equalities, a measure-zero endpoint convention recorded per dataset;
no event time, event membership or uptime integral is changed. Positive
offsets and detector downtime gaps remain invalid. Frozen PDF products are unchanged.
A box covering every good-run interval recovers the time-integrated
likelihood, detector fractions and fitted n/TS exactly.

The statistic is `TS = 2 log(L_hat / L(n=0))`, constrained to n >= 0,
without an added duration penalty. It is not the significance of the time
search. Time-dependent p-values, one-sided significances and catalog-corrected
values remain unavailable. The time-integrated half-chi-square formulas and
independent-source catalog correction are deliberately bypassed. Matching
background trials must repeat the complete temporal, spectral and catalog
search; their scrambling method awaits owner approval and no time-dependent
background trials are executed. Time-integrated background-trial follow-up
rejects these tasks.

## Fixed parameters and explicit searches

A supplied t0 or width is fixed unless the researcher explicitly requests
fitting it and supplies its value as a search seed. An omitted parameter
means fitted; it cannot execute until finite bounds, search seeds and search
settings are supplied. Gaussian and box profiles allow either or both temporal
parameters to be fitted. No bounds, search range, background model or
scrambling method is silently chosen.

`grid_powell_v1` first evaluates the Cartesian product of the supplied seeds,
then starts one bounded Powell search at each seed. At every temporal point,
the original SkyLLH `skyllh_lbfgs_v1` optimizer profiles n and any free spectral index.
MJD centers are scaled linearly to the unit interval; widths use log scaling.
The requested maxiter, xtol and ftol refer to this scaled outer search.
All seed evaluations and search outcomes are retained. An unconverged search
or inner maximization fails; the runtime never widen bounds, changes seeds
or substitutes a different scientific request. Multiple starts improve search
coverage but do not certify a unique global maximum. Box objectives are
nonsmooth when an edge passes an event; choose seeds/resolution accordingly.
When n=0, the temporal parameters and spectral index are not measurements.

The standalone source's existing linear spectral-index interpolation and the catalog
scan's existing quadratic interpolation retain their respective definitions.
A supplied fixed non-PL spectrum and an explicitly requested PL range use the
same spectrum-preparation interface as the other supported DR2 analyses.
Time-integrated flux products cannot be applied to these fits. Time-dependent
flux/fluence products are outside this implementation; tasks finish after
the primary result and review, with no AWAITING_FLUX continuation.

## Public wrapper

The files under `configs/examples/` are **illustrative analysis settings**,
not approved defaults for a researcher's source. A fixed Gaussian example is:

```json
{
  "profile": "gaussian",
  "time_format": "mjd",
  "time_scale": "ut1",
  "background_time_model": "uniform_livetime",
  "t0": {"value": 57000.0},
  "width": {"value": 65.0}
}
```

For a fitted t0 and width, replace the last two settings and add search:

```json
{
  "profile": "gaussian",
  "time_format": "mjd",
  "time_scale": "ut1",
  "background_time_model": "uniform_livetime",
  "t0": {"bounds": [56900.0, 57100.0], "seeds": [56950.0, 57000.0, 57050.0]},
  "width": {"bounds": [10.0, 100.0], "seeds": [20.0, 65.0]},
  "search": {"method": "grid_powell_v1", "maxiter": 100, "xtol": 0.0001, "ftol": 0.00001}
}
```

Use `"profile": "box"` for a box, with width in full-duration days. To fix
one parameter, use its `value` mapping and omit its bounds/seeds. To fit a
supplied initial value explicitly, put it in `seeds` and use `"mode":"fitted"`.
An explicit fixed `mode` cannot also carry fit bounds or seeds.

```bash
.venv/bin/python run_agent_wrap.py create-single \
  --name 'TXS 0506+056' --ra-deg 77.3581851 --dec-deg 5.69314828 \
  --temporal-file configs/examples/temporal_gaussian_fixed.json \
  --request 'Use the explicit fixed Gaussian example for implementation checking; no trials.'
.venv/bin/python run_agent_wrap.py run --task <task_id>
```

Omitting the spectral-index option selects the default fit. Supplying
--s fixes the power-law spectral index unless --s-mode fitted is
explicit. Generic ICRS/Galactic coordinates, angular units and provenance
use the shared input layer.

```bash
.venv/bin/python run_agent_wrap.py create-catalog \
  --source 'source A,77.3581851,5.69314828' --source 'source B,40,-20' \
  --catalog-operation scan --s 2 \
  --temporal-file configs/examples/temporal_gaussian_fitted.json \
  --request 'Independently scan both example coordinates with the explicit Gaussian search.'
.venv/bin/python run_agent_wrap.py run --task <task_id> --workers 2
```

The --temporal-file option implies time_dependent unless --time-mode is
explicitly supplied. A multi-source time-dependent request selects scan when
no catalog operation was specified. Stacking and scan_and_stack are rejected.
Individual scans do not accept stacking weighting factors.
`create-single --time-mode time_dependent` without a complete specification
stays AWAITING_CONFIRMATION; resolve it with
`confirm --task <task_id> --temporal-file <complete.json>`.
Only a READY task can run. The task records the input JSON path/hash, complete
settings and parameter provenance; the normalized request itself seals the
actual values used for execution. Changing the source JSON afterward does not
retroactively alter a recorded task.

## Outputs and review

`show`/`run` return `time_dependent_summary`: input-ordered results with n,
spectral index, TS, t0, width, fixed/fitted modes, and unavailable calibration fields.
Artifacts include the complete CSV, one temporal evaluation CSV per source,
intrinsic-profile PNG/PDF figures, normalized settings, code/input provenance
and scientific/artifact reviews. The figures display intrinsic profile shape;
likelihood normalization separately accounts for detector downtime.
Review checks the recorded settings, convergence, detector fractions, source
identity/order, unavailable calibration, zero trials and artifact hashes.
A nonzero signal fit at a requested temporal bound is preliminary and keeps
its boundary warning. Failed reviews block valid-result reporting.

## Validation scope

Owner-only tests remain outside the distributed repository. Deterministic
checks compare time-profile normalization against independent quadrature,
dataset-fraction derivatives against finite differences, and the complete
SkyLLH log-likelihood/gradient against the explicit event-mixture formula.
A broad-box limit tests the unchanged time-integrated maximum. Real persistent
wrapper runs cover fixed/fitted temporal parameters, Gaussian/box profiles,
fixed/fitted spectral index, spatial-only mode and catalog scans with input-order
preservation. These checks establish the implemented likelihood and workflow;
they do not supply time-search significance calibration or parameter coverage.

SkyLLH references: [v26 time-dependent tutorial](https://icecube.github.io/skyllh/v26.0.0/html/tutorials/time_dependent_point_source.html),
[upstream implementation](https://github.com/icecube/skyllh/blob/v26.0.0/skyllh/analyses/i3/publicdata_ps/time_dependent_ps.py).
The upstream single-dataset example is not used as a four-dataset yield model;
this implementation explicitly includes temporal acceptance across all datasets.
