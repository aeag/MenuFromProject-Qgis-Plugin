# Testing the plugin

Tests are written in 2 separate folders:

- `tests/unit`: testing code which is independent of QGIS API
- `tests/qgis`: testing code which depends on QGIS API

## Requirements

- 3.34 < QGIS < 3.99

```sh
python -m pip install -U -r requirements/testing.txt
```

## Run unit tests

```bash
# run all tests with PyTest and Coverage report
python -m pytest

# run only unit tests with pytest launcher (disabling pytest-qgis)
python -m pytest -p no:qgis tests/unit

# run only QGIS tests with pytest launcher
python -m pytest tests/qgis

# run a specific test module using standard unittest
python -m unittest tests.unit.test_plg_metadata

# run a specific test function using standard unittest
python -m unittest tests.unit.test_plg_metadata.TestPluginMetadata.test_version_semver
```
