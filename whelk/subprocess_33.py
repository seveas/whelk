# Code taken and modified from subprocess - Subprocesses with accessible I/O streams
#
# For more information about this module, see PEP 324.
#
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
#
# Licensed to PSF under a Contributor Agreement.
# See http://www.python.org/2.4/license for licensing details.

import subprocess
import select
import os
import sys

class Popen(subprocess.Popen):
    output_callback_supported = sys.platform != 'mswindows' and hasattr(select, 'poll')
    def _communicate_with_poll(self, input, endtime, orig_timeout):
        stdout = None # Return
        stderr = None # Return

        if not self._communication_started:
            self._fd2file = {}

        poller = select.poll()
        def register_and_append(file_obj, eventmask):
            poller.register(file_obj.fileno(), eventmask)
            self._fd2file[file_obj.fileno()] = file_obj

        def close_unregister_and_remove(fd):
            poller.unregister(fd)
            self._fd2file[fd].close()
            self._fd2file.pop(fd)
            if self.output_callback:
                self.output_callback[0](self.shell, self, fd, None, *self.output_callback[1:])

        if self.stdin and input:
            register_and_append(self.stdin, select.POLLOUT)

        # Only create this mapping if we haven't already.
        if not self._communication_started:
            self._fd2output = {}
            if self.stdout:
                self._fd2output[self.stdout.fileno()] = []
            if self.stderr:
                self._fd2output[self.stderr.fileno()] = []

        select_POLLIN_POLLPRI = select.POLLIN | select.POLLPRI
        if self.stdout:
            register_and_append(self.stdout, select_POLLIN_POLLPRI)
            stdout = self._fd2output[self.stdout.fileno()]
        if self.stderr:
            register_and_append(self.stderr, select_POLLIN_POLLPRI)
            stderr = self._fd2output[self.stderr.fileno()]

        self._save_input(input)

        while self._fd2file:
            timeout = self._remaining_time(endtime)
            if timeout is not None and timeout < 0:
                raise subprocess.TimeoutExpired(self.args, orig_timeout)
            try:
                ready = poller.poll(timeout)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise
            self._check_timeout(endtime, orig_timeout)

            # XXX Rewrite these to use non-blocking I/O on the
            # file objects; they are no longer using C stdio!

            for fd, mode in ready:
                if mode & select.POLLOUT:
                    chunk = self._input[self._input_offset :
                                        self._input_offset + subprocess._PIPE_BUF]
                    try:
                        self._input_offset += os.write(fd, chunk)
                    except OSError as e:
                        if e.errno == errno.EPIPE:
                            close_unregister_and_remove(fd)
                        else:
                            raise
                    else:
                        if self._input_offset >= len(self._input):
                            close_unregister_and_remove(fd)
                elif mode & select_POLLIN_POLLPRI:
                    data = os.read(fd, 4096)
                    if self.output_callback:
                        self.output_callback[0](self.shell, self, fd, data, *self.output_callback[1:])
                    if not data:
                        close_unregister_and_remove(fd)
                    self._fd2output[fd].append(data)
                else:
                    # Ignore hang up or errors.
                    close_unregister_and_remove(fd)

        return (stdout, stderr)

    def _communicate_with_select(self, input, endtime, orig_timeout):
        if not self._communication_started:
            self._read_set = []
            self._write_set = []
            if self.stdin and input:
                self._write_set.append(self.stdin)
            if self.stdout:
                self._read_set.append(self.stdout)
            if self.stderr:
                self._read_set.append(self.stderr)

        self._save_input(input)

        stdout = None # Return
        stderr = None # Return

        if self.stdout:
            if not self._communication_started:
                self._stdout_buff = []
            stdout = self._stdout_buff
        if self.stderr:
            if not self._communication_started:
                self._stderr_buff = []
            stderr = self._stderr_buff

        while self._read_set or self._write_set:
            timeout = self._remaining_time(endtime)
            if timeout is not None and timeout < 0:
                raise subprocess.TimeoutExpired(self.args, orig_timeout)
            try:
                (rlist, wlist, xlist) = \
                    select.select(self._read_set, self._write_set, [],
                                  timeout)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise

            # According to the docs, returning three empty lists indicates
            # that the timeout expired.
            if not (rlist or wlist or xlist):
                raise subprocess.TimeoutExpired(self.args, orig_timeout)
            # We also check what time it is ourselves for good measure.
            self._check_timeout(endtime, orig_timeout)

            # XXX Rewrite these to use non-blocking I/O on the
            # file objects; they are no longer using C stdio!

            if self.stdin in wlist:
                chunk = self._input[self._input_offset :
                                    self._input_offset + subprocess._PIPE_BUF]
                try:
                    bytes_written = os.write(self.stdin.fileno(), chunk)
                except OSError as e:
                    if e.errno == errno.EPIPE:
                        self.stdin.close()
                        self._write_set.remove(self.stdin)
                    else:
                        raise
                else:
                    self._input_offset += bytes_written
                    if self._input_offset >= len(self._input):
                        self.stdin.close()
                        self._write_set.remove(self.stdin)

            if self.stdout in rlist:
                data = os.read(self.stdout.fileno(), 1024)
                if not data:
                    self.stdout.close()
                    self._read_set.remove(self.stdout)
                    if self.output_callback:
                        self.output_callback[0](self.shell, self, self.stdout, None, *self.output_callback[1:])
                stdout.append(data)
                if data and self.output_callback:
                    self.output_callback[0](self.shell, self, self.stdout, data, *self.output_callback[1:])

            if self.stderr in rlist:
                data = os.read(self.stderr.fileno(), 1024)
                if not data:
                    self.stderr.close()
                    self._read_set.remove(self.stderr)
                    if self.output_callback:
                        self.output_callback[0](self.shell, self, self.stderr, None, *self.output_callback[1:])
                stderr.append(data)
                if data and self.output_callback:
                    self.output_callback[0](self.shell, self, self.stderr, data, *self.output_callback[1:])

        return (stdout, stderr)
