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

If you want to tinker with the source, you can install the latest source from
github::

  git clone https://github.com/seveas/whelk.git

And finally, Ubuntu users can install whelk from my ppa::

  sudo apt-add-repository ppa:dennis/python
  sudo apt-get update
  sudo apt-get install python-whelk python3-whelk

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
:class:`Popen` object::

    result = shell.netstat('-tlpn')
    result = shell.git('status', cwd='/home/dennis/code/whelk')
    result = shell['2to3']('awesome.py')
    result = shell['./Configure']('-des', '-Dusedevel')

Oh, and on windows you can leave out the :data:`.exe` suffix, like you would on
the command line as well::

    result = shell.nmake('test')

Shell commands return a namedtuple :data:`(returncode, stdout, stderr)` These
result objects can also be used as booleans. As in shellscript, a non-zero
returncode is consifered :data:`False` and a returncode of zero is considered
:data:`True`, so this simply works::

    result = shell.make('test'):
    if not result:
        print("You broke the build!")
        print(result.stderr)

The result of :data:`pipe(...)` is slightly different: instead of a single return
code, it actually will give you a list of returncodes of all items in the
pipeline. Result objects like this are only considered :data:`True` if all
elements are zero.

Keyword arguments
-----------------

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

  The reason this is not the default, is that for quite a few commands a
  non-zero exitcode, does not indicate an error at all. For example, the
  venerable :data:`diff` command returns 1 if there is a change and 0 if there
  is none.

* :data:`exit_callback`

  If you want slightly more fine-grained control than :data:`raise_on_error`,
  you can use this argument to specify a callable to call whenever a process
  exits, irrespective of the returncode. The callback will be called with as
  arguments the command instance, the subprocess, the result tuple and any
  user-provided arguments.

  Both :data:`raise_on_exit` and :data:`exit_callback` are most useful when set
  as a default of a :class:`Shell` instance, they are not really needed when
  calling single commands.

  Here's a real life example of an exit callback, which will retry git
  operations when the break due to repository locks::

    def check_sp(command, sp, res):
        if not res:
            if 'index.lock' in res.stderr:
                # Let's retry
                time.sleep(random.random())
                return command(*command.args, **command.kwargs)
            raise RuntimeError("%s %s failed: %s" % (command.name, ' '.join(command.args), res.stderr))

    git = Shell(exit_callback=check_lock).git
    git.checkout('master')

* :data:`run_callback`

  A function that will be called whenever the shell instance is about to create
  a new process. The callback will be called with as arguments  the command
  instance and any user-provided arguments. Here's an example that logs all
  starts of applications::

    def runlogger(cmd):
        args = [cmd.name] + list(cmd.args)
        env = cmd.sp_kwargs.get('env', '')
        if env:
            env = ['%s=%s' % (x, env[x]) for x in env if env[x] != os.environ.get(x, None)]
            env = '%s ' % ' '.join(env)
        logger.debug("Running %s%s" % (env, ' '.join(args)))

    shell = Shell(run_callback=runlogger)

* :data:`encoding`

  On python 3, subprocesses require :class:`bytes` objects as input and will
  return :class:`bytes` objects as output. You can specify an encoding for a
  command to make whelk do the encoding/decoding for you::

    kernel_says = shell.dmesg('-t', encoding='latin-1')

  On python 2, this keyword is ignored ans whelk will leave your data alone.

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
   shell = Shell(stderr=Shell.STDOUT, env=my_env, encoding='utf8')

   shell.wget("http://google.com", "-o", "google.html")

Python compatibility
--------------------
Whelk is compatible with python 2.4 and up, including python 3. If you find an
incompatibility, please report a bug at https://github.com/seveas/whelk.
