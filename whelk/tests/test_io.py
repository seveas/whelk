from whelk.tests import *

class IoTest(unittest.TestCase):
    def test_stderr(self):
        # Command with stderr
        r = shell.test_return(1, '', 'error')
        self.assertTrue(r.returncode != 0)
        self.assertEqual(r.stdout, b(''))
        self.assertEqual(r.stderr, b('error\n'))

    def test_withinput(self):
        # with inputstring
        inp = b('Hello, world!')
        r = shell.cat(input=inp)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(inp, r.stdout)
        self.assertEqual(b(''), r.stderr)

    def test_withio(self):
        # Use open filehandles
        fd = open(__file__.replace('.pyc', '.py'), 'rb')
        data = fd.read()
        fd.seek(0)
        r = shell.tr('a-zA-Z', 'n-za-mN-ZA-M', stdin=fd)
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
        r = shell.test_return(0, "something", "something", redirect=False)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, None)
        self.assertEqual(r.stderr, None)

    def test_encoding(self):
        input = "Hello, world!"
        r = pipe(
            pipe.tr('a-zA-Z', 'k-za-jK-ZA-J', input=input, encoding='utf-8') |
            pipe.tr('a-zA-Z', 'k-za-jK-ZA-J') |
            pipe.tr('a-zA-Z', 'g-za-fG-ZA-F', encoding='utf-8')
        )
        self.assertEqual(r.returncode, [0,0,0])
        self.assertEqual(r.stdout, input)
        self.assertEqual(r.stderr, '')

        r = shell.tr('a-zA-Z', 'n-za-mN-ZA-M', input=input, encoding='utf-8')
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

