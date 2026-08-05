# Feature testing
A repository designed to collect tests that simulate the features provided by Piattaforma Unitaria.

## Installation
Install [pipenv](https://pipenv.pypa.io/en/latest/):

```
pip install pipenv
```

Create and enter the virtual environment:

```commandline
pipenv shell
```

Install dependencies:

```commandline
pipenv sync
```

Update dependencies:
```commandline
pipenv run pip freeze > requirements.txt
pipenv install -r requirements.txt
```

> **_NOTE_**: Create `pu_feature_secrets.json` based on `pu_feature_secrets_template.json` and customize it.

## Test execution
Run tests:

```commandline
behave [--junit --junit-directory <JUNIT_OUTPUT_DIR>] [--tags @<[TEST_TAG/s]>]
```

For example this command runs tests with tag 'login' and save the junitxml report to a file:

```commandline
behave --junit --junit-directory "tests/reports" --tags login
```
or save the html report to a file:
```commandline
behave -f html-pretty -o ./tests/reports/behave-report.html  
```

## Validating step definitions
You can check that every Gherkin step matches a step definition **without hitting the live APIs**
(the dry-run loads and matches the steps but does not run `before_scenario` or the step bodies):

```commandline
behave --dry-run
```

To list step definitions that are no longer used by any scenario:

```commandline
behave --dry-run -f steps.usage
```

## Project layout
- `bdd/features/` — Gherkin feature files (`.feature`)
- `bdd/steps/` — step definitions (one `*_step.py` per domain area)
- `bdd/steps/utils/` — shared helpers (scenario-state accessors, assertions, builders)
- `bdd/environment.py` — behave hooks; initializes per-scenario state in `before_scenario`
- `api/` — HTTP/SOAP clients
- `model/` — domain models and constants
- `config/` — settings and secrets loading
