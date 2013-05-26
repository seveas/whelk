# whelk.py - A pythonic version of perl's 'use Shell;'
# (c) 2010-2012 Dennis Kaarsemaker <dennis@kaarsemaker.net>
#
# This script is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# version 3, as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

try:
    from collections import namedtuple
    Result = namedtuple('Result', ('returncode','stdout','stderr'))
except ImportError:
    # namedtuple only exists in 2.6+
    class Result(tuple):
        __slots__ = ()
        def __new__(cls, returncode, stdout, stderr):
            return tuple.__new__(cls, (returncode, stdout, stderr))
        def __repr__(self):
            return 'Result' + super(Result, self).__repr__()
        returncode = property(lambda self: self[0])
        stdout = property(lambda self: self[1])
        stderr = property(lambda self: self[2])
import os
import subprocess
import sys
import select

__all__ = ['shell','pipe','PIPE','STDOUT']
# Mirror some subprocess constants
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
PY3 = sys.version_info[0] == 3

# Output callbacks are only implemented for polling on POSIX systems
_output_callback_supported = sys.platform != 'mswindows' and hasattr(select, 'poll')

class Shell(object):
    """The magic shell class that finds executables on your $PATH"""
    # Mirror some module-level constants as we expect people to 'from shell
    # import shell'
    PIPE = PIPE
    STDOUT = STDOUT

    def __init__(self, **kwargs):
        self.defaults = kwargs

    def __getattr__(self, name):
        # Real functionality factored out for subclass purposes. super()
        # instances cannot really do __getattr__
        return self._getattr(name, defer=False)

    def __getitem__(self, name):
        return self._getitem(name, defer=False)

    def _getattr(self, name, defer):
        """Locate the command on the PATH"""
        try:
            return super(Shell, self).__getattribute__(name)
        except AttributeError:
            cmd = self._getitem(name, defer, try_path=False)
            if not cmd:
                raise
            return cmd

    def _getitem(self, name, defer, try_path=True):
        if try_path and '/' in name and os.access(name, os.X_OK):
            return Command(name,defer=defer,defaults=self.defaults)
        name_ = name.replace('_','-')
        for d in os.environ['PATH'].split(':'):
            p = os.path.join(d, name)
            if os.access(p, os.X_OK):
                return Command(p,defer=defer,defaults=self.defaults)
            # Try a translation from _ to - as python identifiers can't
            # contain -
            if name != name_:
                p = os.path.join(d, name_)
                if os.access(p, os.X_OK):
                    return Command(p,defer=defer,defaults=self.defaults)
        if try_path:
            raise KeyError("Command '%s' not found" % name)

class Pipe(Shell):
    """Shell subclass that returns defered commands"""
    def __getattr__(self, name):
        """Return defered commands"""
        return self._getattr(name, defer=True)

    def __getitem__(self, name):
        return self._getitem(name, defer=True)

    def __call__(self, cmd):
        """Run the last command in the pipeline and return data"""
        return cmd.run_pipe()

