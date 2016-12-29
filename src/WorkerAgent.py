from src.BaseThread import BaseThread
from src.MPI_Wrapper import Client
from src.MPI_Wrapper import MSG
from src.WorkerRegistry import WorkerStatus
from src.TaskInfo import Task4Worker
from src.TaskInfo import TaskStatus
import Client_Module as CM
from src.MPI_Wrapper import Tags
import threading
import subprocess
import json
import time
import Queue

# constants
miliseconds = 1000
delay = 10 #interval = 10s
RT_PULL_REQUEST = True
PULL_REQUEST_DELAY = 1


class HeartbeatThread(BaseThread):
    """
    ping to master to update status
    """
    def __init__(self, client, wid):
        self._client = client
        self._wid = wid


    def run(self):
        try:
            last_ping_time = time.time()
            while not self.get_stop_flag():
                if last_ping_time and (time.time()-last_ping_time) >= delay:
                    #TODO add log: ping server, return taskid and task status
                    self._client.ping()
                    last_ping_time = time.time()
                else:
                    time.sleep(1)
        except Exception:
            #TODO
            pass

        self.stop()

class WorkerAgent(BaseThread, CM.IRecv_handler):
    """
    agent
    """
    def __init__(self, svcname):
        BaseThread.__init__(self, name='worker')
        import uuid as uuid_mod
        self.uuid = str(uuid_mod.uuid4())
        self.client = Client(self, svcname, "")
        if self.client.initialize() == 0:
            #TODO logging connect success
            pass
        else:
            #TODO logging connect error give error code
            pass
        self.wid = None
        self.capacity = 5                   # can change
        self.task_queue=Queue.Queue(maxsize=self.capacity) #~need lock~ thread safe
        self.task_list={}
        self.task_completed_queue = Queue.Queue()

        self.task_sync_flag = False

        self.heartbeat_thread=None
        self.cond = threading.Condition()
        self.worker=Worker(self, self.cond)
        #self.worker_status = WorkerStatus.NEW

        #self.app_init_boot = None
        #self.app_init_data = None
        #self.app_fin_boot = None

        self.msgQueue = Queue.Queue()

        # init_data finalize_bash result dir can be store in Task object
        self.register_flag = False
        self.register_time = None

        self.initialized = False
        self.finalized = False


    def register(self):
        self.worker.start()
        ret = self.client.send_int(self.uuid, 1, 0, Tags.MPI_REGISTY)
        if ret != 0:
            #TODO add error handler
            pass
        #TODO add logging  register to master
        self.register_time = time.time()

    def MSG_wrapper(self, **kwd):
        return json.dumps(kwd)

    def run(self):
        # use while to check receive buffer or Client buffer
        self.client.run()
        self.register()
        #comfirm worker is registered
        while not self.register_flag:
            if time.time() - self.register_time > delay:
                # TODO log: register timeout
                raise
            else:
                continue
        #ask for app_init
        if self.wid:
            self.client.send_int(self.wid,1,0, Tags.APP_INI_ASK)

        while not self.get_stop_flag():

            # single task finish ,notify master
            if self.task_sync_flag:
                self.task_sync_flag = False
                tmp_task= self.task_completed_queue.get()
                send_str = self.MSG_wrapper(wid=self.wid, tid=tmp_task.tid, time_start=tmp_task.time_start, time_fin=tmp_task.time_finish, status=tmp_task.task_status)
                self.client.send_string(send_str, len(send_str), 0, Tags.TASK_FIN)

            # handle msg from master
            if not self.msgQueue.empty():
                msg_t = self.msgQueue.get()
                if msg_t.tags == Tags.MPI_REGISTY_ACK:
                    if msg_t.pack.ibuf > 0:
                        #TODO register successfully
                        self.heartbeat_thread = HeartbeatThread(self.client,self.wid)
                        self.heartbeat_thread.start()
                        self.register_flag = True
                    else:
                        #TODO register fail
                        raise
                    self.wid = msg_t.pack.ibuf

                elif msg_t.tags == Tags.APP_INI:
                    #TODO consider if not a complete command
                    comm_dict = json.loads(msg_t.sbuf)
                    task = Task4Worker(0, comm_dict['app_init_boot'], comm_dict['app_init_data'], comm_dict['res_dir'])
                    self.task_queue.put_nowait(task)
                    self.cond.acquire()
                    self.cond.notify()
                    self.cond.release()

                elif msg_t.tags == Tags.TASK_ADD:
                    if self.task_queue.qsize() == self.capacity :
                        #TODO add error handler: out of queue bound
                        raise
                    comm_dict = json.loads(msg_t.sbuf)
                    task = Task4Worker(comm_dict['tid'], comm_dict['task_boot'], comm_dict['task_data'], comm_dict['res_dir'])
                    task.task_status = TaskStatus.SCHEDULED_HALT
                    self.task_queue.put_nowait(task.tid)
                    self.task_list[task.tid] = task
                    if self.worker.status == WorkerStatus.IDLE:
                        self.cond.acquire()
                        self.cond.notify()
                        self.cond.release()

                elif msg_t.tags == Tags.TASK_SYNC:
                    comm_dict = json.loads(msg_t.sbuf)
                    comm_send = dict()
                    t_tid = comm_dict['tid']
                    comm_send['tid'] = t_tid
                    comm_send['task_status'] = self.task_list[t_tid].task_status
                    comm_send['time_start'] = self.task_list[t_tid].time_start
                    comm_send['time_finish'] = self.task_list[t_tid].time_finish
                    send_str = json.dumps(comm_send)
                    self.client.send_string(send_str, len(send_str), 0 , Tags.TASK_SYNC)

                elif msg_t.tags == Tags.TASK_REMOVE:
                    pass
                elif msg_t.tags == Tags.WORKER_STOP:
                    pass
                elif msg_t.tags == Tags.APP_FIN:
                    comm_dict = json.loads(msg_t.sbuf)
                    task = Task4Worker(0,comm_dict['app_fin_boot'], None, None)
                    self.task_queue.put_nowait(task)
                    self.worker.finialize = True
                    if self.worker.status == WorkerStatus.IDLE:
                        self.cond.acquire()
                        self.cond.notify()
                        self.cond.release()
                    #self.worker.work_finalize(comm_dict['app_fin_boot'])
                    #self.worker_status = WorkerStatus.IDLE

            # App init complete
            if not self.initialized:
                if self.task_completed_queue.qsize() > 0:
                    task = self.task_completed_queue.get()
                    if task.task_status == TaskStatus.COMPLETED:
                        self.worker_status = WorkerStatus.INITILAZED
                        self.initialized = True
                        send_str = self.MSG_wrapper(wid=self.wid, res_dir=task.res_dir)
                        self.client.send_string(send_str, len(send_str), 0, Tags.APP_INI)
                    else:
                        # init error TODO and error handler and logging
                        self.worker_status = WorkerStatus.IDLE
                        send_str = self.MSG_wrapper(wid=self.wid, res_dir=task.res_dir, error='initialize error')
                        self.client.send_string(send_str, len(send_str), 0, Tags.APP_INI)
                #else:# ask for initial
                    #self.client.send_int(self.wid,1,0,Tags.APP_INI_ASK)


            # ask master for app fin, master may add new tasks
            if self.task_queue.empty() and self.task_completed_queue.qsize() > 1:
                self.worker_status = WorkerStatus.IDLE
                comm_send = {}
                comm_send['wid'] = self.wid
                comm_send['ltc'] = str(self.task_completed_queue.get().tid)
                while not self.task_completed_queue.empty():
                    comm_send['ltc'] += ','+str(self.task_completed_queue.get().tid)
                send_str = json.dumps(comm_send)
                self.client.send_string(send_str, len(send_str), 0 ,Tags.APP_FIN)
                if self.worker.status == WorkerStatus.COMPELETE:
                    #notify worker and stop
                    self.cond.acquire()
                    self.cond.notify()
                    self.cond.release()
                    break


            #TODO monitor the task queue, when less than thrashold, ask for more task

            # loop delay
            if not RT_PULL_REQUEST:
                time.sleep(PULL_REQUEST_DELAY)

        self.stop()


    def finalize_run(self):
        pass

    def stop(self):
        BaseThread.stop()
        if self.heartbeat_thread:
            self.heartbeat_thread.stop()
        #TODO client stop

    def kill(self):
        pass

    def remove_task(self, taskid):
        pass

    def add_task(self,taskid , task):
        pass

    def handler_recv(self, tags, pack):
        msg = MSG(tags, pack)
        self.msgQueue.put_nowait(msg)

