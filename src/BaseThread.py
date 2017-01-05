import threading
import logging

class BaseThread(threading.Thread):
    """
    Master Worker Base thread class
    """
    def __init__(self, name=None):
        super(BaseThread, self).__init__(name=name)
        self.setDaemon(1)
        self.__should_stop_flag = False
        #TODO add log output: BaseThread object create:self.__class__.__name__

    def get_stop_flag(self):
        return self.__should_stop_flag

    def stop(self):
        if not self.__should_stop_flag:
            #TODO add log: Stopping thread:
            self.__should_stop_flag = True