class Command(object):
    """A subprocess wrapper that executes the program when called or when
       combined with the or operator for pipes"""

    def __init__(self, name=None, defer=False, defaults={}):
        self.name = str(name)
        self.defer = defer
        self.defaults = defaults

    def __call__(self, *args, **kwargs):
        """Save arguments, execute a subprocess unless we need to be defered"""
        self.args = args
        # When not specified, make sure stdio is coming back to us
        kwargs['close_fds'] = True
        if kwargs.pop('redirect', True):
            for stream in ('stdin', 'stdout', 'stderr'):
                if stream not in kwargs:
                    kwargs[stream] = PIPE
        self.input = kwargs.pop('input','')
        self.encoding = kwargs.pop('encoding', self.defaults.get('encoding', None))
        # Backwards compatibility
        self.encoding = kwargs.pop('charset', self.encoding)
        if PY3 and hasattr(self.input, 'encode') and self.encoding:
            self.input = self.input.encode(self.encoding)
        self.defer = kwargs.pop('defer', self.defer)
        self.output_callback = kwargs.pop('output_callback', self.defaults.get('output_callback', None))
        self.output_callback_args = kwargs.pop('output_callback_args', self.defaults.get('output_callback_args', []))
        self.output_callback_kwargs = kwargs.pop('output_callback_kwargs', self.defaults.get('output_callback_kwargs', {}))
        if self.output_callback and not _output_callback_supported:
            raise EnvironmentError("Output callbacks are not supported on your system")

        self.kwargs = kwargs
        if PY3:
            all_kwargs = subprocess.Popen.__init__.__code__.co_varnames[2:subprocess.Popen.__init__.__code__.co_argcount]
        else:
            all_kwargs = subprocess.Popen.__init__.im_func.func_code.co_varnames[2:subprocess.Popen.__init__.im_func.func_code.co_argcount]
        for kwarg in all_kwargs:
            if kwarg in self.defaults and kwarg not in self.kwargs:
                self.kwargs[kwarg] = self.defaults[kwarg]

        if not self.defer:
            # No need to defer, so call ourselves
            sp = subprocess.Popen([str(self.name)] +
                    [str(x) for x in self.args], **(self.kwargs))
            sp.output_callback = self.output_callback
            sp.output_callback_args = self.output_callback_args
            sp.output_callback_kwargs = self.output_callback_kwargs
            (out, err) = sp.communicate(self.input)
            if PY3 and self.encoding:
                if hasattr(out, 'decode'):
                    out = out.decode(self.encoding)
                if hasattr(err, 'decode'):
                    err = err.decode(self.encoding)
            return Result(sp.returncode, out, err)
        # When defering, return ourselves
        self.next = self.prev = None
        return self

    def __or__(self, other):
        """Chain processes together and execute a subprocess for the first
           process in the chain"""
        # Can we chain the two together?
        if not isinstance(other, self.__class__):
            raise TypeError("Can only chain commands together")
        if not self.defer or not hasattr(self, 'next') or self.next:
            raise ValueError("Command not chainable or already chained")
        if not other.defer or not hasattr(other, 'prev') or other.prev:
            raise ValueError("Command not chainable or already chained")
        if not hasattr(self, 'args') or not hasattr(other, 'args'):
            raise ValueError("Command not called yet")
        # Can't chain something with input behind something else
        if hasattr(other, 'input') and other.input:
            raise ValueError("Cannot chain a command with input")
        # Yes, we can!
        self.next = other
        other.prev = self
        r, w = os.pipe()
        self.kwargs['stdout'] = PIPE
        self.sp = subprocess.Popen([str(self.name)] + [str(x) for x in self.args], **(self.kwargs))
        other.kwargs['stdin'] = self.sp.stdout
        return other

    def run_pipe(self):
        """Run the last command in the pipe and collect returncodes"""
        sp = subprocess.Popen([str(self.name)] + [str(x) for x in self.args], **(self.kwargs))
        sp.output_callback = self.output_callback
        sp.output_callback_args = self.output_callback_args
        sp.output_callback_kwargs = self.output_callback_kwargs

        # Ugly fudging of file descriptors to make communicate() work
        old_stdin = sp.stdin
        proc = self.prev
        input = ''
        while proc:
            sp.stdin = proc.sp.stdin
            input = proc.input
            if proc.sp.stdout:
                proc.sp.stdout.close()
                proc.sp.stdout = None
            if proc.sp.stderr:
                proc.sp.stderr.close()
                proc.sp.stderr = None
            proc = proc.prev

        (out, err) = sp.communicate(input)
        if PY3 and self.encoding:
            out = out.decode(self.encoding)
            err = err.decode(self.encoding)

        sp.stdin = old_stdin

        returncodes = [sp.returncode]
        proc = self.prev
        while proc:
            returncodes.insert(0, proc.sp.wait())
            proc = proc.prev
        return Result(returncodes, out, err)

# You really only need one Shell or Pipe instance, so let's create one and recommend to
# use it.
shell = Shell()
pipe = Pipe()

