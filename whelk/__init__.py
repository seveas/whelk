# whelk.py - Pretending python is a shell
# Copyright (c) 2010-2015 Dennis Kaarsemaker <dennis@kaarsemaker.net>
# All rights reserved.
# 
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
# 
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.
# 
# THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR
# OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.

class Result(tuple):
    __slots__ = ()
    def __new__(cls, returncode, stdout, stderr):
        return tuple.__new__(cls, (returncode, stdout, stderr))
    def __repr__(self):
        return 'Result' + super(Result, self).__repr__()
    returncode = property(lambda self: self[0])
    stdout = property(lambda self: self[1])
    stderr = property(lambda self: self[2])
    def __nonzero__(self):
        if isinstance(self.returncode, int):
            return self.returncode == 0
        return self.returncode.count(0) == len(self.returncode)
    __bool__ = __nonzero__

import os
import subprocess
import sys
import threading
Popen = subprocess.Popen

__all__ = ['Shell', 'Pipe', 'shell', 'pipe', 'PIPE', 'STDOUT', 'DEVNULL', 'CommandFailed']
# Mirror some subprocess constants
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
DEVNULL = subprocess.DEVNULL

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
        for d in os.environ['PATH'].split(os.pathsep):
            if d.endswith('"') and d.startswith('"'):
                d=d[1:-1]
            if sys.platform == 'win32' and not name.endswith('.exe'):
                p = os.path.join(d, name) + '.exe'
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return Command(p,defer=defer,defaults=self.defaults)
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
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
    """Shell subclass that returns deferred commands"""
    def __getattr__(self, name):
        """Return deferred commands"""
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
        """Save arguments, execute a subprocess unless we need to be deferred"""
        self.args = args[:]
        self.kwargs = kwargs.copy()

        # When not specified, make sure stdio is coming back to us
        if kwargs.pop('redirect', self.defaults.get('redirect', True)):
            for stream in ('stdin', 'stdout', 'stderr'):
                if stream not in kwargs:
                    kwargs[stream] = PIPE

        # close_fds is not supported under windows when redirecting stdin/out/err
        if sys.platform != 'win32' or (kwargs.get('stdin'), kwargs.get('stdout', None), kwargs.get('stderr', None)).count(None) == 3:
            kwargs['close_fds'] = True

        self.input = kwargs.pop('input','')
        self.encoding = kwargs.get('encoding', self.defaults.get('encoding', None))
        self.errors = kwargs.get('errors', self.defaults.get('errors', None))
        self.text = kwargs.get('text', self.defaults.get('text', None))
        # Backwards compatibility
        self.encoding = kwargs.get('charset', self.encoding)
        self.defer = kwargs.pop('defer', self.defer)
        self.output_callback = kwargs.pop('output_callback', self.defaults.get('output_callback', None))
        if callable(self.output_callback):
            self.output_callback = [self.output_callback]
        self.exit_callback = kwargs.pop('exit_callback', self.defaults.get('exit_callback', None))
        if callable(self.exit_callback):
            self.exit_callback = [self.exit_callback]
        self.run_callback = kwargs.pop('run_callback', self.defaults.get('run_callback', None))
        if callable(self.run_callback):
            self.run_callback = [self.run_callback]
        self.raise_on_error = kwargs.pop('raise_on_error', self.defaults.get('raise_on_error', False))

        stdout_reader = stderr_reader = None
        if self.output_callback:
            if kwargs['stdout'] == PIPE:
                stdout_reader = ReaderThread(self)
                kwargs['stdout'] = stdout_reader.writefd
            if kwargs['stderr'] == PIPE:
                stderr_reader = ReaderThread(self)
                kwargs['stderr'] = stderr_reader.writefd

        self.sp_kwargs = kwargs
        all_kwargs = Popen.__init__.__code__.co_varnames[2:Popen.__init__.__code__.co_argcount] + tuple(Popen.__init__.__kwdefaults__)
        for kwarg in all_kwargs:
            if kwarg in self.defaults and kwarg not in self.sp_kwargs:
                self.sp_kwargs[kwarg] = self.defaults[kwarg]

        if not self.defer:
            # No need to defer, so call ourselves
            if self.run_callback:
                self.run_callback[0](self, *self.run_callback[1:])
            sp = Popen([str(self.name)] + [str(x) for x in self.args], **(self.sp_kwargs))
            if stdout_reader:
                stdout_reader.set_process(sp)
            if stderr_reader:
                stderr_reader.set_process(sp)
            (out, err) = sp.communicate(self.input)
            if stdout_reader:
                stdout_reader.thread.join()
                out = stdout_reader.output
            if stderr_reader:
                stderr_reader.thread.join()
                err = stderr_reader.output
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

class ReaderThread:
    def __init__(self, shell):
        self.readfd, self.writefd = os.pipe()
        if shell.encoding or shell.text:
            self.readfd = os.fdopen(self.readfd, 'r', encoding=shell.encoding, errors=shell.errors)
            self.writefd = os.fdopen(self.writefd, 'w', encoding=shell.encoding, errors=shell.errors)
        else:
            self.readfd = os.fdopen(self.readfd, 'rb')
            self.writefd = os.fdopen(self.writefd, 'wb')
        self.shell = shell
        self.callback = shell.output_callback[0]
        self.args = shell.output_callback[1:]
        self.process = None
        self.thread = threading.Thread(target=self.reader)
        self.output = b''
        self.thread.start()

    def set_process(self, process):
        self.process = process
        self.writefd.close()

    def reader(self):
        while True:
            data = self.readfd.read(100)
            if data == b'':
                data = None
            self.callback(self.shell, self.process, self.readfd, data, *self.args)
            if not data:
                break
            self.output += data
        self.readfd.close()

class CommandFailed(RuntimeError):
    def __init__(self, result):
        self.result = result
        return super(CommandFailed, self).__init__(result.stderr)

# You really only need one Shell or Pipe instance, so let's create one and recommend to
# use it.
shell = Shell()
pipe = Pipe()
