## Developing `djangocms-moderation`

To set up your development environment you need to
* prepare a virtual environment: `python3 -m venv .venv`
* activate it: `source .venv/bin/activate`
* install dependencies, e.g. `pip install -r tests/requirements/dj52_cms51.txt`

Tests can be executed using `coverage run -m pytest`.
Coding conventions can be checked by running `ruff check`.