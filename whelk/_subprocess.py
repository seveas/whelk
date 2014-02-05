import subprocess
import sys

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT

# Popen.communicate gets reimplemented sometimes. These implementations ensure
# compatibility from python 2.4 up to 3.4
if sys.version_info[:2] < (3,3):
    from whelk.subprocess_32 import Popen
elif sys.version_info[:2] == (3,3):
    from whelk.subprocess_33 import Popen
else:
    from whelk.subprocess_34 import Popen
