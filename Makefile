.PHONY: help install install-dev test lint format clean run setup docs

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements/base.txt

install-dev:  ## Install development dependencies
	pip install -r requirements/dev.txt

test:  ## Run tests
	python tests/test_scraper.py

verify:  ## Run verification tests
	python tests/verify_scraper.py

lint:  ## Run code linting
	flake8 src/
	mypy src/

format:  ## Format code
	black src/ tests/ scripts/
	isort src/ tests/ scripts/

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:  ## Run the scraper
	python main.py

run-test:  ## Run scraper with limited pages (test mode)
	python main.py --max-pages 2

setup:  ## Initial project setup
	pip install -r requirements/dev.txt
	python -c "from pathlib import Path; [Path(d).mkdir(exist_ok=True) for d in ['data/raw', 'data/processed', 'logs']]"

docs:  ## Generate documentation
	@echo "Documentation generation not implemented yet"

build:  ## Build package
	python setup.py sdist bdist_wheel

install-package:  ## Install package in development mode
	pip install -e .

.DEFAULT_GOAL := help
