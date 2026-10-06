import io
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from src.shell_emulator import (
    ShellConfig,
    ShellSession,
    execute_command,
    parse_cli_args,
    parse_input,
    run_startup_script,
    validate_config,
)


class TestShellEmulator(unittest.TestCase):
    def test_parse_simple(self):
        self.assertEqual(parse_input("ls -la"), ("ls", ["-la"]))

    def test_parse_quotes(self):
        self.assertEqual(
            parse_input('cd "my folder"'),
            ("cd", ["my folder"]),
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

    def test_parse_cli_args(self):
        config = parse_cli_args([
            "./vfs",
            "./scripts/startup_success.txt",
        ])
        self.assertEqual(config.vfs_path, (Path.cwd() / "vfs").resolve())
        self.assertEqual(
            config.startup_script,
            (Path.cwd() / "scripts" / "startup_success.txt").resolve(),
        )

    def test_parse_cli_args_without_startup(self):
        config = parse_cli_args([])
        self.assertEqual(config.vfs_path, (Path.cwd() / "vfs").resolve())
        self.assertIsNone(config.startup_script)

    def test_validate_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vfs = root / "vfs"
            script = root / "startup.txt"
            vfs.mkdir()
            script.write_text("exit\n", encoding="utf-8")
            config = ShellConfig(vfs, script)
            validate_config(config)

    def test_startup_script_stops_on_first_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vfs = root / "vfs"
            vfs.mkdir()
            (vfs / "home").mkdir()
            script = root / "startup.txt"
            script.write_text(
                "ls\ncd missing\nls\nexit\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = run_startup_script(
                    ShellSession(vfs),
                    script,
                    "test$ ",
                )
            self.assertFalse(result)
            lines = output.getvalue().splitlines()
            self.assertIn("test$ ls", lines)
            self.assertIn("test$ cd missing", lines)
            self.assertNotIn("test$ exit", lines)

    def test_startup_script_dialog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vfs = root / "vfs"
            vfs.mkdir()
            script = root / "startup.txt"
            script.write_text("ls\nexit\n", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                result = run_startup_script(
                    ShellSession(vfs),
                    script,
                    "prompt$ ",
                )
            self.assertTrue(result)
            self.assertIn("prompt$ ls", output.getvalue())
            self.assertIn("prompt$ exit", output.getvalue())

    def test_shell_session_cd_and_ls(self):
        with tempfile.TemporaryDirectory() as tmp:
            vfs = Path(tmp)
            (vfs / "home").mkdir()
            (vfs / "home" / "file.txt").write_text(
                "ok",
                encoding="utf-8",
            )
            session = ShellSession(vfs)
            success, should_exit = session.execute("cd", ["home"])
            self.assertTrue(success)
            self.assertFalse(should_exit)
            self.assertEqual(
                session.current_dir,
                (vfs / "home").resolve(),
            )
            output = io.StringIO()
            with redirect_stdout(output):
                success, should_exit = session.execute("ls", [])
            self.assertTrue(success)
            self.assertFalse(should_exit)
            self.assertIn("file.txt", output.getvalue())

    def test_invalid_vfs_fails_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "startup.txt"
            script.write_text("exit\n", encoding="utf-8")
            config = ShellConfig(root / "missing-vfs", script)
            with self.assertRaises(FileNotFoundError):
                validate_config(config)

    def test_script_read_error_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vfs = root / "vfs"
            vfs.mkdir()
            script = root / "missing.txt"
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                result = run_startup_script(
                    ShellSession(vfs),
                    script,
                    "prompt$ ",
                )
            self.assertFalse(result)
            self.assertIn(
                "Ошибка чтения стартового скрипта",
                output.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
