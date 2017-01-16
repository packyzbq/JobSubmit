from src.BaseThread import BaseThread
from src.MPI_Wrapper import Client
from src.MPI_Wrapper import MSG
import IRecv_Module as IM
from src.WorkerRegistry import WorkerStatus
from src.TaskInfo import Task4Worker
from src.TaskInfo import TaskStatus
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

class WorkerPolicy:
    pass

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

class WorkerAgent(BaseThread):
    """
    agent
    """
    def __init__(self, svcname, capacity=5):
        BaseThread.__init__(self, name='worker')
        self.recv_buffer = IM.IRecv_buffer()
        import uuid as uuid_mod
        self.uuid = str(uuid_mod.uuid4())
        self.client = Client(self.recv_buffer, svcname, self.uuid)
        if self.client.initialize() == 0:
            #TODO logging connect success
            pass
        else:
            #TODO logging connect error give error code
            print("mpi client initial error")
            pass
        self.wid = None
        self.appid = None # the app that are running
        self.capacity = capacity                   # can change
        self.task_queue=Queue.Queue(maxsize=self.capacity) #~need lock~ thread safe
        self.task_completed_queue = Queue.Queue()

        self.app_ini_task = None
        self.app_ini_task_lock = threading.RLock()
        self.app_fin_task = None
        self.app_fin_task_lock = threading.RLock()

        self.task_sync_flag = False
        self.task_sync_lock = threading.RLock()

        self.heartbeat_thread=None
        self.cond = threading.Condition()
        self.worker=Worker(self, self.cond)
        #self.worker_status = WorkerStatus.NEW

        #self.app_init_boot = None
        #self.app_init_data = None
        #self.app_fin_boot = None


        # init_data finalize_bash result dir can be store in Task object
        self.register_flag = False
        self.register_time = None

        self.initialized = False
        self.finalized = False


    def register(self):
        self.worker.start()
        ret = self.client.send_string(self.uuid, len(self.uuid), 0, Tags.MPI_REGISTY)
        if ret != 0:
            #TODO add error handler
            pass
        #TODO add logging  register to master, take down register info
        self.register_time = time.time()

    def MSG_wrapper(self, **kwd):
        return json.dumps(kwd)

    def run(self):
        # use while to check receive buffer or Client buffer
        self.client.run()
        self.register()
        # ensure the worker is registered and initialed
        while True:
            #already register and inistialize
            if self.register_flag and self.initialized:
                break

            if not self.recv_buffer.empty():
                msg_t = self.recv_buffer.get()
                if msg_t.tag == -1:
                    continue
                # comfirm worker is registered
                if not self.register_flag:
                    if msg_t.tag == Tags.MPI_REGISTY_ACK:
                        self.wid = msg_t.ibuf
                        if msg_t.ibuf > 0:
                            # TODO register successfully
                            self.heartbeat_thread = HeartbeatThread(self.client, self.wid)
                            self.heartbeat_thread.start()
                            self.register_flag = True
                            # ask for api_ini
                            self.client.send_int(self.wid, 1, 0, Tags.APP_INI_ASK)
                        else:
                            # TODO register fail
                            raise

                    elif time.time() - self.register_time > delay:
                        # TODO log: register timeout
                        raise
                    else:
                        continue
                # confirm worker is initialed
                if not self.initialized:
                    if msg_t.tag == Tags.APP_INI:
                        task_info = eval(json.loads(msg_t.sbuf))
                        assert task_info.has_key('app_ini_boot') and task_info.has_key('app_ini_data') and task_info.has_key('res_dir')
                        self.app_ini_task_lock.acquire()
                        self.app_ini_task = Task4Worker(0, task_info['app_ini_boot'], task_info['app_ini_data'], task_info['res_dir'])
                        self.app_ini_task_lock.release()
                        #self.task_queue.put(tmp_task)
                        #wake worker
                        if self.worker.get_status() == WorkerStatus.NEW:
                            self.cond.acquire()
                            self.cond.notify()
                            self.cond.release()

                    else:
                        continue
            else:
                continue
        # message handle
        while not self.get_stop_flag():

            # single task finish ,notify master
            self.task_sync_lock.acquire()
            if self.task_sync_flag:
                self.task_sync_flag = False
                self.task_sync_lock.release()
                while not self.task_completed_queue.empty():
                    tmp_task= self.task_completed_queue.get()
                    send_str = self.MSG_wrapper(wid=self.wid, tid=tmp_task.tid, time_start=tmp_task.time_start, time_fin=tmp_task.time_finish, status=tmp_task.task_status)
                    self.client.send_string(send_str, len(send_str), 0, Tags.TASK_FIN)
            else:
                self.task_sync_lock.release()
            # handle msg from master
            if not self.recv_buffer.empty():
                msg_t = self.recv_buffer.get()
                '''
                if msg_t.tag == Tags.APP_INI:
                    #TODO consider if not a complete command
                    comm_dict = json.loads(msg_t.sbuf)
                    self.appid = comm_dict['appid']
                    self.app_ini_task_lock.acquire()
                    self.app_ini_task = Task4Worker(0, comm_dict['app_init_boot'], comm_dict['app_init_data'], comm_dict['res_dir'])
                    self.app_ini_task_lock.release()
                    #self.task_queue.put_nowait(task)
                    #wake worker up and do app initialize
                    self.cond.acquire()
                    self.cond.notify()
                    self.cond.release()
                '''

                if msg_t.tag == Tags.TASK_ADD:
                    if self.task_queue.qsize() == self.capacity:
                        #TODO add error handler: out of queue bound
                        raise
                    comm_dict = json.loads(msg_t.sbuf)
                    task = Task4Worker(comm_dict['tid'], comm_dict['task_boot'], comm_dict['task_data'], comm_dict['res_dir'])
                    task.task_status = TaskStatus.SCHEDULED_HALT
                    self.task_queue.put_nowait(task.tid)
                    #self.task_list[task.tid] = task
                    if self.worker.status == WorkerStatus.IDLE:
                        self.cond.acquire()
                        self.cond.notify()
                        self.cond.release()



                elif msg_t.tag == Tags.TASK_REMOVE:
                    pass
                elif msg_t.tag == Tags.WORKER_STOP:
                    pass
                elif msg_t.tag == Tags.APP_FIN:
                    comm_dict = json.loads(msg_t.sbuf)
                    self.app_fin_task_lock.acquire()
                    self.app_fin_task = Task4Worker(0, comm_dict['app_fin_boot'], None, None)
                    self.app_fin_task_lock.release()
                    #self.task_queue.put_nowait(task)
                    self.worker.finialize = True
                    if self.worker.get_status() == WorkerStatus.IDLE:
                        self.cond.acquire()
                        self.cond.notify()
                        self.cond.release()
                    #self.worker.work_finalize()
                    #self.worker_status = WorkerStatus.IDLE

            # ask master for app fin, master may add new tasks or give stop order
            if self.task_queue.empty() == 0:
                #self.worker_status = WorkerStatus.IDLE
                while not self.task_completed_queue.empty():
                    tmp_task = self.task_completed_queue.get()
                    send_str = self.MSG_wrapper(wid=self.wid, tid=tmp_task.tid, time_start=tmp_task.time_start,
                                                time_fin=tmp_task.time_finish, status=tmp_task.task_status)
                    self.client.send_string(send_str, len(send_str), 0, Tags.TASK_FIN)
                self.client.send_int(self.appid, 1, 0 ,Tags.APP_FIN)
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

    def stop(self):
        BaseThread.stop()
        if self.heartbeat_thread:
            self.heartbeat_thread.stop()
        #TODO client stop

    def task_done(self, task):
        self.task_completed_queue.put_nowait(task)
        #self.task_list[task.tid] = task
        try:
            self.task_sync_lock.acquire()
            self.task_sync_flag = True
        finally:
            self.task_sync_lock.release()

    def app_ini_done(self):
        if self.task_completed_queue.qsize() > 0:
            task = self.task_completed_queue.get()
            if task.task_status == TaskStatus.COMPLETED:
                self.initialized = True
                send_str = self.MSG_wrapper(wid=self.wid, res_dir=task.res_dir)
                self.client.send_string(send_str, len(send_str), 0, Tags.APP_INI)
            else:
                # init error TODO and error handler and logging
                #self.worker_status = WorkerStatus.IDLE
                send_str = self.MSG_wrapper(wid=self.wid, res_dir=task.res_dir, error='initialize error')
                self.client.send_string(send_str, len(send_str), 0, Tags.APP_INI)
        else:
            #TODO can't find completed task error
            pass

    def app_fin_done(self):
        """
        finialize end, worker will diconnect from master (to be modified)
        :return:
        """
        if self.task_queue.empty() and self.task_completed_queue.qsize() > 0:
            self.task_completed_queue.get()

        self.client.send_int(self.wid, 1, 0, Tags.LOGOUT)


    def remove_task(self, taskid):
        pass

    def add_task(self, taskid , task):
        pass

