class SnifferTask:
    def __init__(self, id=None, iface=None, active=False, thread_id=None, schedule=None, dynamic=False) -> None:
        self.id = id
        if iface is None:
            raise ValueError("Param 'iface' cannot be None.")
        self.iface = iface
        self.active = active
        self.thread_id = thread_id
        self.schedule = schedule 
        self.dynamic = dynamic  # static or dynamic

    def is_scheduled(self):
        if not self.schedule._from and not self.schedule._to:
            return False
        return True

    def clear_schedule(self):
        if self.schedule._from:
            self.schedule._from = None
        if self.schedule._to:
            self.schedule._to = None
            

    def __lt__(self, other):
        return self.id < other.id

class Schedule:
    def __init__(self, sched_from=None, sched_to=None) -> None:
        self._from = sched_from
        self._to = sched_to

