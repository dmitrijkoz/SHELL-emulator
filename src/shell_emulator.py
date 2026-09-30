import getpass
import shlex
import socket
import sys
def get_prompt() -> str:
    username = getpass.getuser()
    hostname = socket.gethostname()
    return f"{username}@{hostname}:~$ "
def parse_input(line: str) -> tuple[str, list[str]]:
    try:
        parts = shlex.split(line)
    except ValueError as error:
        raise ValueError(f"Ошибка разбора: {error}") from error
    if not parts:
        return "", []
    return parts[0], parts[1:]
def execute_command(command: str, args: list[str]) -> bool:
    if command == "exit":
        return False
    if command in ("ls", "cd"):
        print(f"{command}: {args}")
        return True
    print(f"Ошибка: команда не найдена: {command}")
    return True
def run_repl() -> None:
    prompt = get_prompt()
    print("Эмулятор shell. Введите 'exit' для выхода.")
    while True:
        try:
            line = input(prompt)
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
        if not execute_command(command, args):
            break
if __name__ == "__main__":
    run_repl()