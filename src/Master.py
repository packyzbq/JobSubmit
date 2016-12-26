import Server_Module as SM
from src.MPI_Wrapper import Server
from src.MPI_Wrapper import Tags
from src.IScheduler import TestScheduler
from src.IApplicationMgr import TestAppMgr
import src.WorkerRegistry
import time
import json
from src.BaseThread import BaseThread

CONTROL_DELAY = 2 #config to change


def MSG_wrapper(**kwd):
    return json.dumps(kwd)

class ControlThread(BaseThread):
    """
    check and remove lost worker
    """
    def __init__(self, master):
        BaseThread.__init__(self, 'ControlThread')
        self.master = master
        self.processing = False

    def run(self):
        time_start = time.time()
        while not self.get_stop_flag():
            try:
                for wid in self.master.worker_registry:
                    w = self.master.worker_registry.get(wid)
                    try:
                        w.alive_lock.require()
                        if w.alive and w.lost():
                            #TODO loging: lost worker
                            self.master.remove_worker(wid)
                            continue
                        if w.alive :
                            if w.processing_task:
                                w.idle_time = 0
                            else:
                                if w.idle_time == 0:
                                    w.idle_time = time.time()
                            if w.idle_timeout():
                                #TODO logging  idle timeout, worker will be removed
                                self.master.remove_worker(wid)
                    finally:
                        w.alive_lock.release()
            finally:
                pass

            time.sleep(CONTROL_DELAY)

    def activateProcessing(self):
        self.processing = True

class IMasterController:
    """
    interface used by Scheduler to control task scheduling
    """
    def schedule(self, wid, task):
        """
        schedule task to be consumed by the worker
        If worker can not be scheduled tasks , then call Scheduler task_unschedule()
        :param wid: worker id
        :param task: task
        :return:
        """
        raise  NotImplementedError

    def unschedule(self, wid, tasks=None):
        """
        Release scheduled tasks from the worker, when tasks = None ,release all tasks on worker
        Sucessfully unscheduled tasks will be reported via the tasks_unscheduled() callback on the task manager.
        :param wid: worker id
        :return: list of successfully unscheduld tasks
        """
        raise NotImplementedError

    def remove_worker(self, wid):
        """
        Remove worker from the pool and release all unscheduled tasks(all processing tasks will be declared lost)
        :param worker: worker id
        :return:
        """
        raise NotImplementedError

class Master(SM.IRecvhandler, IMasterController, SM.IRecv_handler):

    def __init__(self, rid = 0, svc_name='TEST'):
        self.svc_name = svc_name
        # worker registery
        self.worker_registry = src.WorkerRegistry.WorkerRegisty()
        # task scheduler
        self.task_scheduler = None

        self.control_thread = ControlThread(self)

        self.appmgr = None

        self.__tid = 1
        self.__wid = 1

        self.server= Server(self, "svcname")
        self.server.initialize(svc_name)
        self.server.run()


    def startProcessing(self):
        # create task -> appmgr
        self.appmgr = TestAppMgr(self)
        self.appmgr.init_app()
        if self.appmgr.applist.has_key(1):
            self.appmgr.create_task(1)
        else:
            print "error no such application"

        # schedule task -> scheduler
        self.task_scheduler = TestScheduler(self)
        self.task_scheduler.start()
        # manage worker registery


    def schedule(self, wid, tasks):
        pass





    def handler_recv(self, tags, pack):
        if tags == Tags.MPI_REGISTY:
            pass
        elif tags == Tags.TASK_SYNC:
            pass
        elif tags == Tags.TASK_FIN:
            pass
        elif tags == Tags.APP_INI_ASK:
            pass

    def register(self, w_uuid, capacity=10):
        self.worker_registry.add_worker(w_uuid,capacity)
        #TODO loggong worker register
