.PHONY: help setup run tunnel lint lint-fix format format-check certs clean

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  setup        Create venv and install dependencies"
	@echo "  certs        Generate SSL certificates (requires mkcert)"
	@echo ""
	@echo "Development:"
	@echo "  run          Start the application"
	@echo "  tunnel       Start ngrok tunnel"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint         Check code with ruff"
	@echo "  lint-fix     Auto-fix linting issues"
	@echo "  format       Format code with ruff"
	@echo "  format-check Check code formatting"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean        Remove venv and cache files"

setup:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install ruff

run:
	./venv/bin/python3 run.py

tunnel:
	ngrok http 9090

lint:
	./venv/bin/python3 -m ruff check .

lint-fix:
	./venv/bin/python3 -m ruff check --fix .

format:
	./venv/bin/python3 -m ruff format .

format-check:
	./venv/bin/python3 -m ruff format --check .

certs:
	mkcert -install
	mkcert qbo.journalsmart.app 127.0.0.1 ::1
	@echo ""
	@echo "Certificates created. Add to .env:"
	@echo "  SSL_CERT=qbo.journalsmart.app+2.pem"
	@echo "  SSL_KEY=qbo.journalsmart.app+2-key.pem"

clean:
	rm -rf venv __pycache__ .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
