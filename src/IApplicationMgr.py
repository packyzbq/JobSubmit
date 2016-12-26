import src.Master
from src.TaskInfo import Task

class Application:
    def __init__(self,app_id):
        self.app_id = app_id
        self.init_boot = None
        self.init_data = None

        self.task_list={}

        self.fin_boot = None
        self.fin_data = None


class IApplicationMgr:
    def __init__(self, master):
        self.master = master
        self.applist = {}  #id: app{ini_boot,inid_data}

    def init_app(self):
        """
        Read init_script, fill init_boot/data and fin_boot/data
        :return: application
        """
        pass

    def create_task(self, app_id):
        """
        create task list
        :return: list of tasks
        """""
        pass



class TestAppMgr(IApplicationMgr):
    def __init__(self, master):
        IApplicationMgr(master)
        self.__appid = 1
        self.__tid = 1

    def init_app(self):
        app = Application(self.__appid)
        self.applist[self.__appid] = app
        self.__appid += 1


    def create_task(self, app_id):
        tmp_task = Task(self.__tid)
        tmp_task.initial("$JUNOTESTROOT/python/JunoTest/junotest UnitTest JunoTest", "/home/cc/zhaobq")
        self.applist[app_id].task_list[tmp_task.tid] = tmp_task