# Monkeypatch a method onto subprocess that allows callbacks to be called for
# each block of input. Copied from python2.7's subprocess.py and modified.
_PIPE_BUF = subprocess._PIPE_BUF
def _communicate_with_poll(self, input):
    stdout = None # Return
    stderr = None # Return
    fd2file = {}
    fd2output = {}

    poller = select.poll()
    def register_and_append(file_obj, eventmask):
        poller.register(file_obj.fileno(), eventmask)
        fd2file[file_obj.fileno()] = file_obj

    def close_unregister_and_remove(fd):
        poller.unregister(fd)
        fd2file[fd].close()
        fd2file.pop(fd)
        if self.output_callback:
            self.output_callback(self, fd, None, *self.output_callback_args, **self.output_callback_kwargs)

    if self.stdin and input:
        register_and_append(self.stdin, select.POLLOUT)

    select_POLLIN_POLLPRI = select.POLLIN | select.POLLPRI
    if self.stdout:
        register_and_append(self.stdout, select_POLLIN_POLLPRI)
        fd2output[self.stdout.fileno()] = stdout = []
    if self.stderr:
        register_and_append(self.stderr, select_POLLIN_POLLPRI)
        fd2output[self.stderr.fileno()] = stderr = []

    input_offset = 0
    while fd2file:
        try:
            ready = poller.poll()
        except select.error:
            e = sys.exc_info[1]
            if e.args[0] == errno.EINTR:
                continue
            raise

        for fd, mode in ready:
            if mode & select.POLLOUT:
                chunk = input[input_offset : input_offset + _PIPE_BUF]
                try:
                    input_offset += os.write(fd, chunk)
                except OSError as e:
                    if e.errno == errno.EPIPE:
                        close_unregister_and_remove(fd)
                    else:
                        raise
                else:
                    if input_offset >= len(input):
                        close_unregister_and_remove(fd)
            elif mode & select_POLLIN_POLLPRI:
                data = os.read(fd, 4096)
                if self.output_callback:
                    self.output_callback(self, fd, data, *self.output_callback_args, **self.output_callback_kwargs)
                if not data:
                    close_unregister_and_remove(fd)
                fd2output[fd].append(data)
            else:
                # Ignore hang up or errors.
                close_unregister_and_remove(fd)

    return (stdout, stderr)
subprocess.Popen._communicate_with_poll = _communicate_with_poll

