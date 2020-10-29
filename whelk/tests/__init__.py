from whelk import *
import unittest
import sys, os

os.environ['PATH'] = os.pathsep.join([
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin'),
    os.environ['PATH']
])
