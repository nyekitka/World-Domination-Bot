lint:
	poetry run ruff check .

format:
	poetry run ruff format .

.PHONY: test
test:
	poetry run pytest -v -k "$(k)"

.PHONY: test-cov
test-cov:
	poetry run pytest -v --cov-report=html