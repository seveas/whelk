from whelk.tests import *

class IoTest(unittest.TestCase):
    def test_stderr(self):
        # Command with stderr
        r = shell.ls('/does/not/exist')
        self.assertTrue(r.returncode != 0)
        self.assertEqual(r.stdout, b(''))
        self.assertTrue(r.stderr != b(''))

    def test_withinput(self):
        # with inputstring
        inp = b('Hello, world!')
        r = shell.cat(input=inp)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(inp, r.stdout)
        self.assertEqual(b(''), r.stderr)

    def test_withio(self):
        # Use open filehandles
        fd = open('/etc/resolv.conf', 'rb')
        data = fd.read()
        fd.seek(0)
        r = shell.rot13(stdin=fd)
        fd.close()
        self.assertEqual(r.returncode, 0)
        if PY3:
            rot13 = bytes.maketrans(b('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                                    b('nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM'))
            self.assertEqual(data.translate(rot13), r.stdout)
        else:
            self.assertEqual(data.encode('rot13'), r.stdout)
        self.assertEqual(r.stderr, b(''))

    def test_withoutredirect(self):
        # Run something with redirect=False
        r = shell.echo("-n",".", redirect=False)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, None)
        self.assertEqual(r.stderr, None)

    def test_encoding(self):
        input = "Hello, world!"
        r = pipe(
            pipe.caesar(10, input=input, encoding='utf-8') |
            pipe.caesar(10) |
            pipe.caesar(6, encoding='utf-8')
        )
        self.assertEqual(r.returncode, [0,0,0])
        self.assertEqual(r.stdout, input)
        self.assertEqual(r.stderr, '')

        r = shell.rot13(input=input, encoding='utf-8')
        self.assertEqual(r.returncode, 0)
        if PY3:
            rot13 = str.maketrans('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
                                     'nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM')
            self.assertEqual(input.translate(rot13), r.stdout)
        else:
            self.assertEqual(input.encode('rot13'), r.stdout)
        self.assertEqual(r.stderr, '')

    def test_encoding2(self):
        input = '\u041f\u0440\u0438\u0432\u0435\u0442, \u043c\u0438\u0440!'
        s = Shell(encoding='utf-8')
        r = s.cat(input=input)
        self.assertEqual(input, r.stdout)

