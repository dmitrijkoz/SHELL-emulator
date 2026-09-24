import unittest
from src.shell_emulator import parse_input, execute_command


class TestShellEmulator(unittest.TestCase):
    def test_parse_simple(self):
        self.assertEqual(parse_input("ls -la"), ("ls", ["-la"]))

    def test_parse_quotes(self):
        self.assertEqual(
            parse_input('cd "my folder"'), ("cd", ["my folder"])
        )

    def test_parse_unclosed_quote(self):
        with self.assertRaises(ValueError):
            parse_input('cd "unclosed')

    def test_execute_stub(self):
        self.assertTrue(execute_command("ls", ["-l"]))

    def test_execute_exit(self):
        self.assertFalse(execute_command("exit", []))

    def test_execute_unknown(self):
        self.assertTrue(execute_command("pwd", []))


if __name__ == "__main__":
    unittest.main()