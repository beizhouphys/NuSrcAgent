"""Current-invocation flux work timing; observers never choose numerical points."""
from contextlib import contextmanager
from statistics import median

from agent_core import progress as progress_module
from agent_core.stacking_progress import StackingFitProgress
from agent_core.stage_progress import error_summary


class ProfileProgress:
    def __init__(self):
        self.command=progress_module._active
        self.group=None
        self.unit_observer=None
        self.gamma=None
        self.records=[]

    def evaluate(self,function,ns,gamma):
        def call():
            result=function(ns,gamma)
            self.gamma=gamma
            return result
        return self.unit_observer.evaluate(call) if self.unit_observer else call()

    def snapshot(self,now):
        group=self.group
        done=len(group['durations']);remaining=group['total']-done
        obs=self.unit_observer
        row=(obs.snapshot(now) if obs else dict(phase=group['name'],uses_history=False,
            estimate_quality='rough',estimate_is_heuristic=True,remaining_seconds=None))
        if remaining==0:
            estimate,basis=0.,'all_profile_units_completed'
        elif group['durations']:
            age=0. if obs is None else max(0.,now-group['unit_started'])
            rate=median(group['durations'][-8:])
            if age>=rate:rate=age*1.25
            estimate=max(1e-9,rate*remaining-age)
            basis='same_profile_group_completed_units_in_current_run'
        else:
            inner=row['remaining_seconds'];age=0. if obs is None else now-group['unit_started']
            estimate=None if inner is None else inner+max(0,remaining-1)*(inner+age)
            basis='first_unit_current_evaluation_speed_and_structural_call_assumption'
        row.update(remaining_seconds=estimate,estimate_basis=basis,completed_units=done,
            total_units=group['total'],phase_elapsed_seconds=now-group['started'],
            estimate_scope='current_profile_group_only',
            estimate_status='rough_from_current_run' if estimate is not None else 'waiting_for_first_completed_evaluation',
            estimate_note='Rough ETA for this profile group only; later groups, fits, output and review are unestimated.',
            pending_profile_groups_are_unestimated=True)
        if estimate is not None and remaining>0 and now-group['last_prediction']>=5.:
            group['predictions'].append(dict(elapsed_seconds=now-group['started'],
                completed_units=done,remaining_seconds=estimate,estimate_basis=basis))
            group['last_prediction']=now
        return row

    @contextmanager
    def work(self,name,total,initial_calls=12):
        command=self.command
        if command is None:
            yield
            return
        previous=self.group
        previous_provider,previous_phase=command.phase_provider,command.phase
        group=dict(name=name,total=total,initial_calls=initial_calls,durations=[],predictions=[],
                   started=command.clock(),last_prediction=-1e99)
        with command.lock:
            self.group=group
            command.phase,command.phase_provider=None,self.snapshot
        command.emit('profile_group_started')
        try:yield
        finally:
            with command.lock:
                elapsed=command.clock()-group['started']
                errors=[dict(p,actual_remaining_seconds=max(0.,elapsed-p['elapsed_seconds']),
                             signed_error_seconds=p['remaining_seconds']-max(0.,elapsed-p['elapsed_seconds']))
                        for p in group['predictions']]
                record=dict(phase=name,estimate_scope='current_profile_group_only',uses_history=False,
                    seconds=elapsed,completed_units=len(group['durations']),total_units=total,
                    unit_seconds=group['durations'],prediction_errors=errors,
                    prediction_error_summary=error_summary(errors))
                self.records.append(record)
                if not hasattr(command,'work_records'):command.work_records=[]
                command.work_records.append(record)
                self.group=previous
                command.phase_provider,command.phase=previous_provider,previous_phase
            command.emit('profile_group_completed')

    @contextmanager
    def unit(self):
        command,group=self.command,self.group
        if command is None or group is None:
            yield
            return
        started=command.clock()
        # Only reporting assumptions; the numerical algorithm chooses every point.
        with command.lock:
            obs=StackingFitProgress(command,fitted_gamma=False,clock=command.clock,
                cost_state=lambda:self.gamma,phase=group['name'],scope='current_profile_unit_only',
                initial_budget=group['initial_calls'],emit_initial=False)
            group['unit_started']=started
            self.unit_observer=obs
            command.phase_provider=self.snapshot
        command.emit('profile_unit_started')
        completed=False
        try:
            yield
            completed=True
        finally:
            with command.lock:
                obs.close()
                self.unit_observer=None
                if completed:group['durations'].append(command.clock()-started)
            command.emit('profile_unit_completed' if completed else 'profile_unit_failed')
