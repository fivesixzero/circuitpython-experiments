# Code Checking Workflow

* `pre-commit`/`black`/`pylint` *code quality*
* `mypy` *typing*
* `pylint` *code quality*
* `sphinx` *doc building*

## `pre-commit`/`black`

```sh
pre-commit run --all-files
```

```sh
black --diff .\file.py
```

```
pylint .\dir\
```

## `mypy`

```sh
mypy .\adafruit_macropad.py --disallow-untyped-defs --ignore-missing-imports
```

## `sphinx`

```
cd docs
sphinx-build -E -W -b html . _build/html
```
