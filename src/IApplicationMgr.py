import src.Master
from src.TaskInfo import Task
from src.TaskInfo import TaskStatus

class Application:
    def __init__(self,app_id, name):
        self.app_id = app_id
        self.app_name=name
        self.init_boot = None
        self.init_data = None

        self.task_list={} #tid:task

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

    def check_init_res(self, wid, res_dir):
        """

        :param wid:
        :param res_dir:
        :return: True/False
        """
        return True

    def check_task_res(self, wid, tid, res_dir):
        pass



class TestAppMgr(IApplicationMgr):
    def __init__(self, master):
        IApplicationMgr(master)
        self.__appid = 1
        self.__tid = 1

        self.assign_list = {}

    def init_app(self):
        app = Application(self.__appid)
        self.applist[self.__appid] = app
        self.assign_list[self.__appid] = []
        self.__appid += 1


    def create_task(self, app_id):
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

    def finilize(self):
        pass

    def get_app_init(self, wid):
        for k in self.assign_list.keys():
            if wid not in self.assign_list[k]:
                self.assign_list[k].append(wid)
                return k, self.applist[k].init_boot, self.applist[k].init_data

    def get_app_fin(self, appid):
        return self.applist[appid].fin_boot, self.applist[appid].fin_data
