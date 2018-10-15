VIRTUALENV = virtualenv --python=python3.6
VENV = .venv
VENV_ACTIVATE = . $(VENV)/bin/activate

HERE = $(shell pwd)
PIP_CONFIG_FILE ?= $(HERE)/pip.conf
PIP_INSTALL = PIP_CONFIG_FILE="$(PIP_CONFIG_FILE)" pip3 install

TOX = PIP_CONFIG_FILE="$(PIP_CONFIG_FILE)" tox

$(VENV):
	$(VIRTUALENV) $(VENV)

setup: $(VENV) ## Install/upgrade project and development requirements in virtual environment.
	$(VENV_ACTIVATE); $(PIP_INSTALL) -r requirements.txt

setup-tests: $(VENV) ## Install/upgrade test requirements in virtual environment.
	$(VENV_ACTIVATE); $(PIP_INSTALL) -r test-requirements.txt


clean:  ## Removes the virtual environment and tox folder
	rm -rf $(VENV)
	rm -rf .tox

test:  ## Run unit tests
	$(PIP_INSTALL) -U pip
	$(PIP_INSTALL) tox
	$(TOX)

venv: $(VENV) ## Create Python virtual environment.

