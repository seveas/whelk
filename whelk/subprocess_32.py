# Code taken and modified from subprocess - Subprocesses with accessible I/O streams
#
# For more information about this module, see PEP 324.
#
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
#
# Licensed to PSF under a Contributor Agreement.
# See http://www.python.org/2.4/license for licensing details.

import errno
import subprocess
import select
import os
import sys

class Popen(subprocess.Popen):
    output_callback_supported = sys.platform != 'mswindows'
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
                self.output_callback[0](self.shell, self, fd, None, *self.output_callback[1:])

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
                e = sys.exc_info()[1]
                if e.args[0] == errno.EINTR:
                    continue
                raise

            for fd, mode in ready:
                if mode & select.POLLOUT:
                    chunk = input[input_offset : input_offset + subprocess._PIPE_BUF]
                    try:
                        input_offset += os.write(fd, chunk)
                    except OSError:
                        e = sys.last_exc()
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
                        self.output_callback[0](self.shell, self, fd, data, *self.output_callback[1:])
                    if not data:
                        close_unregister_and_remove(fd)
                    fd2output[fd].append(data)
                else:
                    # Ignore hang up or errors.
                    close_unregister_and_remove(fd)

        return (stdout, stderr)

    def _communicate_with_select(self, input):
        read_set = []
        write_set = []
        stdout = None # Return
        stderr = None # Return

        if self.stdin and input:
            write_set.append(self.stdin)
        if self.stdout:
            read_set.append(self.stdout)
            stdout = []
        if self.stderr:
            read_set.append(self.stderr)
            stderr = []

        input_offset = 0
        while read_set or write_set:
            try:
                rlist, wlist, xlist = select.select(read_set, write_set, [])
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise

            if self.stdin in wlist:
                chunk = input[input_offset : input_offset + subprocess._PIPE_BUF]
                try:
                    bytes_written = os.write(self.stdin.fileno(), chunk)
                except OSError as e:
                    if e.errno == errno.EPIPE:
                        self.stdin.close()
                        write_set.remove(self.stdin)
                    else:
                        raise
                else:
                    input_offset += bytes_written
                    if input_offset >= len(input):
                        self.stdin.close()
                        write_set.remove(self.stdin)

            if self.stdout in rlist:
                data = os.read(self.stdout.fileno(), 1024)
                if data == "":
                    self.stdout.close()
                    read_set.remove(self.stdout)
                    if self.output_callback:
                        self.output_callback[0](self.shell, self, self.stdout, None, *self.output_callback[1:])
                stdout.append(data)
                if data and self.output_callback:
                    self.output_callback[0](self.shell, self, self.stdout, data, *self.output_callback[1:])

            if self.stderr in rlist:
                data = os.read(self.stderr.fileno(), 1024)
                if data == "":
                    self.stderr.close()
                    read_set.remove(self.stderr)
                    if self.output_callback:
                        self.output_callback[0](self.shell, self, self.stderr, None, *self.output_callback[1:])
                stderr.append(data)
                if data and self.output_callback:
                    self.output_callback[0](self.shell, self, self.stderr, data, *self.output_callback[1:])

        return (stdout, stderr)
