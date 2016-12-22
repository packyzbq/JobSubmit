from src.BaseThread import BaseThread
from src.MPI_Wrapper import Client
import Client_Module as CM
from src.MPI_Wrapper import Tags
import time
import Queue
import os,sys

# constants
miliseconds = 1000
delay = 10 #interval = 10s

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

class WorkerAgent(BaseThread, CM.IRecvhandler):
    """
    agent
    """
    def __init__(self, wid, svcname):
        BaseThread.__init__(self, name='worker'+wid)
        import uuid as uuid_mod
        self.uuid = str(uuid_mod.uuid4())
        self.client = Client(self, svcname, "")
        self.wid = wid
        self.capacity = 5                   # can change
        self.task_queue=Queue.Queue(maxsize=self.capacity) #need lock
        self.current_task = None

        self.heartbeat_thread=None
        self.worker_thread=None

        # init_data finalize_bash result dir can be store in Task object
        #self.init_bash = None
        #self.finalize_bash = None

        #self.res_dir=None

    def __getstate__(self):


    def register(self):
        pass

    def run(self):
        # use while to check receive buffer or Client buffer

    def finalize_run(self):

    def stop(self):
        BaseThread.stop()
        if self.heartbeat_thread:
            self.heartbeat_thread.stop()
        #TODO client stop

    def kill(self):
        pass

    def remove_task(self, taskid):

    def add_task(self,taskid , task):

    def handler_recv(self, tags, pack):
        if tags == Tags.WORKER_STOP:
            pass
        elif tags == Tags.MPI_REGISTY_ACK:
            pass

class Worker(BaseThread):
    """
    worker
    """
    def __init__(self,workagent):
        BaseThread.__init__("worker")
        self.workagent = workagent
        self.mytask = None

    def run(self):
        #check worker agent's task queue

    def work_initial(self):
        pass

    def do_work(self):
        pass

    def work_finalize(self):
        pass

    def stop(self):
        pass




