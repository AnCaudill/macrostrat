# Macrostrat API script

Python script that queries the [Macrostrat API](https://macrostrat.org/api) for stratigraphic units near a location, summarizes lithology and geologic age, writes a CSV of selected fields, and plots an age column chart plus a lithology pie chart.

## Documentation

- [Macrostrat data services](https://macrostrat.org/docs/data-services)
- [Macrostrat API (v2)](https://macrostrat.org/api/v2)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python macrostrat_api.py
```

Outputs are written to `output/`.
