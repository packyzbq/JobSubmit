import subprocess
import os


subprocess.Popen("source  /afs/ihep.ac.cn/soft/juno/JUNO-ALL-SLC6/Release/J16v2r1/setup.sh")
if not os.environ.get('JUNOTESTROOT'):
    print 'source env error'
