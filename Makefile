.PHONY: help install-tox install-deps tox

help:
	@echo "Makefile targets:"
	@echo "  make install-deps - Install Python dependencies from requirements.txt"
	@echo "  make install-tox  - Ensure tox is installed"
	@echo "  make tox          - Run all tox environments"

install-deps:
	pip install --upgrade pip
	pip install -r requirements.txt

install-tox:
	./scripts/install-tox.sh

tox: install-tox
	tox
