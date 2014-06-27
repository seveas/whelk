from whelk.tests import *

class BasicTest(unittest.TestCase):
    """Tests whether we can find commands"""
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
        if sys.version_info[:2] >= (3,4):
            self.assertEqual(r.stderr, b(''))
            self.assertTrue(b(v) in r.stdout)
        else:
            self.assertEqual(r.stdout, b(''))
            self.assertTrue(b(v) in r.stderr)

        r = shell[os.path.basename(sys.executable)]('-V')
        self.assertEqual(r.returncode, 0)
        if sys.version_info[:2] >= (3,4):
            self.assertEqual(r.stderr, b(''))
            self.assertTrue(b(v) in r.stdout)
        else:
            self.assertEqual(r.stdout, b(''))
            self.assertTrue(b(v) in r.stderr)

        self.assertTrue(shell.true())
        self.assertFalse(shell.false())

    def test_underscores(self):
        # Underscore-replacement
        c = shell.ssh_add
        self.assertTrue('ssh-add' in c.name)
        r = c('-l')
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, b(''))
        self.assertTrue(r.stdout != b(''))

    def test_exceptions(self):
        self.assertRaises(CommandFailed, lambda: shell.false(raise_on_error=True))

    def test_defaults(self):
        s = Shell(stdout = shell.STDOUT)
        input = b("Testing 1 2 3")
        r = s.cat(input=input)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, input)
