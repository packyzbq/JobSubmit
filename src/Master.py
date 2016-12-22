import Server_Module as SM
import src.MPI_Wrapper

class Master(SM.IRecvhandler):

    # server= MPI_Server(self, "svcname")

    def handler_recv(self, tags, pack):
        if tags == src.Tags.MPI_REGISTY:
            pass
        elif tags == src.Tags.TASK_SYNC:
            pass
        elif tags == src.Tags.TASK_FIN:
            pass