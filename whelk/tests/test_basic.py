from whelk.tests import *

class BasicTest(unittest.TestCase):
    """Tests whether we can find commands"""
    def test_notfound(self):
        # Non-existing command
        self.assertRaises(AttributeError, lambda: shell.i_do_not_exist)
        self.assertRaises(KeyError, lambda: shell['/not/found'])

    def test_basic(self):
        # Basic command test
        r = shell.test_return('0', 'output')
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, b('output\n'))
        self.assertEqual(r.stderr, b(''))

        r = shell.test_return('22', 'stdout', 'stderr')
        self.assertEqual(r.returncode, 22)
        self.assertEqual(r.stdout, b('stdout\n'))
        self.assertEqual(r.stderr, b('stderr\n'))


    def test_underscores(self):
        # Underscore-replacement
        c = shell.test_dashes
        self.assertTrue('test-dashes' in c.name)
        r = c(0)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, b(''))
        self.assertEqual(r.stdout, b(''))

    def test_exceptions(self):
        self.assertRaises(CommandFailed, lambda: shell.false(raise_on_error=True))

    def test_defaults(self):
        s = Shell(stdout = shell.STDOUT)
        input = b("Testing 1 2 3")
        r = s.cat(input=input)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, input)
