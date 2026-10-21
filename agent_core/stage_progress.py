"""Named execution phases and auditable, out-of-sample wall-time forecasts."""
from contextlib import contextmanager
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import platform
from statistics import median
import math
from time import monotonic

from agent_core import progress as progress_module


def environment_identity():
    packages = {}
    for name in ('numpy','scipy','skyllh'):
        try: packages[name] = version(name)
        except PackageNotFoundError: packages[name] = None
    return dict(host=platform.node(),machine=platform.machine(),packages=packages,
        threads={name:os.environ.get(name) for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS',
            'MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS')})


def error_summary(rows):
    errors = [abs(r['signed_error_seconds']) for r in rows]
    if not errors:return dict(samples=0)
    return dict(samples=len(errors),mean_absolute_error_seconds=sum(errors)/len(errors),
        median_absolute_error_seconds=median(errors),
        p90_absolute_error_seconds=sorted(errors)[max(0,math.ceil(.9*len(errors))-1)],
        mean_signed_error_seconds=sum(r['signed_error_seconds'] for r in rows)/len(rows))


class StageProgress:
    """Record stages and expose only estimates measured in the current invocation."""
    names = ('request preparation','analysis','output generation','scientific review')

    def __init__(self, root, settings, mode, started=None, clock=monotonic):
        self.command = progress_module._active
        self.clock=clock
        self.use_fit_eta=(mode=="primary" and isinstance(settings,dict)
            and settings.get("analysis_type")=="catalog_stacking"
            and settings.get("catalog_operation")=="stack")
        self.environment=environment_identity()
        self.started=clock() if started is None else started
        self.current=None;self.phase_started=None;self.durations={}
        self.subphases=list(getattr(self.command,'subphase_records',[]));self.predictions=[]
        self.last_prediction=-1e99
        if self.command is not None:
            self.previous_plan=getattr(self.command,'stage_plan',None)
            self.command.stage_plan=self

    @contextmanager
    def phase(self,name):
        self.current=name;self.phase_started=self.clock()
        if name==self.names[0]:self.phase_started=self.started
        if self.command:self.command.emit('stage_started')
        try:yield
        finally:
            self.durations[name]=self.clock()-self.phase_started
            self.current=None
            if self.command:self.command.emit('stage_completed')

    def enrich(self,row,now):
        stage=self.current
        if stage is None:return row
        elapsed=max(0.,now-self.phase_started)
        stage_estimate=None
        # The primary joint fit is the last numerical step in primary analysis.
        if stage=='analysis' and self.use_fit_eta and row.get('phase')=='joint stacking fit':
            stage_estimate=row['remaining_seconds']
        future=[n for n in self.names[self.names.index(stage)+1:]]
        total=None
        if stage_estimate is not None and not future:
            total=stage_estimate
        row.update(current_stage=stage,stage_elapsed_seconds=elapsed,
            stage_remaining_seconds=stage_estimate,request_remaining_seconds=total,
            uses_history=False,request_estimate_scope='analysis_wrapper_through_review',
            request_estimate_status='current_run_only' if total is not None else 'pending_stages_have_no_current_measurement',
            pending_stages=future)
        if row.get('phase') is None:
            row.update(phase=stage,estimate_scope='current_stage_only',remaining_seconds=stage_estimate,
                estimate_status='current_run_only' if stage_estimate is not None else 'no_current_stage_rate_sample')
        if total is not None and now-self.last_prediction>=5:
            self.predictions.append(dict(elapsed_seconds=now-self.started,current_stage=stage,remaining_seconds=total))
            self.last_prediction=now
        return row

    def finish(self,run_dir):
        elapsed=self.clock()-self.started
        rows=[dict(p,actual_remaining_seconds=max(0.,elapsed-p['elapsed_seconds']),
              signed_error_seconds=p['remaining_seconds']-max(0.,elapsed-p['elapsed_seconds'])) for p in self.predictions]
        record=dict(version=3,uses_history=False,environment=self.environment,stage_seconds=self.durations,
            subphases=self.subphases,wall_seconds=elapsed,prediction_errors=rows,prediction_error_summary=error_summary(rows),
            run_directory=str(run_dir))
        (Path(run_dir)/'timing.json').write_text(json.dumps(record,indent=2)+'\n')
        if self.command:self.command.stage_plan=self.previous_plan

    def abort(self):
        if self.command:self.command.stage_plan=self.previous_plan


@contextmanager
def subphase(name):
    command=progress_module._active
    if command is None:
        yield
        return
    started=command.clock()
    with command.lock:
        previous=command.phase
        command.phase=dict(phase=name,remaining_seconds=None,estimate_scope='current_subphase_only',
            estimate_status='subphase_without_current_rate_sample',measured_at=started)
    command.emit('subphase_started')
    try:yield
    finally:
        elapsed=command.clock()-started
        plan=getattr(command,'stage_plan',None)
        record=dict(phase=name,seconds=elapsed)
        if not hasattr(command,'subphase_records'):command.subphase_records=[]
        command.subphase_records.append(record)
        if plan is not None:plan.subphases.append(record)
        with command.lock:command.phase=previous
        command.emit('subphase_completed')
