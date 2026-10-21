"""Named execution phases and auditable, out-of-sample wall-time forecasts."""
from contextlib import contextmanager
import hashlib
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
    """A same-input/environment history; each prediction is recorded before completion."""
    names = ('request preparation','analysis','output generation','scientific review')

    def __init__(self, root, settings, mode, started=None, clock=monotonic):
        self.command = progress_module._active
        self.root,self.clock=Path(root),clock
        self.environment=environment_identity()
        inputs={}
        if isinstance(settings,dict) and settings.get('sample'):
            from agent_core.environment import _required_paths
            from agent_core.file_cache import sha256_file
            inputs={str(p):(sha256_file(self.root/p) if (self.root/p).is_file() else None)
                    for p in _required_paths(settings['sample'],settings.get('likelihood_mode'))}
        payload=dict(settings=settings,mode=mode,inputs=inputs,environment=self.environment,model='phase_eta_v2')
        self.key=hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()
        self.references=[]
        for path in sorted((self.root/'data_output/runs').glob('run*/timing.json'),reverse=True)[:64]:
            try:
                data=json.loads(path.read_text())
                review=json.loads((path.parent/'review.json').read_text())
                if data['key']==self.key and all(k in data['stage_seconds'] for k in self.names) and review.get('status') in ('pass','warning'):
                    self.references.append(data)
            except (OSError,ValueError,KeyError,TypeError):continue
            if len(self.references)==5:break
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
        history=[r['stage_seconds'] for r in self.references]
        stage_estimate=None
        if history:stage_estimate=max(0.,median(r[stage] for r in history)-elapsed)
        # The primary joint fit is the last numerical step in primary analysis.
        if stage=='analysis' and row.get('phase')=='joint stacking fit' and row.get('remaining_seconds') is not None:
            stage_estimate=row['remaining_seconds']
        future=[n for n in self.names[self.names.index(stage)+1:]]
        total=None
        if stage_estimate is not None and all(all(n in r for n in future) for r in history) and history:
            total=stage_estimate+sum(median(r[n] for r in history) for n in future)
        row.update(current_stage=stage,stage_elapsed_seconds=elapsed,
            stage_remaining_seconds=stage_estimate,request_remaining_seconds=total,
            stage_history_count=len(history),request_estimate_status='same_input_environment_history' if total is not None else 'no_completed_comparable_phase_history',
            pending_stages=future)
        if row.get('phase') is None:
            row.update(phase=stage,estimate_scope='current_stage_only',remaining_seconds=stage_estimate,
                estimate_status='historical_stage_time' if stage_estimate is not None else 'no_completed_comparable_phase_history')
        if total is not None and now-self.last_prediction>=5:
            self.predictions.append(dict(elapsed_seconds=now-self.started,current_stage=stage,remaining_seconds=total))
            self.last_prediction=now
        return row

    def finish(self,run_dir):
        elapsed=self.clock()-self.started
        rows=[dict(p,actual_remaining_seconds=max(0.,elapsed-p['elapsed_seconds']),
              signed_error_seconds=p['remaining_seconds']-max(0.,elapsed-p['elapsed_seconds'])) for p in self.predictions]
        record=dict(version=2,key=self.key,environment=self.environment,stage_seconds=self.durations,
            subphases=self.subphases,wall_seconds=elapsed,prediction_errors=rows,prediction_error_summary=error_summary(rows),
            reference_runs=[r.get('run_directory') for r in self.references],run_directory=str(run_dir))
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
            estimate_status='subphase_without_completed_reference',measured_at=started)
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
