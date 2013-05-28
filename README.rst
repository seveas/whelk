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

If your command is not valid as a python identifier, even after substituting
dashes for underscores, you can using the :class:`shell` object as a dict. This
dict also accepts full paths to commands, even if they are not on your
:data:`$PATH`.

Attributes of the :class:`shell` instance are all callables. Arguments to this
callable get mapped to arguments to the command via a :class:`subprocess.Popen`
object. Keyword arguments get mapped to keyword arguments for the
:class:`Popen` object.  Shell commands return a namedtuple :data:`(returncode,
stdout, stderr)`::

    result = shell.netstat('-tlpn')

    result = shell.git('status', cwd='/home/dennis/code/whelk')

    result = shell['2to3']('awesome.py')

    result = shell['./Configure']('-des', '-Dusedevel')

In addition to the :class:`subprocess.Popen` arguments, whelk supports a few
more keyword arguments:

* :data:`input`

  Contrary to the :mod:`subprocess` defaults, :data:`stdin`, :data:`stdout`
  and :data:`stderr` are set to :data:`whelk.PIPE` by default. Input for the
  command can be passed as the :data:`input` keyword parameter.

  Some examples::

    result = shell.cat(input="Hello world!")

    result = shell.vipe(input="Some data I want to edit in an editor")

* :data:`output_callback`

  To process output as soon as it arrives, specify a callback to use. Whenever
  output arrives, this callback will be called with as arguments the shell
  instance, the subprocess, the filedescriptor the data came in on, the actual
  data (or :data:`None` in case of EOF) and any user-specified arguments .
  Here's an example that uses this feature for logging::

    def cb(shell, sp, fd, data, extra=""):
        if data is None:
            logging.debug("%s<%d:%d> File descriptor closed" % (extra, sp.pid, fd))
        for line in data.splitlines():
            logging.debug("%s<%d:%d> %s" % (extra, sp.pid, fd, line))

    shell.dmesg(output_callback=cb)
    shell.mount(output_callback=[cb, "Mountpoints: "])

* :data:`raise_on_error`

  This makes your shell even more pythonic: instead of returning an errorcode,
  a :class:`CommandFailed` exception is raised whenever a command returns with
  a nonzero exitcode.

* :data:`exit_callback`

  If you want slightly more fine-grained control than :data:`raise_on_error`,
  you can use this argument to specify a callable to call whenever a process
  exits, irrespective of the returncode. The callback will be called with as
  arguments the shell instance, the subprocess, the result tuple and any
  user-provided arguments.

  Both :data:`raise_on_exit` and :data:`exit_callback` are ost useful when set
  as a default of a :class:`Shell` instance, they are not really needed when
  calling single commands.


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

Setting default arguments
-------------------------
If you want to launch many commands with the same parameters, you can set
defaults by passing parameters to the :class:`Shell` constructor. These are
passed on to all commands launched by that shell, unless overridden in specific
calls::

   from whelk import Shell
   my_env = os.environ.copy()
   my_env['http_proxy'] = 'http://webproxy.corp:3128'
   shell = Shell(stderr=Shell.STDOUT, env=my_env)

   shell.wget("http://google.com", "-o", "google.html")

Python compatibility
--------------------
Whelk is compatible with python 2.4 and up, including python 3. If you find an
incompatibility, please report a bug at https://github.com/seveas/whelk.

Note that on python 3, subprocesses require :class:`bytes` objects as input and
will return :class:`bytes` objects as output. You can specify an encoding for a
command to make whelk do the encoding/decoding for you::

  kernel_says = shell.dmesg('-t', encoding='latin-1')

You can also make all commands launched by a Shell instance do this::

  from whelk import Shell
  shell = Shell(encoding='utf-8')
  kernel_says = shell.dmesg('-t')
