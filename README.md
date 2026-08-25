# Feature testing
A repository designed to collect tests that simulate the features provided by Piattaforma Unitaria.

The tests are written with [behave](https://behave.readthedocs.io/) — a Python BDD
framework — using the **[Gherkin](https://cucumber.io/docs/gherkin/reference/)** syntax,
and the scenario catalogue is built with
[MkDocs](https://www.mkdocs.org/) + [Material](https://squidfunk.github.io/mkdocs-material/).
In BDD terms:

- a **feature** (a `.feature` file) describes one functionality of the platform;
- a **scenario** is a concrete example of that feature, written as `Given` / `When` /
  `Then` steps; each step is backed by a Python function in `bdd/steps/`.

## Contents
- [Scenario documentation](#scenario-documentation)
  - [Documenting complex steps](#documenting-complex-steps)
  - [Previewing locally](#previewing-locally)
- [Project layout](#project-layout)
- [Installation](#installation)
- [Test execution](#test-execution)
- [Validating step definitions](#validating-step-definitions)

## Scenario documentation
A browsable catalogue of the Gherkin scenarios is published to GitHub Pages:

**https://pagopa.github.io/p4pa-pu-feature-test/**

It is generated from `bdd/features/` by `script/scenario_parser.py` and published
automatically by the `.github/workflows/scenario-docs.yml` workflow on every push to
`main`. The site has one page per feature, plus a **Steps glossary** grouped by
Given / When / Then. It only reads the feature and step files — it never runs the
tests, so it needs no secrets or environment access.

### Documenting complex steps
If you add a step that performs **several checks internally** (multiple assertions,
workflow checks, or that orchestrates other steps), give it a **docstring**: a short
summary line followed by a bulleted list of what it checks. The generator shows it as
a clickable **+** annotation next to the step and in the Steps glossary.

Steps that do a single, self-explanatory action should have **no** docstring, so they
stay out of the catalogue. Look at the existing `bdd/steps/*_step.py` for the format
to follow.

### Previewing locally
Install the docs dependencies, generate the pages and serve the site:

```commandline
pip install behave mkdocs mkdocs-material
python script/scenario_parser.py --page-name "Piattaforma Unitaria Functional Testing" --repo-name p4pa-pu-feature-test --root-dir bdd/features
mkdocs serve
```

The generated `docs/`, `site/` and `mkdocs.yml` are build artifacts (git-ignored);
the workflow regenerates them in CI.

## Project layout
- `bdd/features/` — Gherkin feature files (`.feature`)
- `bdd/steps/` — step definitions (one `*_step.py` per domain area)
- `bdd/steps/utils/` — shared helpers (scenario-state accessors, assertions, builders)
- `bdd/environment.py` — behave hooks; initializes per-scenario state in `before_scenario`
- `api/` — HTTP/SOAP clients
- `model/` — domain models and constants
- `config/` — settings and secrets loading
- `script/` — standalone utilities, e.g. `scenario_parser.py` (the docs generator)

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
During local development you usually just run a scenario (or a tag) and check that it
passes:

```commandline
behave --tags=@<tag>
```

For example, to run only the scenarios tagged `@debt_positions`:

```commandline
behave --tags=@debt_positions
```

You rarely need a report locally — the CI pipeline is the one that produces the JUnit
report. If you do want one, add `--junit`:

```commandline
behave --junit --junit-directory "tests/reports" --tags=@debt_positions
```

Or produce an HTML report instead:

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
