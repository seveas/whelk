# whelk.py - A pythonic version of perl's 'use Shell;'
# (c) 2010-2012 Dennis Kaarsemaker <dennis@kaarsemaker.net>
#
# This library is free software; you can redistribute it and/or
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
import whelk._subprocess as subprocess
import sys
Popen = subprocess.Popen

__all__ = ['Shell', 'Pipe', 'shell', 'pipe', 'PIPE', 'STDOUT', 'CommandFailed']
# Mirror some subprocess constants
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
PY3 = sys.version_info[0] == 3

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
        self.args = args[:]
        self.kwargs = kwargs.copy()

        # When not specified, make sure stdio is coming back to us
        kwargs['close_fds'] = True
        if kwargs.pop('redirect', self.defaults.get('redirect', True)):
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
        if callable(self.output_callback):
            self.output_callback = [self.output_callback]
        if self.output_callback and not Popen.output_callback_supported:
            raise EnvironmentError("Output callbacks are not supported on your system")
        self.exit_callback = kwargs.pop('exit_callback', self.defaults.get('exit_callback', None))
        if callable(self.exit_callback):
            self.exit_callback = [self.exit_callback]
        self.run_callback = kwargs.pop('run_callback', self.defaults.get('run_callback', None))
        if callable(self.run_callback):
            self.run_callback = [self.run_callback]
        self.raise_on_error = kwargs.pop('raise_on_error', self.defaults.get('raise_on_error', False))

        self.sp_kwargs = kwargs
        if PY3:
            all_kwargs = Popen.__init__.__code__.co_varnames[2:Popen.__init__.__code__.co_argcount]
        else:
            all_kwargs = Popen.__init__.im_func.func_code.co_varnames[2:Popen.__init__.im_func.func_code.co_argcount]
        for kwarg in all_kwargs:
            if kwarg in self.defaults and kwarg not in self.sp_kwargs:
                self.sp_kwargs[kwarg] = self.defaults[kwarg]

        if not self.defer:
            # No need to defer, so call ourselves
            if self.run_callback:
                self.run_callback[0](self, *self.run_callback[1:])
            sp = Popen([str(self.name)] + [str(x) for x in self.args], **(self.sp_kwargs))
            sp.output_callback = self.output_callback
            sp.shell = self
            (out, err) = sp.communicate(self.input)
            if PY3 and self.encoding:
                if hasattr(out, 'decode'):
                    out = out.decode(self.encoding)
                if hasattr(err, 'decode'):
                    err = err.decode(self.encoding)
            res = Result(sp.returncode, out, err)
            if self.exit_callback:
                self.exit_callback[0](self, sp, res, *self.exit_callback[1:])
            if self.raise_on_error and res.returncode:
                raise CommandFailed(res)
            return res
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
        self.sp_kwargs['stdout'] = PIPE
        if self.run_callback:
            self.run_callback[0](self, *self.run_callback[1:])
        self.sp = Popen([str(self.name)] + [str(x) for x in self.args], **(self.sp_kwargs))
        self.sp.shell = self
        other.sp_kwargs['stdin'] = self.sp.stdout
        return other

    def run_pipe(self):
        """Run the last command in the pipe and collect returncodes"""
        if self.run_callback:
            self.run_callback[0](self, *self.run_callback[1:])
        sp = Popen([str(self.name)] + [str(x) for x in self.args], **(self.sp_kwargs))
        sp.shell = self
        sp.output_callback = self.output_callback

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
        res = Result(returncodes, out, err)
        if self.exit_callback:
            self.exit_callback[0](self, sp, res, *self.exit_callback[1:])
        if self.raise_on_error and res.returncode.count(0) != len(res.returncode):
            raise CommandFailed(res)
        return res

class CommandFailed(RuntimeError):
    def __init__(self, result):
        self.result = result
        return super(CommandFailed, self).__init__(result.stderr)

# You really only need one Shell or Pipe instance, so let's create one and recommend to
# use it.
shell = Shell()
pipe = Pipe()
