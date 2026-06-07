.PHONY: help venv run scan pair settime userinfo goal data all clean lint test diagnostics

help: ## Show available commands
	@echo "Available commands:"
	@echo "  make venv       - Create virtual environment"
	@echo "  make run        - Run the VeryFit client"
	@echo "  make scan       - Scan for BLE devices"
	@echo "  make diagnostics- Run BLE diagnostics"
	@echo "  make pair       - Pair with device"
	@echo "  make settime    - Set device time"
	@echo "  make userinfo   - Set user info"
	@echo "  make goal       - Set daily goals"
	@echo "  make data       - Request health data"
	@echo "  make all        - Full setup (pair + time + userinfo + goal)"
	@echo "  make lint       - Run ruff linter"
	@echo "  make clean      - Remove virtual environment and cache files"

venv: ## Create virtual environment
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run: ## Run the VeryFit client
	.venv/bin/python veryfit_client.py $(args)

diagnostics: ## Run BLE diagnostics
	.venv/bin/python diagnostics.py

scan: ## Scan for BLE devices
	.venv/bin/python veryfit_client.py scan

pair: ## Pair with device (usage: make pair DEVICE="WowME ID217G")
ifndef DEVICE
	$(error DEVICE not set. Usage: make pair DEVICE="WowME ID217G")
endif
	.venv/bin/python veryfit_client.py pair $(DEVICE)

settime: ## Set device time (usage: make settime DEVICE="WowME ID217G")
ifndef DEVICE
	$(error DEVICE not set. Usage: make settime DEVICE="WowME ID217G")
endif
	.venv/bin/python veryfit_client.py settime $(DEVICE)

userinfo: ## Set user info (usage: make userinfo DEVICE="WowME ID217G")
ifndef DEVICE
	$(error DEVICE not set. Usage: make userinfo DEVICE="WowME ID217G")
endif
	.venv/bin/python veryfit_client.py userinfo $(DEVICE)

goal: ## Set daily goals (usage: make goal DEVICE="WowME ID217G")
ifndef DEVICE
	$(error DEVICE not set. Usage: make goal DEVICE="WowME ID217G")
endif
	.venv/bin/python veryfit_client.py goal $(DEVICE)

data: ## Request health data (usage: make data DEVICE="WowME ID217G")
ifndef DEVICE
	$(error DEVICE not set. Usage: make data DEVICE="WowME ID217G")
endif
	.venv/bin/python veryfit_client.py data $(DEVICE)

all: ## Full setup (usage: make all DEVICE="WowME ID217G")
ifndef DEVICE
	$(error DEVICE not set. Usage: make all DEVICE="WowME ID217G")
endif
	.venv/bin/python veryfit_client.py all $(DEVICE)

lint: ## Run ruff linter
	ruff check veryfit_client.py

clean: ## Remove virtual environment and cache files
	rm -rf .venv __pycache__ .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
