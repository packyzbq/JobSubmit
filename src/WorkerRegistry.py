import sys
import time
import Queue
import threading

LOST_WORKER_TIMEOUT = 10 # lost worker when overhead this thrashold

class WorkerStatus:
    NEW = -1
    INITILAZED = 0
    IDLE = 1
    RUNNING = 2
    ERROR = 3
    LOST = 4

class WorkerEntry:
    """
    contain worker information and task queue
    """
    def __int__(self, wid, w_uuid, max_capacity):
        self.wid = wid
        self.w_uuid = w_uuid
        self.registration_time = time.time()
        self.last_contact_time = self.registration_time
        self.idle_time = 0
        self.max_capacity = max_capacity
        self.worker_status=None

        self.initialized = False

        self.processing_task = None
        self.scheduled_tasks = Queue.Queue()

        self.alive = True
        #LOCK ?

    def capacity(self):
        return self.max_capacity-self.scheduled_tasks.qsize()

    def lost(self):
        return time.time()-self.last_contact_time > LOST_WORKER_TIMEOUT

#    def getStatusReport(self):
#       return "wid=%d alive = %d registered %s last_contact %s (%f seconds ago)\n" % \
#               (self.wid, self.alive, self.registration_time, \
#                self.last_contact_time, \
#                time.time() - self.last_contact_time)

class WorkerRegisty:
    def __int__(self):
        self.__all_workers={}           # w_id:registryEntry
        self.__all_workers_uuid={}      # w_uuid:wid
        self.last_wid= 0;
        self.lock = threading.RLock()

        self.__waiting_workers = {}     # w_uuid:wid
        self.__alive_workers = {}       # w_uudi:wid

    def add(self, wid, w_uuid, max_capacity):
        self.lock.acquire()
        try:
            if self.__alive_workers.has_key(w_uuid):
                wid = self.__all_workers_uuid[w_uuid]
                #TODO logging warning
                return None
            else:
                self.last_wid+=1
                newid = self.last_wid
                w = WorkerEntry(newid,w_uuid, max_capacity)
                self.__all_workers[newid] = w
                self.__all_workers_uuid[w_uuid] = newid
                self.__alive_workers.append(w_uuid)
                #TODO logging
            return w
        except:
            #TODO logging
            pass
        finally:
            self.lock.release()

    def remove(self,wid):
        try:
            self.lock.acquire()
            try:
                w_uuid = self.__all_workers[wid].w_uuid
            except KeyError:
                #TODO log
                pass
            else:
                #TODO log
                self.__all_workers[wid].alive = False
                self.__alive_workers.remove(wid)
        finally:
            self.lock.release()