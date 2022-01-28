# Code Checking Workflow

* `pre-commit` *code quality*
* `mypy` *typing*
* `sphinx` *doc building*

## `pre-commit`/`black`

```sh
black --diff .\file.py
```

```sh
pre-commit run --all-files
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
