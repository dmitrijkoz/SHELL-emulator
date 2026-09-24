# Конфигурационное управление. Вариант №10, этап 1

## 1. Общее описание
Эмулятор shell для UNIX-подобной ОС. Этап 1 — минимальный REPL:
парсер с поддержкой кавычек, команды-заглушки `ls`, `cd`, команда `exit`.

## 2. Функции и настройки
- `get_prompt()` — формирует приглашение `username@hostname:~$`.
- `parse_input(line)` — разбирает строку на команду и аргументы через `shlex`.
- `execute_command(command, args)` — выполняет команду.
- `run_repl()` — запускает интерактивный цикл.

## 3. Сборка и запуск тестов

### Windows (PowerShell / CMD)
Запуск эмулятора и тестов:
```powershell
python -m src.shell_emulator
python -m unittest discover -s tests -v