#!/usr/bin/python

from distutils.core import setup

setup(name = "whelk",
      version = "1.3",
      author = "Dennis Kaarsemaker",
      author_email = "dennis@kaarsemaker.net",
      url = "http://github.com/seveas/whelk",
      description = "Easy access to shell commands from python",
      py_modules = ["whelk"],
      classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Libraries :: Python Modules',
      ]
)
