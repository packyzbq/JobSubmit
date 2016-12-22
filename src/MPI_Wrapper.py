import Server_Module as SM
import Client_Module as CM
import WorkerAgent
#Waring remember to add exception handler: try catch

class Tags:
    MPI_REGISTY = 11
    MPI_REGISTY_ACK = 12
    MPI_DISCONNECT = 13
###### NUM <100 for mpich ; NUM>= 100 for python
    WORKER_STOP =100


    TASK_FIN = 110      #w->m   client ask for new task
    TASK_SYNC = 111     #m<->w   master ask for work info
    APP_SCH_INI = 112   #m->w   master schedule app and transfer the init data
    TASK_ADD = 113      #m->w
    TASK_REMOVE = 114   #m->w   remove worker task, maybe give it to another worker
    APP_FIN = 115       #m->w   master tell worker how to finalize


class Client_recv_handler(CM.IRecvhandler):


class Server():
    """
    Set up a server using C++ lib
    """

    def initial(self, svcname):
        self.server = SM.MPI_Server(self, svcname)
        ret = self.server.initialize()
        if ret != 0:
            #TODO log init error

    def send(self):
        pass

    def command_analyze(self, command):
        pass





class Client():
    """
    Set up a client(workerAgent) using C++ lib
    """
    def __init__(self, workeragent, svcname, portname):

    def ping(self):
        # type: () -> object


    def send(self):
