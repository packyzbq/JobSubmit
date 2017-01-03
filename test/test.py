import threading
import time

class A(threading.Thread):
    def __init__(self, b):
        super(A,self).__init__(name="A")
        self.b = b
    def run(self):
        i = 0
        while i < 13:
            self.b.addval()
            time.sleep(1)
            i+=1
            print self.b.val

class B(threading.Thread):
    def __init__(self):
        super(B,self).__init__(name="B")
        self.val = 0

    def run(self):
        while True:
            if self.val > 5:
                print("hello")
                break

    def addval(self):
        self.val+=1

b = B()
a = A(b)
b.start()
a.start()