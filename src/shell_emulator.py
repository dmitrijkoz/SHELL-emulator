"""Эмулятор shell для варианта №10, этап 2 (конфигурация)."""

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
    """Конфигурация запуска эмулятора."""

    vfs_path: Path
    startup_script: Path


def get_prompt() -> str:
    """Сформировать приглашение на основе реальных данных ОС."""
    username = getpass.getuser()
    hostname = socket.gethostname()
    return f"{username}@{hostname}:~$ "


def get_session_prompt(session: "ShellSession") -> str:
    """Сформировать приглашение с учётом текущего каталога VFS."""
    username = getpass.getuser()
    hostname = socket.gethostname()
    relative = session.current_dir.relative_to(session.vfs_path)
    location = "~" if not relative.parts else "~/" + "/".join(relative.parts)
    return f"{username}@{hostname}:{location}$ "


def parse_input(line: str) -> tuple[str, list[str]]:
    """Разобрать строку на команду и аргументы, корректно обрабатывая кавычки."""
    try:
        parts = shlex.split(line)
    except ValueError as error:
        raise ValueError(f"Ошибка разбора: {error}") from error

    if not parts:
        return "", []
    return parts[0], parts[1:]


def create_cli_parser() -> argparse.ArgumentParser:
    """Создать парсер параметров командной строки."""
    parser = argparse.ArgumentParser(
        description="Эмулятор shell с настраиваемым VFS и стартовым скриптом."
    )
    parser.add_argument(
        "vfs_path",
        help="путь к физическому расположению VFS",
    )
    parser.add_argument(
        "startup_script",
        help="путь к стартовому скрипту",
    )
    return parser


def parse_cli_args(argv: list[str] | None = None) -> ShellConfig:
    """Разобрать параметры командной строки и нормализовать пути."""
    args = create_cli_parser().parse_args(argv)
    vfs_path = Path(args.vfs_path).expanduser().resolve()
    startup_script = Path(args.startup_script).expanduser().resolve()
    return ShellConfig(vfs_path=vfs_path, startup_script=startup_script)


def validate_config(config: ShellConfig) -> None:
    """Проверить, что VFS и стартовый скрипт существуют и имеют нужный тип."""
    if not config.vfs_path.exists():
        raise FileNotFoundError(f"VFS не найден: {config.vfs_path}")
    if not config.vfs_path.is_dir():
        raise NotADirectoryError(
            f"Путь к VFS не является каталогом: {config.vfs_path}"
        )

    if not config.startup_script.exists():
        raise FileNotFoundError(
            f"Стартовый скрипт не найден: {config.startup_script}"
        )
    if not config.startup_script.is_file():
        raise IsADirectoryError(
            f"Путь к стартовому скрипту не является файлом: {config.startup_script}"
        )


class ShellSession:
    """Сеанс эмулятора с привязанным физическим VFS."""

    def __init__(self, vfs_path: Path) -> None:
        self.vfs_path = vfs_path
        self.current_dir = vfs_path

    def _resolve_vfs_path(self, user_path: str) -> Path:
        """Преобразовать виртуальный путь в физический путь внутри VFS."""
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
        """
        Выполнить команду.

        Возвращает пару (успех, нужно_выйти).
        """
        if command == "exit":
            if args:
                print("exit: команда не принимает аргументы")
                return False, False
            return True, True

        if command == "ls":
            return self._execute_ls(args), False

        if command == "cd":
            return self._execute_cd(args), False

        print(f"Ошибка: команда не найдена: {command}")
        return False, False

    def _execute_ls(self, args: list[str]) -> bool:
        """Выполнить ls внутри VFS."""
        if len(args) > 1:
            print("ls: используется не более одного пути")
            return False

        # Параметр -l из этапа 1 принимается, хотя формат подробного вывода
        # отдельно не требуется заданием второго этапа.
        path_args = [arg for arg in args if arg != "-l"]
        if any(arg.startswith("-") for arg in path_args):
            unknown = next(arg for arg in path_args if arg.startswith("-"))
            print(f"ls: неизвестный параметр: {unknown}")
            return False
        if len(path_args) > 1:
            print("ls: используется не более одного пути")
            return False

        if path_args:
            try:
                target = self._resolve_vfs_path(path_args[0])
            except ValueError as error:
                print(f"ls: {error}")
                return False
        else:
            target = self.current_dir

        if not target.exists():
            print(f"ls: такого файла или каталога нет: {target}")
            return False

        if target.is_file():
            print(target.name)
            return True

        entries = sorted(target.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower()))
        for entry in entries:
            suffix = "/" if entry.is_dir() else ""
            print(f"{entry.name}{suffix}")
        return True

    def _execute_cd(self, args: list[str]) -> bool:
        """Изменить текущий каталог внутри VFS."""
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
    """Выполнить команду в режиме, совместимом с API этапа 1.

    Возвращает False только для команды ``exit``; ошибки остальных команд
    не завершают интерактивный REPL.
    """
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


def run_startup_script(session: ShellSession, script_path: Path, prompt: str | None = None) -> bool:
    """Выполнить стартовый скрипт до первой ошибки.

    На экран выводятся как выполняемые команды, так и их результат. Возвращается
    True при успешном завершении скрипта и False при первой ошибке.
    """
    display_prompt = prompt

    try:
        lines = script_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        print(f"Ошибка чтения стартового скрипта: {error}", file=sys.stderr)
        return False

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Имитируем реальный диалог: сначала показываем ввод пользователя.
        current_prompt = display_prompt if display_prompt is not None else get_session_prompt(session)
        print(f"{current_prompt}{line}")

        try:
            command, args = parse_input(line)
        except ValueError as error:
            print(f"Ошибка стартового скрипта (строка {line_number}): {error}")
            return False

        if not command:
            continue

        success, should_exit = session.execute(command, args)
        if not success:
            print(
                "Ошибка стартового скрипта: "
                f"команда завершилась с ошибкой (строка {line_number})"
            )
            return False

        if should_exit:
            return True

    return True


def run_repl(session: ShellSession | None = None) -> None:
    """Запустить интерактивный цикл REPL."""
    active_session = session
    prompt = get_prompt()
    print("Эмулятор shell. Введите 'exit' для выхода.")

    while True:
        current_prompt = get_session_prompt(active_session) if active_session is not None else prompt
        try:
            line = input(current_prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        try:
            command, args = parse_input(line)
        except ValueError as error:
            print(error)
            continue

        if not command:
            continue

        if active_session is None:
            should_continue = execute_command(command, args)
            if not should_continue:
                break
            continue

        success, should_exit = active_session.execute(command, args)
        if should_exit:
            break
        if not success:
            # Интерактивный режим после ошибки продолжает работу.
            continue


def main(argv: list[str] | None = None) -> int:
    """Точка входа приложения."""
    try:
        config = parse_cli_args(argv)
    except SystemExit as error:
        # argparse сам печатает справку/ошибку; возвращаем код завершения.
        return int(error.code) if isinstance(error.code, int) else 2

    print("Отладочная информация конфигурации:")
    print(f"  Путь к VFS: {config.vfs_path}")
    print(f"  Путь к стартовому скрипту: {config.startup_script}")

    try:
        validate_config(config)
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError) as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return 2

    session = ShellSession(config.vfs_path)
    print("Стартовый скрипт:")
    if not run_startup_script(session, config.startup_script):
        return 1

    print("Стартовый скрипт выполнен успешно.")
    run_repl(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
