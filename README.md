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

> **_NOTE_**: Create `pu_feature_secrets.yaml` based on `pu_feature_secrets_template.yaml` and customize it.

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