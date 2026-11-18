PYTHON ?= python3
PDK_ROOT ?= ../icsprout55-pdk
CONFIG ?= config/ics55.pdk.yml

.PHONY: generate-tech test

generate-tech:
	PYTHONPATH=src $(PYTHON) -m ics55_klayout_drc.cli generate-tech --config $(CONFIG) --pdk-root $(PDK_ROOT)

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
