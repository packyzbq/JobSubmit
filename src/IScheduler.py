from src.BaseThread import BaseThread
import src
import Queue
import json

from src.MPI_Wrapper import Tags


class Policy:
    """
    Collection of policy values. Empty by default.
    """
    pass

class IScheduler(BaseThread):
    policy = Policy()
    def __int__(self, master):
        BaseThread.__init__(self, name=self.__class__.__name__)
        self.master = master
        #self.appmgr = appmgr
        self.current_app = None
        self.task_todo_Queue = Queue.Queue()
        self.task_unschedule_queue = Queue.Queue()

    def run(self):
        pass

    def initialize(self):
        pass

    def has_more_work(self):
        """
        Return ture if current app has more work( when the number of works of app is larger than sum of workers' capacities)
        :return: bool
        """
        pass

    #def worker_add(self, w_entry):

    def worker_initialized(self, w_entry):
        """
        called by Master when a worker agent successfully initialized the worker, (maybe check the init_output)
        when the method returns, the worker can be marked as ready
        :param w_entry:
        :return:
        """
        raise NotImplementedError

    def worker_removed(self, w_entry):
        """
        called by Master when a worker has been removed from worker Regitry list (lost. terminated or other reason)
        :param w_entry:
        :return:
        """
        pass

    def task_failed(self,task):
        """
        called when tasks completed with failure
        :param task:
        :return:
        """
        raise NotImplementedError

    def task_schedule(self, tasks):
        """
        called when need to assign tasks to workers
        :param tasks:
        :return:
        """
        raise NotImplementedError

    def task_unschedule(self, tasks):
        """
        called when tasks have been unschedule. tasks that have not been started or that are not completed
        :param tasks:
        :return:
        """


def MSG_wrapper(**kwd):
    return json.dumps(kwd)

class TestScheduler(IScheduler):
    def __init__(self, master):
        IScheduler.__init__(master)
        self.current_app = self.master.appmgr.applist(1)
        for t in self.current_app.task_list:
            self.task_todo_Queue.put(self.current_app.task_list[t])

    def has_more_work(self):
        return not self.task_todo_Queue.empty()

    def task_schedule(self, tasks):
        while not self.task_todo_Queue.empty():
            wid, room = self.master.worker_registry.get_aviliable_worker(True)
            if wid != -1:
                for r in range(0, room):
                    self.master.schedule(wid, self.task_todo_Queue.get())
            else:
                #TODO no aviliable worker can be assigned
                #Halt?
                pass

    def worker_initialized(self, w_entry):
        send_str = MSG_wrapper(app_ini_boot = self.current_app.init_boot, app_ini_data=self.current_app.init_data, res_dir='/home/cc/zhaobq')
        self.master.server.send_str(send_str, len(send_str), w_entry.w_uuid, Tags.APP_INI)

    def run(self):
        # init worker
        try:
            self.master.worker_registry.lock.require()
            for w in self.master.worker_registry.get_worker_list():
                if not w.initialized and not w.current_app:
                    w.current_app = self.current_app
                    self.worker_initialized(w)
        finally:
            self.master.worker_registry.lock.release()

        while self.has_more_work() and not self.get_stop_flag():

            for w,r in self.master.worker_registry.get_aviliable_worker(True):
                tasks = []
                try:
                    for i in range(r):
                        tasks.append(self.task_todo_Queue.get_nowait())
                except Queue.Empty:
                    pass
            self.master.schedule(w.wid, tasks)

        while







