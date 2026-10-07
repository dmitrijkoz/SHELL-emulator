from __future__ import annotations
import argparse
import getpass
import shlex
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
@dataclass(frozen=True)
class ShellConfig:
    vfs_path: Path
    startup_script: Path | None
def get_prompt() -> str:
    username = getpass.getuser()
    hostname = socket.gethostname()
    return f"{username}@{hostname}:~$ "
def get_session_prompt(session: "ShellSession") -> str:
    username = getpass.getuser()
    hostname = socket.gethostname()
    relative = session.current_dir.relative_to(session.vfs_path)
    location = "~" if not relative.parts else "~/" + "/".join(relative.parts)
    return f"{username}@{hostname}:{location}$ "
def parse_input(line: str) -> tuple[str, list[str]]:
    try:
        parts = shlex.split(line)
    except ValueError as error:
        raise ValueError(f"Ошибка разбора: {error}") from error
    if not parts:
        return "", []
    return parts[0], parts[1:]
def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Эмулятор shell с настраиваемым VFS и стартовым скриптом."
    )
    parser.add_argument(
        "vfs_path",
        nargs="?",
        default="vfs",
        help="путь к физическому расположению VFS (по умолчанию: vfs)",
    )
    parser.add_argument(
        "startup_script",
        nargs="?",
        default=None,
        help="путь к стартовому скрипту (необязательно)",
    )
    return parser
def parse_cli_args(argv: list[str] | None = None) -> ShellConfig:
    args = create_cli_parser().parse_args(argv)
    vfs_path = Path(args.vfs_path).expanduser().resolve()
    startup_script = (
        Path(args.startup_script).expanduser().resolve()
        if args.startup_script
        else None
    )
    return ShellConfig(vfs_path=vfs_path, startup_script=startup_script)
def validate_config(config: ShellConfig) -> None:
    if not config.vfs_path.exists():
        raise FileNotFoundError(f"VFS не найден: {config.vfs_path}")
    if not config.vfs_path.is_dir():
        raise NotADirectoryError(
            "Путь к VFS не является каталогом: "
            f"{config.vfs_path}"
        )
    if config.startup_script is None:
        return
    if not config.startup_script.exists():
        raise FileNotFoundError(
            f"Стартовый скрипт не найден: {config.startup_script}"
        )
    if not config.startup_script.is_file():
        raise IsADirectoryError(
            "Путь к стартовому скрипту не является файлом: "
            f"{config.startup_script}"
        )
class ShellSession:
    def __init__(self, vfs_path: Path) -> None:
        self.vfs_path = vfs_path
        self.current_dir = vfs_path
    def _resolve_vfs_path(self, user_path: str) -> Path:
        if user_path.startswith("/"):
            candidate = self.vfs_path / user_path.lstrip("/")
        else:
            candidate = self.current_dir / user_path
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.vfs_path)
        except ValueError as error:
            raise ValueError("Путь выходит за пределы VFS") from error
        return resolved
    def execute(self, command: str, args: list[str]) -> tuple[bool, bool]:
        if command == "exit":
            return self._execute_exit(args)
        if command == "ls":
            return self._execute_ls(args), False
        if command == "cd":
            return self._execute_cd(args), False
        print(f"Ошибка: команда не найдена: {command}")
        return False, False
    @staticmethod
    def _execute_exit(args: list[str]) -> tuple[bool, bool]:
        if args:
            print("exit: команда не принимает аргументы")
            return False, False
        return True, True
    @staticmethod
    def _parse_ls_args(args: list[str]) -> tuple[bool, str | None]:
        if len(args) > 1:
            print("ls: используется не более одного пути")
            return False, None
        path_args = [arg for arg in args if arg != "-l"]
        unknown = next(
            (arg for arg in path_args if arg.startswith("-")),
            None,
        )
        if unknown is not None:
            print(f"ls: неизвестный параметр: {unknown}")
            return False, None
        if len(path_args) > 1:
            print("ls: используется не более одного пути")
            return False, None
        return True, path_args[0] if path_args else None
    def _get_ls_target(self, path_arg: str | None) -> Path | None:
        if path_arg is None:
            return self.current_dir
        try:
            return self._resolve_vfs_path(path_arg)
        except ValueError as error:
            print(f"ls: {error}")
            return None
    def _print_ls_target(self, target: Path) -> bool:
        if not target.exists():
            print(f"ls: такого файла или каталога нет: {target}")
            return False
        if target.is_file():
            print(target.name)
            return True
        entries = sorted(
            target.iterdir(),
            key=lambda path: (not path.is_dir(), path.name.lower()),
        )
        for entry in entries:
            suffix = "/" if entry.is_dir() else ""
            print(f"{entry.name}{suffix}")
        return True
    def _execute_ls(self, args: list[str]) -> bool:
        valid, path_arg = self._parse_ls_args(args)
        if not valid:
            return False
        target = self._get_ls_target(path_arg)
        if target is None:
            return False
        return self._print_ls_target(target)
    def _execute_cd(self, args: list[str]) -> bool:
        if len(args) > 1:
            print("cd: используется один путь")
            return False
        target_arg = args[0] if args else "/"
        try:
            target = self._resolve_vfs_path(target_arg)
        except ValueError as error:
            print(f"cd: {error}")
            return False
        if not target.exists():
            print(f"cd: каталог не найден: {target_arg}")
            return False
        if not target.is_dir():
            print(f"cd: это не каталог: {target_arg}")
            return False
        self.current_dir = target
        return True
