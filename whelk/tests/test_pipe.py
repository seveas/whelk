from whelk.tests import *

class PipeTest(unittest.TestCase):
    """Tests pipe functionality"""
    def test_pipes(self):
        # Test basic pipe usage
        r = pipe(pipe.test_return(0)|pipe.test_return(0, "output")|pipe.grep("o"))
        self.assertEqual(r.returncode, [0,0,0])
        self.assertEqual(r.stdout, b('output\n'))
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
        r = pipe(pipe.test_return(0, 'output'))
        self.assertEqual(r.returncode, [0])
        self.assertEqual(r.stderr, b(''))
        self.assertEqual(r.stdout, b('output\n'))

    def test_pipe_stderr(self):
        # Stderr redirection in the middle of the pipe
        r = pipe(pipe.test_return(0) | pipe.test_return(1, "", "error", stderr=STDOUT) | pipe.cat())
        self.assertEqual(r.returncode, [0,1,0])
        self.assertEqual(r.stdout, b('error\n'))
        self.assertEqual(r.stderr, b(''))

    def test_pipewithinput(self):
        input = b("Hello, world!")
        r = pipe(
            pipe.tr('a-zA-Z', 'k-za-jK-ZA-J', input=input) |
            pipe.tr('a-zA-Z', 'k-za-jK-ZA-J') |
            pipe.tr('a-zA-Z', 'g-za-fG-ZA-F')
        )
        self.assertEqual(r.returncode, [0,0,0])
        self.assertEqual(r.stdout, input)
        self.assertEqual(r.stderr, b(''))

    def test_pipewithhugeinput(self):
        input = b("123456789ABCDEF") * 65536 * 16 # 16 MB
        r = pipe(
            pipe.tr('a-zA-Z', 'k-za-jK-ZA-J', input=input) |
            pipe.tr('a-zA-Z', 'k-za-jK-ZA-J') |
            pipe.tr('a-zA-Z', 'g-za-fG-ZA-F')
        )
        self.assertEqual(r.returncode, [0,0,0])
        self.assertEqual(r.stdout, input)
        self.assertEqual(r.stderr, b(''))
