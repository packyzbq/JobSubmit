import time

class TaskStatus:
    """
    tansk status enumeration
    """
    NEW = 0
    #INITIALIZED = 1
    PROCESSING = 2
    COMPLETED = 3
    FAILED = 4
    LOST = 5
    UNSCHEDULED = 6
    SCHEDULED_HALT = 7

class Task:
    """
    task to be scheduled for worker to execute
    """
    def __init__(self, tid):
        self.tid = tid
        self.status = TaskStatus.NEW

        self.history = [TaskDetail()]

        self.task_boot = []
        self.task_data = None

        self.res_dir = None

    def initial(self, work_script=None, res_dir="./"):
        self.task_boot = work_script
        self.res_dir = res_dir
        self.status = TaskStatus.UNSCHEDULED

    def status(self):
        return self.status

    def assign(self, wid):
        if not self.status is TaskStatus.NEW:
            try:
                assert (self.status in [TaskStatus.FAILED, TaskStatus.UNSCHEDULED, TaskStatus.LOST])
            except:
                #TODO
                pass
            self.history.append(TaskDetail())
        self.mydetial().assign(wid)

    def mydetial(self):
        return self.history[-1]

class TaskDetail:
    """
    details about task status for a single execution attempt
    """
    def __int__(self):
        self.assigned_wid = -1
        self.result_dir = None
        self.time_start = 0
        self.time_exec = 0
        self.time_finish = 0
        self.time_scheduled = 0

    def assign(self, wid):
        assert(wid >0)
        assert(self.assigned_wid == -1)
        self.assigned_wid = wid
        self.time_scheduled = time.time()

class Task4Worker:
    def __init__(self, tid, task_boot, task_data, res_dir):
        self.tid = tid
        self.task_boot = task_boot
        self.task_boot = task_data
        self.res_dir = res_dir

        self.time_start = 0
        self.time_finish = 0
        self.task_status = TaskStatus.NEW