def execute_command(command: str, args: list[str]) -> bool:
    if command == "exit":
        if args:
            print("exit: команда не принимает аргументы")
            return True
        return False
    if command in ("ls", "cd"):
        print(f"{command}: {args}")
        return True
    print(f"Ошибка: команда не найдена: {command}")
    return True
def _read_startup_script(script_path: Path) -> list[str] | None:
    try:
        return script_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        print(
            f"Ошибка чтения стартового скрипта: {error}",
            file=sys.stderr,
        )
        return None
def _run_startup_line(
    session: ShellSession,
    raw_line: str,
    line_number: int,
    prompt: str | None,
) -> tuple[bool, bool]:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return True, False
    current_prompt = (
        prompt if prompt is not None else get_session_prompt(session)
    )
    print(f"{current_prompt}{line}")
    try:
        command, args = parse_input(line)
    except ValueError as error:
        print(
            "Ошибка стартового скрипта "
            f"(строка {line_number}): {error}"
        )
        return False, False
    if not command:
        return True, False
    success, should_exit = session.execute(command, args)
    if not success:
        print(
            "Ошибка стартового скрипта: "
            "команда завершилась с ошибкой "
            f"(строка {line_number})"
        )
        return False, False
    return True, should_exit
def run_startup_script(
    session: ShellSession,
    script_path: Path,
    prompt: str | None = None,
) -> bool:
    lines = _read_startup_script(script_path)
    if lines is None:
        return False
    for line_number, raw_line in enumerate(lines, start=1):
        success, should_exit = _run_startup_line(
            session,
            raw_line,
            line_number,
            prompt,
        )
        if not success or should_exit:
            return success
    return True
def _read_repl_line(prompt: str) -> str | None:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return None
def _execute_repl_input(
    active_session: ShellSession | None,
    line: str,
) -> bool:
    try:
        command, args = parse_input(line)
    except ValueError as error:
        print(error)
        return True
    if not command:
        return True
    if active_session is None:
        return execute_command(command, args)
    success, should_exit = active_session.execute(command, args)
    if should_exit:
        return False
    return True if success else True
def run_repl(session: ShellSession | None = None) -> None:
    active_session = session
    prompt = get_prompt()
    print("Эмулятор shell. Введите 'exit' для выхода.")
    while True:
        current_prompt = (
            get_session_prompt(active_session)
            if active_session is not None
            else prompt
        )
        line = _read_repl_line(current_prompt)
        if line is None:
            break
        if not _execute_repl_input(active_session, line):
            break
def main(argv: list[str] | None = None) -> int:
    try:
        config = parse_cli_args(argv)
    except SystemExit as error:
        return int(error.code) if isinstance(error.code, int) else 2
    print("Отладочная информация конфигурации:")
    print(f"  Путь к VFS: {config.vfs_path}")
    if config.startup_script is not None:
        print(f"  Путь к стартовому скрипту: {config.startup_script}")
    else:
        print("  Стартовый скрипт: не задан")
    try:
        validate_config(config)
    except (
        FileNotFoundError,
        NotADirectoryError,
        IsADirectoryError,
    ) as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return 2
    session = ShellSession(config.vfs_path)
    if config.startup_script is not None:
        print("Стартовый скрипт:")
        if not run_startup_script(session, config.startup_script):
            return 1
        print("Стартовый скрипт выполнен успешно.")
    run_repl(session)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())