class Worker(BaseThread):
    """
    worker
    """
    def __init__(self,workagent, cond):
        BaseThread.__init__("worker")
        self.workagent = workagent
        self.mytask = None

        self.cond = cond

        self.initialized = False
        self.finialize = False
        self.status = WorkerStatus.NEW

    def run(self):
        #check worker agent's task queue
        while not self.initialized:
            if self.status != WorkerStatus.NEW:
                self.workagent.status = WorkerStatus.IDLE
            self.cond.acquire()
            self.cond.wait()
            self.cond.release()
            self.work_initial(self.workagent.task_queue.get())
            if self.initialized == False:
                continue


        while not self.finialize:
            self.status = WorkerStatus.RUNNING
            while not self.workagent.task_queue.empty():
                task = self.workagent.task_queue.get()
                self.workagent.current_task = task.tid
                err = self.do_work(task)
                if err:
                    #TODO change TaskStatus logging
                    pass
                self.workagent.task_completed_queue.put(task)
                self.workagent.task_sync_flag = True

            self.status = WorkerStatus.IDLE
            self.cond.acquire()
            self.cond.wait()
            self.cond.release()

        self.work_finalize(self.workagent.task_queue.get())
        self.status = WorkerStatus.COMPELETE
        self.cond.acquire()
        self.cond.wait()
        self.cond.release()


    def do_task(self,task):
        task.time_start = time.time()
        task.task_status = TaskStatus.PROCESSING
        rc = subprocess.Popen([task.task_boot, task.task_data], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = rc.communicate()
        task.time_finish = time.time()
        return len(stderr) == 0
#        if len(stderr) == 0:  # no error
#            self.initialized = True
#            self.status = WorkerStatus.INITILAZED
#            task.task_status = TaskStatus.COMPLETED
#        else:
#            task.task_status = TaskStatus.FAILED
#            self.initialized = False
#            # TODO error handler and log

    def work_initial(self, task):
        #do the app init
        if not task.task_boot and not task.task_data:
            self.initialized = True
        else:
            #TODO execuate the bash/.py
            if self.do_task(task) == 0:
                self.initialized = True
                self.status = WorkerStatus.INITILAZED
                task.task_status = TaskStatus.COMPLETED
            else:
                task.task_status =TaskStatus.FAILED
                self.initialized = False
        self.workagent.task_completed_queue.put(task)


    def do_work(self, task):
        return self.do_task(task)

    def work_finalize(self, fin_task):
        if fin_task.task_boot:
            self.do_task(fin_task)
        self.workagent.task_completed_queue.put(fin_task)

    def stop(self):
        pass




