PYTHON_FILES = src/*.py
HTML_FILES = src/templates/*.html

.PHONY: format format-py format-html check check-py check-html install-dev clean

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Format all code (Python + HTML)
format: format-py format-html

# Format Python files with Black and isort
format-py:
	@echo "Formatting Python files with Black..."
	black $(PYTHON_FILES)
	@echo "Sorting Python imports with isort..."
	isort $(PYTHON_FILES)

# Format HTML files with Prettier (prefer npx, fallback to docker)
format-html:
	@echo "Formatting HTML files with Prettier..."
	@if command -v npx >/dev/null 2>&1; then \
		npx prettier --write $(HTML_FILES); \
	elif command -v docker >/dev/null 2>&1; then \
		docker run --rm -v $(PWD):/workspace -w /workspace node:alpine npx prettier --write $(HTML_FILES); \
	else \
		echo "Error: Neither npx nor docker available. Please install Node.js or Docker."; \
		exit 1; \
	fi

# Check all formatting without fixing (CI mode)
check: check-py check-html

# Check Python formatting
check-py:
	@echo "Checking Python formatting with Black..."
	black --check $(PYTHON_FILES)
	@echo "Checking Python import order with isort..."
	isort --check-only $(PYTHON_FILES)

# Check HTML formatting
check-html:
	@echo "Checking HTML formatting with Prettier..."
	@if command -v npx >/dev/null 2>&1; then \
		npx prettier --check $(HTML_FILES); \
	elif command -v docker >/dev/null 2>&1; then \
		docker run --rm -v $(PWD):/workspace -w /workspace node:alpine npx prettier --check $(HTML_FILES); \
	else \
		echo "Error: Neither npx nor docker available. Please install Node.js or Docker."; \
		exit 1; \
	fi

# Clean up any cache files
clean:
	rm -rf .mypy_cache
	rm -rf __pycache__
	rm -rf src/__pycache__
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
