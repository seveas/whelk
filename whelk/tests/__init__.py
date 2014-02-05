from whelk import *
import unittest
import sys, os

PY3 = sys.version_info[0] == 3
if PY3:
    b = lambda x: x.encode('latin-1')
else:
    b = lambda x: x
