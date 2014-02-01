from whelk.tests import *

class PipeTest(unittest.TestCase):
    """Tests pipe functionality"""
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

