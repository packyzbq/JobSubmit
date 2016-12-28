import Server_Module as SM
from src.MPI_Wrapper import Server
from src.MPI_Wrapper import Tags
from src.MPI_Wrapper import MSG
from src.IScheduler import TestScheduler
from src.IApplicationMgr import TestAppMgr
from src.TaskInfo import TaskStatus
import src.WorkerRegistry
import time
import json
import Queue
from src.BaseThread import BaseThread

CONTROL_DELAY = 2 #config to change
WORKER_NUM = 1

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

class Master(IMasterController, SM.IRecv_handler):

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

        self.MSGqueue = Queue.Queue()

        self.stop = False

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
        self.control_thread.start()

        while not self.stop:
            if not self.MSGqueue.empty():
                msg = self.MSGqueue.get()

                if msg.tag == Tags.MPI_REGISTY:
                    self.register(msg.pack.ibuf)
                elif msg.tag == Tags.APP_INI_ASK:
                    wid = msg.pack.ibuf
                    init_boot, init_data = self.appmgr.get_app_init(wid)
                    appid, send_str = MSG_wrapper(app_init_boot=init_boot, app_init_data=init_data,
                                              res_dir='/home/cc/zhaobq')
                    w = self.worker_registry.get(wid)
                    w.current_app = appid
                    self.server.send_string(send_str, len(send_str), w.w_uuid, Tags.APP_INI)
                elif msg.tag == Tags.APP_INI:
                # worker init success or fail
                    recv_dict = eval(json.loads(msg.pack.sbuf))
                    if 'error' in recv_dict:
                        #worker init error TODO stop worker or reassign init_task?
                        print "worker init error"
                        pass
                    else:
                        if self.appmgr.check_init_res(recv_dict['wid'], recv_dict['res_dir']):
                            w = self.worker_registry.get(recv_dict['wid'])
                            try:
                                w.alive_lock.require()
                                w.initialized = True
                                w.worker_status = src.WorkerRegistry.WorkerStatus.INITILAZED
                            except:
                                pass
                            finally:
                                w.alive_lock.release()
                        else: # init result error
                            #TODO reassign init_task?
                            pass
                elif msg.tag == Tags.TASK_FIN:
                    recv_dict = eval(json.loads(msg.pack.sbuf))
                    # wid, tid, time_start, time_fin, status
                    w = self.worker_registry.get(recv_dict['wid'])
                    t = self.appmgr.get_task(w.current_app, recv_dict['tid'])
                    if recv_dict['status'] == TaskStatus.COMPLETED:
                        t.status = TaskStatus.COMPLETED
                        # TODO add task other details
                        self.task_scheduler.task_completed(t)
                        del(w.scheduled_tasks[recv_dict['tid']])
                    elif recv_dict['status'] == TaskStatus.FAILED:
                        t.status = TaskStatus.FAILED
                        self.task_scheduler.task_failed(t)
                        del(w.scheduled_tasks[recv_dict['tid']])
                    else:
                        pass
                elif msg.tag == Tags.APP_FIN:
                    recv_dict = eval(json.loads(msg.pack.sbuf))
                    if self.task_scheduler.has_more_work():
                        #TODO schedule more work
                        pass
                    else:
                        fin_boot,fin_data = self.appmgr.get_app_fin(recv_dict['wid'])
                        send_str = MSG_wrapper(app_fin_boot=fin_boot, app_fin_data=fin_data)
                        self.server.send_string(send_str, len(send_str), self.worker_registry.get(recv_dict['wid']).w_uuid, Tags.APP_FIN)


    def schedule(self, w_uuid, tasks):
        for t in tasks:
            w = self.worker_registry.get_by_uuid(w_uuid)
            w.worker_status = src.WorkerRegistry.WorkerStatus.RUNNING
            w.scheduled_tasks.append(t.tid)
            send_str = MSG_wrapper(tid=t.tid, task_boot=t.task_boot, task_data=t.task_data, res_dir='/home/cc/zhaobq')
            self.server.send_string(send_str,len(send_str), w_uuid,Tags.TASK_ADD)


    def unschedule(self, wid, tasks=None):
        pass

    def remove_worker(self, wid):
        self.task_scheduler.worker_removed(self.worker_registry.get(wid))
        self.worker_registry.remove(wid)



    def handler_recv(self, tags, pack):
        msg = MSG(tags,pack)
        self.MSGqueue.put_nowait(msg)


    def register(self, w_uuid, capacity=10):
        worker = self.worker_registry.add_worker(w_uuid,capacity)
        self.server.send_int(worker.wid, 1, w_uuid, Tags.MPI_REGISTY_ACK)
        #TODO loggong worker register
