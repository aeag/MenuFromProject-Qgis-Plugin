# Development

## Environment setup

> Typically on Ubuntu (but should work on Windows).

### 1. Install virtual environment

Using [qgis-venv-creator](https://github.com/GispoCoding/qgis-venv-creator) (see [this article](https://blog.geotribu.net/2024/11/25/creating-a-python-virtual-environment-for-pyqgis-development-with-vs-code-on-windows/#with-the-qgis-venv-creator-utility)) through [pipx](https://pipx.pypa.io) (`sudo apt install pipx`):

```sh
pipx run qgis-venv-creator
```

Old school way:

```bash
# create virtual environment linking to system packages (for pyqgis)
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
```

### 2. Install development dependencies

```sh
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
