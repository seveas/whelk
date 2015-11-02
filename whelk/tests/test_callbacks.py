from whelk.tests import *

class CallbackTest(unittest.TestCase):
    def test_callback(self):
        chunks = []
        seen_eof = {}
        def cb(shell, sp, fd, data, arg):
            self.assertEqual(arg, 'hello')
            if data is None:
                seen_eof[fd] = True
                return
            chunks.append(data)
        r = shell.test_data(16, output_callback=[cb, 'hello'])
        self.assertEqual(r.returncode, 0)
        self.assertTrue(len(chunks) > 1)
        self.assertEqual(r.stdout, b('').join(chunks))
        self.assertEqual(list(seen_eof.values()), [True, True])

        cb_called = []
        def cb1(command, sp, res):
            self.assertEqual(sp.returncode, 0)
            cb_called.append(1)
        def cb2(command):
            cb_called.append(2)

        s = Shell(exit_callback=cb1, run_callback=cb2)
        p = Pipe(exit_callback=cb1, run_callback=cb2)
        s.true()
        p(p.true(run_callback=None)|p.true(exit_callback=None))
        self.assertEqual(cb_called, [2,1,2])

    def test_exit_callback(self):
        cb_called = []
        def cb(shell, sp, res):
            self.assertEqual(res.returncode, 0)
            cb_called.append(True)
        shell.true(exit_callback=cb)
        self.assertEqual(cb_called, [True])

    def test_run_callback(self):
        cb_called = []
        def cb(shell, *args):
            cb_called.append(args[-1])
        shell.true(run_callback=[cb, 'run'], exit_callback=[cb, 'exit'])
        self.assertEqual(cb_called, ['run', 'exit'])

    def test_raises(self):
        s = Shell(raise_on_error=True)
        self.assertRaises(CommandFailed, s.false)

        try:
            s.test_return(2)
        except:
            t,v,tb = sys.exc_info()
            self.assertEqual(CommandFailed, t)
            self.assertEqual(v.result.returncode, 2)
        else:
            self.fail("No exception was raised")

        try:
            pipe(pipe.true()|pipe.true()|pipe.test_return(1, raise_on_error=True))
        except:
            t,v,tb = sys.exc_info()
            self.assertEqual(CommandFailed, t)
            self.assertEqual(v.result.returncode.count(0), 2)
            self.assertEqual(v.result.returncode.count(1), 1)
        else:
            self.fail("No exception was raised")
