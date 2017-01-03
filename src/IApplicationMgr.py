from src.TaskInfo import Task
from src.TaskInfo import TaskStatus

class Application:
    def __init__(self):
        self.app_id = None
        self.app_name= None
        self.init_boot = None
        self.init_data = None

        self.task_list={} #tid:task

        self.fin_boot = None
        self.fin_data = None

    def initialize(self, appid, name):
        pass

    def finalize(self):
        pass

    def merge(self):
        pass


class IApplicationMgr:
    def __init__(self, master):
        self.master = master
        self.applist = {}  #id: app{ini_boot,inid_data}

    def add_app(self, application):
        """
        add application into mgr applist, application must be initialized
        :param application:
        :return:
        """
        pass

    def create_task(self, app_id):
        """
        create task list
        :return: list of tasks
        """""
        pass

    def check_init_res(self, wid, res_dir):
        """

        :param wid:
        :param res_dir:
        :return: True/False
        """
        return True

    def check_fin_res(self, wid, res_dir):
        pass

    def check_task_res(self, wid, tid, res_dir):
        pass

    def task_done(self, app_id, task):
        raise NotImplementedError



class TestAppMgr(IApplicationMgr):
    def __init__(self, master):
        IApplicationMgr(master)
        self.__appid = 1
        self.__tid = 1

        self.assign_list = {} #appid: app

    def init_app(self):
        app = Application(self.__appid)
        self.applist[self.__appid] = app
        self.assign_list[self.__appid] = []
        self.__appid += 1

    def add_app(self, application):
        self.applist[self.__appid] = application
        self.__appid+=1


    def create_task(self, app_id):
        assert self.applist.has_key(app_id)
        if self.applist[app_id].task_list:
            return
        tmp_task = Task(self.__tid)
        tmp_task.initial("$JUNOTESTROOT/python/JunoTest/junotest UnitTest JunoTest", "/home/cc/zhaobq")
        self.applist[app_id].task_list[tmp_task.tid] = tmp_task

    def get_task(self, appid, tid):
        return self.applist[appid].task_list[tid]


    def task_done(self, app_id, task):
        #TODO
        if task.status == TaskStatus.FAILED:
            print self.applist[app_id].name+" task error"
        else:
            print self.applist[app_id].name + " task finished completed"

    def finilize(self, appid):
        self.applist[appid].merge()

    def get_app_init(self, appid):
        return self.applist[appid].init_boot, self.applist[appid].init_data

    def get_app_fin(self, appid):
        return self.applist[appid].fin_boot, self.applist[appid].fin_data


def runfile_analyzer(runfile):
    pass