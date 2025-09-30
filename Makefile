test-banking:
	pytest banking/tests.py -v

test-agents:
	pytest agents/tests.py -v

test-simulation:
	pytest tests.py -v