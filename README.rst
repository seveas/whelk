Pretending python is a shell
============================

We all like python for scripting, because it's so much more powerful than a
shell. But sometimes we really need to call a shell command because it's so
much easier than writing yet another library in python or adding a dependency::

  from whelk import shell
  shell.zgrep("-r", "downloads", "/var/log/httpd")
  # Here goes code to process the log

You can even pipe commands together::

  from whelk import pipe
  pipe(pipe.getent("group") | pipe.grep(":1...:"))

Installing
----------

Installing the latest released version is as simple as::

  pip install whelk

This downloads it from PyPI and installs it for you. Alternatively, you can
download the tarball manually from
http://pypi.python.org/packages/source/w/whelk/, extract it and run::

  python setup.py install

If you want to tinker with the source, you can install the latest source from
github::

  git clone https://github.com/seveas/whelk.git

Calling a command
-----------------

The :class:`whelk.shell` object can be used to call any command on your
:data:`$PATH` that is also a valid python identifier. Since many commands
contain a "-", it will find those even if you spell it with a "_". So e.g.
:file:`run-parts` can be found as :func:`shell.run_parts`.

Attributes of the :class:`shell` instance are all callables. Arguments to this
callable get mapped to arguments to the command via a :class:`subprocess.Popen`
object. Keyword arguments get mapped to keyword arguments for the
:class:`Popen` object.

One important difference is that :data:`stdin`/:data:`stdout`/:data:`stderr`
are set to :data:`whelk.PIPE` by default. Input for the command can be passed
as the :data:`input` keyword parameter.

Some examples::

  result = shell.cat(input="Hello world!")
  
  result = shell.vipe(input="Some data I want to edit in an editor")

Shell commands return a namedtuple :data:`(returncode, stdout, stderr)`.

Piping commands together
------------------------

The :class:`whelk.pipe` object is similar to the :class:`shell` object but has
a few significant differences:

* :class:`pipe` commands can be chained with :data:`|` (binary or), resembling
  a shell pipe. :class:`pipe` takes care of the I/O redirecting.
* The command is not started immediately, but only when wrapping it in another
  :func:`pipe` call (yes, the object itself is callable), or chaining it to the
  next.
* In the result tuple, the returncode is actually a list of returncodes of all
  the processes in the pipe, in the order they are executed in.
* The only I/O redirection you may want to override is
  :data:`stderr=whelk.STDOUT`, or :data:`stderr=open('/dev/null', 'w')` to
  redirect :data:`stderr` of a process to :data:`stdin` of the next process, or
  :file:`/dev/null` respectively.

Some examples::

  result = pipe(pipe.dmesg() | pipe.grep('Bluetooth'))

  cow = random.choice(os.listdir('/usr/share/cowsay/cows'))
  result = pipe(pipe.fortune("-s") | pipe.cowsay("-n", "-f", cow))

Python compatibility
--------------------
Whelk is compatible with python 2.4 and up, including python 3. If you find an
incompatibility, please report a bug at https://githiub.com/seveas/whelk.

Note that on python 3, subprocesses require :class:`bytes` objects as input and
will return :class:`bytes` objects as output.
