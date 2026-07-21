from __future__ import annotations # Codex

import math # Codex

from agent_core_cdx.schemas_cdx import NormalizedAnalysis # cdx


def run_mock_backend(normalized: NormalizedAnalysis) -> dict[str, object]: # Codex
    score = 0.0 # Codex
    for source in normalized.sources: # Codex
        score += source.weight * (math.sin(source.ra_rad) + math.cos(source.dec_rad)) # Codex
    ts = round(abs(score) * 4.0, 6) # Codex
    pre_trial_p = round(max(1.0 / normalized.n_trials, min(1.0, math.exp(-0.5 * ts))), 12) # Codex
    return {"backend": "mock_phase0", "best_fit_ns": round(ts / 2.0, 6), "ts": ts, "pre_trial_p": pre_trial_p, "post_trial_p": None, "note": "mock backend only; not a scientific IceCube likelihood result"} # Codex
