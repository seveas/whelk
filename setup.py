#!/usr/bin/python

from distutils.core import setup

setup(name = "whelk",
      version = "2.7",
      author = "Dennis Kaarsemaker",
      author_email = "dennis@kaarsemaker.net",
      url = "http://github.com/seveas/whelk",
      description = "Easy access to shell commands from python",
      packages = ["whelk"],
      classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: zlib/libpng License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Libraries :: Python Modules',
      ]
)