#    def handler_recv(self, tags, pack):
#        msg = MSG(tags, pack)
#        self.recv_handler.MSGqueue.put_nowait(msg)

class Worker(BaseThread):
    """
    worker
    """
    def __init__(self,workagent, cond):
        BaseThread.__init__("worker")
        self.workagent = workagent
        self.current_task = None

        self.cond = cond

        self.initialized = False
        self.finialize = False
        self.status = None

    def run(self):
        #check worker agent's task queue, initial app
        while not self.initialized:
            self.status = WorkerStatus.NEW
            self.cond.acquire()
            self.cond.wait()
            self.cond.release()
            self.workagent.app_ini_task_lock.acquire()
            self.work_initial(self.workagent.app_ini_task)
            self.workagent.app_ini_task_lock.release()
            if self.initialized == False:
                continue


        while not self.get_stop_flag():
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
            if self.finialize:
                break

        #task = self.workagent.task_queue.get()
        self.workagent.app_fin_task_lock.acquire()
        self.work_finalize(self.workagent.app_fin_task)
        self.workagent.app_fin_task_lock.release()
        # TODO sleep or stop
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
        self.current_task = task
        #do the app init
        if not task.task_boot and not task.task_data:
            task.task_status = TaskStatus.COMPLETED
            self.initialized = True
        else:
            #TODO execuate the bash/.py
            if self.do_task(task) == 0:
                self.initialized = True
                self.status = WorkerStatus.INITILAZED
                task.task_status = TaskStatus.COMPLETED
            else:
                task.task_status =TaskStatus.FAILED
                self.status = WorkerStatus.IDLE
                self.initialized = False
        self.workagent.task_completed_queue.put(task)
        self.workagent.app_ini_done()
        #sleep
        if not self.initialized:
            self.cond.acquire()
            self.cond.wait()
            self.cond.release()


    def do_work(self, task):
        self.current_task = task
        return self.do_task(task)

    def work_finalize(self, fin_task):
        self.current_task = fin_task
        if fin_task.task_boot:
            self.do_task(fin_task)
            self.workagent.task_completed_queue.put(fin_task)
        self.status = WorkerStatus.COMPELETE
        self.workagent.app_fin_done()


    def stop(self):
        pass

    def get_status(self):
        return self.status



