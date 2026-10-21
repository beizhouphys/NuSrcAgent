"""Current-run-only stacking ETA; never controls the optimizer or likelihood."""
from __future__ import annotations

import math
from statistics import median
from time import monotonic

from agent_core import progress as progress_module
from agent_core.stage_progress import environment_identity, error_summary


class StackingFitProgress:
    """Measure cold, full-PDF and cached calls separately, without reading history."""
    def __init__(self, command, fitted_gamma=True, clock=monotonic, cost_state=None, cache_cost=None):
        self.command,self.clock,self.cost_state=command,clock,cost_state
        self.fitted_gamma=fitted_gamma
        self.cache_cost=cache_cost
        self.cold_cost=None
        self.started=clock()
        self.durations,self.kinds,self.predictions,self.completed_at=[],[],[],[]
        self.last_completed=self.started
        self.last_emitted=self.last_prediction=-math.inf
        self.environment=environment_identity()
        # Explicit, uncalibrated reporting assumptions, never optimizer limits.
        self.initial_budget=24. if fitted_gamma else 12.
        self.budget=self.initial_budget
        self.previous_provider,self.previous_phase=command.phase_provider,command.phase
        command.phase,command.phase_provider=None,self.snapshot
        command.emit()

    def _forecast(self,now):
        if not self.durations:
            return None,'waiting_for_first_completed_evaluation'
        full=[d for d,k in zip(self.durations,self.kinds) if k=='pdf_recomputed']
        cached=[d for d,k in zip(self.durations,self.kinds) if k=='pdf_reused']
        # A free-Gamma fit can need full-PDF work again after a cached burst.
        # Cached durations never enter its full-PDF rate.
        if full:
            rate=median(full[-8:]);basis='current_full_pdf_speed_and_assumed_remaining_calls'
        elif not self.fitted_gamma and cached:
            rate=median(cached[-8:]);basis='current_cached_speed_and_assumed_remaining_calls'
        else:
            rate=(self.cold_cost['estimated_recurring_seconds'] if self.cold_cost is not None
                  else self.durations[0])
            basis=('cold_call_recurring_work_plus_measured_cache_reads' if self.cold_cost is not None
                   else 'first_call_without_cache_instrumentation')
        age=max(0.,now-self.last_completed)
        calls=max(1.,self.budget-len(self.durations))
        remaining=rate*calls-age
        if age>=rate:
            # A still-active call is evidence against its old cost forecast.
            # Revise the per-call cost; do not count down to zero or drop ETA.
            rate=max(rate,age*1.25)
            remaining=rate*calls-age
            basis+=';active_call_cost_revised_upward'
        return max(1e-9,remaining),basis

    def snapshot(self,now):
        estimate,basis=self._forecast(now)
        row=dict(phase='joint stacking fit',estimate_scope='stacking_fit_only',
            completed_evaluations=len(self.durations),estimated_total_evaluations=self.budget,
            evaluation_budget_is_estimated=True,estimate_is_heuristic=True,
            uses_history=False,workload_basis='uncalibrated_initial_call_assumption',
            estimate_quality='rough',uncertainty_level='high',
            estimate_basis=basis,phase_elapsed_seconds=max(0.,now-self.started),
            remaining_seconds=estimate,remaining_seconds_range=None,
            estimate_age_seconds=max(0.,now-self.last_completed),
            estimate_status='rough_from_current_run' if estimate is not None else basis,
            cost_class_counts={kind:self.kinds.count(kind) for kind in set(self.kinds)},
            cold_call_cost=self.cold_cost,
            evaluation_budget_extended=self.budget>self.initial_budget,
            estimate_note='Rough fit-only ETA from this run. Initial workload assumption is uncalibrated, expands if reached, and never limits the optimizer. No confidence interval or guaranteed completion time.')
        if estimate is not None and now-self.last_prediction>=5.:
            self.predictions.append(dict(elapsed_seconds=now-self.started,
                completed_evaluations=len(self.durations),remaining_seconds=estimate,estimate_basis=basis))
            self.last_prediction=now
        return row

    def evaluate(self,function,*args,**kwargs):
        before=self.cost_state() if self.cost_state is not None else None
        before_cost=self.cache_cost() if self.cache_cost is not None and not self.durations else None
        started=self.clock()
        result=function(*args,**kwargs)
        ended=self.clock()
        after=self.cost_state() if self.cost_state is not None else None
        kind=('cold_start' if not self.durations else
              'pdf_recomputed' if self.cost_state is None or before!=after else 'pdf_reused')
        cold_cost=None
        if before_cost is not None:
            after_cost=self.cache_cost(sample_reads=True)
            setup={k:max(0.,after_cost[k]-before_cost[k]) for k in
                   ('cached_geometry_seconds','compression_seconds','energy_build_seconds')}
            measured=max(1e-9,ended-started)
            setup_seconds=min(measured,sum(setup.values()))
            cold_cost=dict(**setup,setup_seconds=setup_seconds,
                estimated_cache_read_seconds=after_cost['estimated_cache_read_seconds'],
                probe_seconds=after_cost['probe_seconds'],
                estimated_recurring_seconds=max(1e-9,measured-setup_seconds)+after_cost['estimated_cache_read_seconds'])
        with self.command.lock:
            if cold_cost is not None:self.cold_cost=cold_cost
            self.durations.append(max(1e-9,ended-started));self.kinds.append(kind)
            self.last_completed=ended
            self.completed_at.append(ended-self.started)
            if len(self.durations)>=self.budget:
                self.budget=len(self.durations)+max(3.,math.ceil(self.initial_budget*.25))
        if ended-self.last_emitted>=1.:
            self.command.emit();self.last_emitted=ended
        return result

    def close(self):
        elapsed=max(0.,self.clock()-self.started)
        with self.command.lock:
            self.command.phase_provider,self.command.phase=self.previous_provider,self.previous_phase
        errors=[dict(p,actual_remaining_seconds=max(0.,elapsed-p['elapsed_seconds']),
                     signed_error_seconds=p['remaining_seconds']-max(0.,elapsed-p['elapsed_seconds']))
                for p in self.predictions]
        return dict(version=4,completed_evaluations=len(self.durations),fit_wall_seconds=elapsed,
            evaluation_seconds=self.durations,evaluation_completed_seconds=self.completed_at,
            cost_classes=self.kinds,environment=self.environment,uses_history=False,
            cold_call_cost=self.cold_cost,
            initial_evaluation_budget=self.initial_budget,final_evaluation_budget=self.budget,
            prediction_errors=errors,prediction_error_summary=error_summary(errors),
            strategy='current_run_cost_classes_with_expanding_work_assumption',scientific_behavior_changed=False)


def start_stacking_progress(sources,gamma_mode,cost_state=None,cache_cost=None):
    command=progress_module._active
    if command is None or len(sources)<2:
        return None
    return StackingFitProgress(command,gamma_mode=='fitted',cost_state=cost_state,cache_cost=cache_cost)
