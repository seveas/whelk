# Code taken and modified from subprocess - Subprocesses with accessible I/O streams
#
# For more information about this module, see PEP 324.
#
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
#
# Licensed to PSF under a Contributor Agreement.
# See http://www.python.org/2.4/license for licensing details.

import os
import selectors
import subprocess
import sys
import errno


class Popen(subprocess.Popen):
    output_callback_supported = True
    def communicate(self, input=None, timeout=None):
        if self._communication_started and input:
            raise ValueError("Cannot send input after starting communication")

        # Python has an optimization here that disables all threads/select in
        # certain cases, which breaks the output callback
        if timeout is not None:
            endtime = _time() + timeout
        else:
            endtime = None

        try:
            stdout, stderr = self._communicate(input, endtime, timeout)
        finally:
            self._communication_started = True

        sts = self.wait(timeout=self._remaining_time(endtime))
        return (stdout, stderr)

    if sys.platform == 'win32':
        def _readerthread(self, fh, buffer):
            bufferx = []
            while True:
                data = fh.read(100)
                if not data:
                    break
                if self.output_callback:
                    self.output_callback[0](self.shell, self, fh, data, *self.output_callback[1:])
                bufferx.append(data)
            fh.close()
            buffer.append(b''.join(bufferx))

    else:
        def _communicate(self, input, endtime, orig_timeout):
            if self.stdin and not self._communication_started:
                # Flush stdio buffer.  This might block, if the user has
                # been writing to .stdin in an uncontrolled fashion.
                self.stdin.flush()
                if not input:
                    self.stdin.close()

            stdout = None
            stderr = None

            # Only create this mapping if we haven't already.
            if not self._communication_started:
                self._fileobj2output = {}
                if self.stdout:
                    self._fileobj2output[self.stdout] = []
                if self.stderr:
                    self._fileobj2output[self.stderr] = []

            if self.stdout:
                stdout = self._fileobj2output[self.stdout]
            if self.stderr:
                stderr = self._fileobj2output[self.stderr]

            self._save_input(input)

            if self._input:
                input_view = memoryview(self._input)

            with subprocess._PopenSelector() as selector:
                if self.stdin and input:
                    selector.register(self.stdin, selectors.EVENT_WRITE)
                if self.stdout:
                    selector.register(self.stdout, selectors.EVENT_READ)
                if self.stderr:
                    selector.register(self.stderr, selectors.EVENT_READ)

                while selector.get_map():
                    timeout = self._remaining_time(endtime)
                    if timeout is not None and timeout < 0:
                        raise TimeoutExpired(self.args, orig_timeout)

                    ready = selector.select(timeout)
                    self._check_timeout(endtime, orig_timeout)

                    # XXX Rewrite these to use non-blocking I/O on the file
                    # objects; they are no longer using C stdio!

                    for key, events in ready:
                        if key.fileobj is self.stdin:
                            chunk = input_view[self._input_offset :
                                               self._input_offset + subprocess._PIPE_BUF]
                            try:
                                self._input_offset += os.write(key.fd, chunk)
                            except OSError as e:
                                if e.errno == errno.EPIPE:
                                    selector.unregister(key.fileobj)
                                    key.fileobj.close()
                                else:
                                    raise
                            else:
                                if self._input_offset >= len(self._input):
                                    selector.unregister(key.fileobj)
                                    key.fileobj.close()
                        elif key.fileobj in (self.stdout, self.stderr):
                            data = os.read(key.fd, 32768)
                            if self.output_callback:
                                self.output_callback[0](self.shell, self, key.fd, data, *self.output_callback[1:])
                            if not data:
                                selector.unregister(key.fileobj)
                                key.fileobj.close()
                                if self.output_callback:
                                    self.output_callback[0](self.shell, self, key.fd, None, *self.output_callback[1:])
                            self._fileobj2output[key.fileobj].append(data)

            self.wait(timeout=self._remaining_time(endtime))

            # All data exchanged.  Translate lists into strings.
            if stdout is not None:
                stdout = b''.join(stdout)
            if stderr is not None:
                stderr = b''.join(stderr)

            # Translate newlines, if requested.
            # This also turns bytes into strings.
            if self.universal_newlines:
                if stdout is not None:
                    stdout = self._translate_newlines(stdout,
                                                      self.stdout.encoding)
                if stderr is not None:
                    stderr = self._translate_newlines(stderr,
                                                      self.stderr.encoding)

            return (stdout, stderr)
