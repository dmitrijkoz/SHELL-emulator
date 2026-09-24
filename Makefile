.PHONY: run test

run:
	python3 -m src.shell_emulator

test:
	python3 -m unittest discover -s tests -v