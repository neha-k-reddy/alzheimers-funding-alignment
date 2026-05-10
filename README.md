# The Alzheimer's Funding Alignment

A state-level analysis of NIH Alzheimer's research funding equity, 2019–2023.

This repository contains the data analysis, regression model, and interactive
website for an independent research project examining whether NIH funding
allocation aligns with state-level Alzheimer's disease burden.

## Project Structure

- `/analysis` — Python scripts that produce numbers.json from raw data
- `/data` — Raw data from CDC WONDER, NIH RePORTER, NORC, Census, BLS
- `/site` — Astro static site (the public-facing website)
- `/paper` — Research paper PDF and source

## Reproducibility

To reproduce the analysis:
1. Clone this repository
2. Install Python dependencies: `pip install -r analysis/requirements.txt`
3. Run: `python analysis/build_numbers.py`
4. This generates `site/public/data/numbers.json`

To run the website locally:
1. `cd site`
2. `npm install`
3. `npm run dev`

## Data Sources

- CDC WONDER (Alzheimer's mortality, 2019–2023)
- NIH RePORTER (research funding, 2019–2023)
- NORC Dementia DataHub (prevalence estimates, 2020)
- U.S. Census Bureau (population, 2019–2023)
- Bureau of Labor Statistics (CPI, 2019–2023)

## Citation

Reddy, N. (2025). The Alzheimer's Funding Atlas: A state-level analysis of
NIH Alzheimer's research funding, 2019–2023. https://alzheimers-funding-alignment.vercel.app/

## License

Code: MIT License. Data: public domain (federal sources).

## TODO Before Public Launch

- [ ] Add live website URL to citation
- [ ] Verify all GitHub links resolve
- [ ] Confirm reproducibility instructions work from a fresh clone
- [ ] Update "Last Updated" date on website

