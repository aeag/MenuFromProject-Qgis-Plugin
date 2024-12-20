# Development

## Environment setup

Typically on Ubuntu:

```bash
# create virtual environment linking to system packages (for pyqgis)
python3 -m venv .venv --system-site-packages
source .venv/bin/activate

# bump dependencies inside venv
python -m pip install -U pip
python -m pip install -U -r requirements/development.txt

# install git hooks (pre-commit)
pre-commit install
```

----

## Staging (_recette_)

### Project through HTTP

Use the project from the repository: <https://github.com/aeag/MenuFromProject-Qgis-Plugin/raw/master/test/projets/aeag-tiny.qgz>
