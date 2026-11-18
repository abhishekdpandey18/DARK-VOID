# DARK VOID — Simplified Makefile for One-Command Setup & Testing
.PHONY: install uninstall doctor test clean

install:
	@./scripts/install.sh

install-deps:
	@./scripts/install.sh --auto-deps

uninstall:
	@./scripts/uninstall.sh

doctor:
	@~/.local/bin/darkvoid doctor

test:
	@python3 -m unittest discover -s tests -v

clean:
	@find . -name "__pycache__" -o -name "*.pyc" -o -name "*.pyo" -o -name "*.egg-info" | xargs rm -rf