# Testing is good. Must test.
if __name__ == '__main__':
    import unittest

    if PY3:
        b = lambda x: x.encode('latin-1')
    else:
        b = lambda x: x

    class ShellTest(unittest.TestCase):
        def test_notfound(self):
            # Non-existing command
            self.assertRaises(AttributeError, lambda: shell.cd)
            self.assertRaises(KeyError, lambda: shell['/not/found'])

        def test_basic(self):
            # Basic command test
            r = shell.ls('/')
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stderr, b(''))
            self.assertTrue(r.stdout != (''))

            v = '.'.join([str(x) for x in sys.version_info[:3]])
            r = shell[sys.executable]('-V')
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, b(''))
            self.assertTrue(b(v) in r.stderr)

            r = shell[os.path.basename(sys.executable)]('-V')
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, b(''))
            self.assertTrue(b(v) in r.stderr)

        def test_underscores(self):
            # Underscore-replacement
            c = shell.ssh_add
            self.assertTrue('ssh-add' in c.name)
            r = c('-l')
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stderr, b(''))
            self.assertTrue(r.stdout != b(''))

        def test_pipes(self):
            # Test basic pipe usage
            r = pipe(pipe.ls('/') | pipe.grep('-v', 'bin') | pipe.rot13() | pipe.rot13())
            self.assertEqual(r.returncode, [0,0,0,0])
            self.assertTrue(b('bin') not in r.stdout)
            self.assertEqual(r.stderr, b(''))

        def test_pipe_madness(self):
            # Test broken usage
            self.assertRaises(TypeError, lambda: pipe.cat() | None)
            self.assertRaises(ValueError, lambda: pipe.cat() | shell.ls)
            self.assertRaises(ValueError, lambda: shell.ls | pipe.cat())
            self.assertRaises(ValueError, lambda: pipe.ls | pipe.cat())
            self.assertRaises(ValueError, lambda: pipe.ls() | pipe.cat)

        def test_pipe_oneprocess(self):
            # Name says all
            r = pipe(pipe.ls('/'))
            self.assertEqual(r.returncode, [0])
            self.assertEqual(r.stderr, b(''))
            self.assertTrue(r.stdout != b(''))

        def test_pipe_stderr(self):
            # Stderr redirection in the middle of the pipe
            r = pipe(pipe.echo("Hello, world!") | pipe.grep("--this-will-not-work", stderr=STDOUT) | pipe.cat())
            self.assertEqual(r.returncode[0], 0)
            self.assertTrue(r.returncode[1] > 1)
            self.assertEqual(r.returncode[2], 0)
            self.assertTrue(b('this-will-not-work') in r.stdout)
            self.assertEqual(r.stderr, b(''))

        def test_stderr(self):
            # Command with stderr
            r = shell.ls('/does/not/exist')
            self.assertTrue(r.returncode != 0)
            self.assertEqual(r.stdout, b(''))
            self.assertTrue(r.stderr != b(''))

        def test_withinput(self):
            # with inputstring
            inp = b('Hello, world!')
            r = shell.cat(input=inp)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(inp, r.stdout)
            self.assertEqual(b(''), r.stderr)

        def test_withio(self):
            # Use open filehandles
            fd = open('/etc/resolv.conf', 'rb')
            data = fd.read()
            fd.seek(0)
            r = shell.rot13(stdin=fd)
            fd.close()
            self.assertEqual(r.returncode, 0)
            if PY3:
                rot13 = bytes.maketrans(b('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                                        b('nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM'))
                self.assertEqual(data.translate(rot13), r.stdout)
            else:
                self.assertEqual(data.encode('rot13'), r.stdout)
            self.assertEqual(r.stderr, b(''))

        def test_withoutredirect(self):
            # Run something with redirect=False
            r = shell.echo("-n",".", redirect=False)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, None)
            self.assertEqual(r.stderr, None)

        def test_pipewithinput(self):
            input = b("Hello, world!")
            r = pipe(
                pipe.caesar(10, input=input) |
                pipe.caesar(10) |
                pipe.caesar(6)
            )
            self.assertEqual(r.returncode, [0,0,0])
            self.assertEqual(r.stdout, input)
            self.assertEqual(r.stderr, b(''))

        def test_pipewithhugeinput(self):
            input = b("123456789ABCDEF") * 1024
            r = pipe(
                pipe.caesar(10, input=input) |
                pipe.caesar(10) |
                pipe.caesar(6)
            )
            self.assertEqual(r.returncode, [0,0,0])
            self.assertEqual(r.stdout, input)
            self.assertEqual(r.stderr, b(''))

        def test_encoding(self):
            input = "Hello, world!"
            r = pipe(
                pipe.caesar(10, input=input, encoding='utf-8') |
                pipe.caesar(10) |
                pipe.caesar(6, encoding='utf-8')
            )
            self.assertEqual(r.returncode, [0,0,0])
            self.assertEqual(r.stdout, input)
            self.assertEqual(r.stderr, '')

            r = shell.rot13(input=input, encoding='utf-8')
            self.assertEqual(r.returncode, 0)
            if PY3:
                rot13 = str.maketrans('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
                                         'nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM')
                self.assertEqual(input.translate(rot13), r.stdout)
            else:
                self.assertEqual(input.encode('rot13'), r.stdout)
            self.assertEqual(r.stderr, '')

        def test_encoding2(self):
            input = '\u041f\u0440\u0438\u0432\u0435\u0442, \u043c\u0438\u0440!'
            s = Shell(encoding='utf-8')
            r = s.cat(input=input)
            self.assertEqual(input, r.stdout)

        def test_callback(self):
            chunks = []
            seen_eof = {}
            def cb(sp, fd, data, *args, **kwargs):
                if data is None:
                    seen_eof[fd] = True
                    return
                chunks.append(data)
            r = shell.dmesg(output_callback=cb)
            self.assertEqual(r.returncode, 0)
            self.assertTrue(len(chunks) > 1)
            self.assertEqual(r.stdout, b('').join(chunks))
            self.assertEqual(list(seen_eof.values()), [True, True])

        def test_defaults(self):
            s = Shell(stdout = shell.STDOUT)
            input = b("Testing 1 2 3")
            r = s.cat(input=input)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, input)

    unittest.main()
