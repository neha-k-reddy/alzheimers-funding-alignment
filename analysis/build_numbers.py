"""
build_numbers.py
=================
Generates numbers.json — the single source of truth for the website.

This script reads data/final_dataset.csv and produces every number the website
displays. Run this whenever the underlying data changes:

    python analysis/build_numbers.py

Output: site/public/data/numbers.json

The website MUST read all displayed numbers from this file. If a number isn't
in numbers.json, it doesn't appear on the website.

Author: Neha K. Reddy
Project: NIH Alzheimer's Funding Alignment
"""

import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

# ----- Paths -----
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_PATH = PROJECT_ROOT / "data" / "final_dataset.csv"
OUTPUT_PATH = PROJECT_ROOT / "site" / "public" / "data" / "numbers.json"

# Region for the 5 rows where Region == '0' in the source data
# (Alaska 2019-2021, Idaho 2020-2021 — preprocessing bug).
# We replicate the paper's behavior: exclude these rows from regional aggregates,
# but keep them in everything else (state-level data, time series, regression).
PAPER_REGIONAL_FILTER = True  # If True, exclude Region='0' rows from regional aggregates


# ----- Helpers -----
def round_currency(x):
    """Round currency values for display."""
    return round(float(x), 2)


def load_data():
    """Load and return the final processed dataset."""
    df = pd.read_csv(DATA_PATH)
    return df


def compute_state_year_metrics(df):
    """
    Per-state, per-year metrics for the choropleth map and tooltips.
    Returns a dict keyed by year, then by state code.
    """
    metrics = {}
    for year in sorted(df["Year"].unique()):
        df_year = df[df["Year"] == year]
        year_data = {}
        for _, row in df_year.iterrows():
            state_code = row["State_Code"]
            year_data[state_code] = {
                "state_name": row["State"],
                "funding_per_death": (
                    None
                    if pd.isna(row["Funding_Per_Death"])
                    else round_currency(row["Funding_Per_Death"])
                ),
                "total_funding": (
                    None
                    if pd.isna(row["Total_Funding_Annual"])
                    else round_currency(row["Total_Funding_Annual"])
                ),
                "total_deaths": (
                    None
                    if pd.isna(row["Total_Deaths_Annual"])
                    else int(row["Total_Deaths_Annual"])
                ),
                "mortality_rate_per_100k": (
                    None
                    if pd.isna(row["Mortality_Rate_Per_100k"])
                    else round(float(row["Mortality_Rate_Per_100k"]), 2)
                ),
                "population_total": (
                    None
                    if pd.isna(row["Total_Population"])
                    else int(row["Total_Population"])
                ),
                "population_65plus": (
                    None
                    if pd.isna(row["Population_65plus"])
                    else int(row["Population_65plus"])
                ),
                "population_85plus": (
                    None
                    if pd.isna(row["Population_85plus"])
                    else int(row["Population_85plus"])
                ),
                "num_r1_universities": (
                    None
                    if pd.isna(row["Num_R1_Universities"])
                    else int(row["Num_R1_Universities"])
                ),
                "median_income": (
                    None if pd.isna(row["Median_Income"]) else int(row["Median_Income"])
                ),
                "region": row["Region"] if row["Region"] != "0" else "West",
            }
        metrics[int(year)] = year_data
    return metrics


def compute_national_yearly(df):
    """National aggregates per year (for time series chart)."""
    yearly = []
    for year in sorted(df["Year"].unique()):
        df_year = df[df["Year"] == year]
        total_funding = float(df_year["Total_Funding_Annual"].sum())
        total_deaths = int(df_year["Total_Deaths_Annual"].sum())
        total_population = int(df_year["Total_Population"].sum())
        total_65plus = int(df_year["Population_65plus"].sum())
        yearly.append(
            {
                "year": int(year),
                "total_funding": round_currency(total_funding),
                "total_deaths_panel": total_deaths,
                "total_population": total_population,
                "total_65plus": total_65plus,
                "funding_per_death_panel": round_currency(total_funding / total_deaths),
                "funding_per_65plus": round_currency(total_funding / total_65plus),
            }
        )
    return yearly


def compute_regional_aggregates(df):
    """
    Regional means by year and overall.

    Replicates paper's methodology: mean of state-level Funding_Per_Death
    within each region, excluding Region='0' rows (preprocessing bug
    affecting AK 2019-2021 and ID 2020-2021).
    """
    if PAPER_REGIONAL_FILTER:
        df_clean = df[df["Region"] != "0"].copy()
    else:
        df_clean = df.copy()
        df_clean.loc[df_clean["Region"] == "0", "Region"] = "West"

    # All-years pooled (matches paper's Figure 7)
    pooled = (
        df_clean.groupby("Region")
        .agg(
            funding_per_death_mean=("Funding_Per_Death", "mean"),
            funding_per_65plus_mean=("Funding_Per_65plus", "mean"),
            total_funding=("Total_Funding_Annual", "sum"),
            total_deaths=("Total_Deaths_Annual", "sum"),
            num_states_year_pairs=("State", "count"),
        )
        .reset_index()
    )

    pooled_dict = {}
    for _, row in pooled.iterrows():
        pooled_dict[row["Region"]] = {
            "funding_per_death": round_currency(row["funding_per_death_mean"]),
            "funding_per_65plus": round_currency(row["funding_per_65plus_mean"]),
            "total_funding_5yr": round_currency(row["total_funding"]),
            "total_deaths_5yr": int(row["total_deaths"]),
        }

    # Yearly regional means
    yearly = (
        df_clean.groupby(["Year", "Region"])["Funding_Per_Death"].mean().reset_index()
    )
    yearly_dict = {}
    for year in sorted(yearly["Year"].unique()):
        yearly_dict[int(year)] = {
            row["Region"]: round_currency(row["Funding_Per_Death"])
            for _, row in yearly[yearly["Year"] == year].iterrows()
        }

    return {"pooled_2019_2023": pooled_dict, "yearly": yearly_dict}


def compute_state_rankings(df, year=2023, metric="Funding_Per_Death"):
    """
    State rankings for a given year on a given metric.
    Full ranked list — site can show top/bottom 5 or all.
    """
    df_year = df[df["Year"] == year].copy()
    df_year = df_year.sort_values(metric, ascending=False).reset_index(drop=True)

    rankings = []
    for rank, (_, row) in enumerate(df_year.iterrows(), start=1):
        rankings.append(
            {
                "rank": rank,
                "state": row["State"],
                "state_code": row["State_Code"],
                "value": round_currency(row[metric])
                if not pd.isna(row[metric])
                else None,
            }
        )
    return rankings


def compute_state_rankings_multiyear(df, metric="Funding_Per_Death"):
    """
    State rankings by 5-year average (2019-2023) of the metric.
    This is what the website's 'Top/Bottom 5 States' typically shows.

    Note: 5 rows in the source data have State_Code='0' (Alaska 2019-2021,
    Idaho 2020-2021) due to a preprocessing bug. These rows also have
    Funding_Per_Death=0, which is incorrect. We exclude them so each state
    is averaged only over years with valid data.
    """
    df_clean = df[df["State_Code"] != "0"].copy()

    state_avg = (
        df_clean.groupby("State")
        .agg(
            value=(metric, "mean"),
            state_code=("State_Code", "first"),
            n_years=("Year", "count"),
        )
        .reset_index()
        .sort_values("value", ascending=False)
        .reset_index(drop=True)
    )

    rankings = []
    for rank, (_, row) in enumerate(state_avg.iterrows(), start=1):
        rankings.append(
            {
                "rank": rank,
                "state": row["State"],
                "state_code": row["state_code"],
                "value": round_currency(row["value"])
                if not pd.isna(row["value"])
                else None,
                "n_years_in_avg": int(row["n_years"]),
            }
        )
    return rankings


def run_regression(df):
    """
    Reproduce the paper's main regression (Model 3 from the notebook):
    Pooled OLS with HC3 robust standard errors.

    Note: coefficients here reflect the FINAL dataset and may differ slightly
    from the paper PDF, which was submitted before final data cleaning.
    Qualitative findings are identical (mortality not significant, R1
    universities are dominant predictor, Adj R² ≈ 0.824).
    """
    X_vars = [
        "Num_R1_Universities",
        "Population_65plus",
        "Population_85plus",
        "Median_Income",
        "Mortality_Rate_Per_100k",
    ]
    X = df[X_vars].copy()
    y = df["Total_Funding_Annual"]

    mask = X.notna().all(axis=1) & y.notna()
    X = sm.add_constant(X[mask])
    y = y[mask]

    model = sm.OLS(y, X).fit(cov_type="HC3")

    pretty_names = {
        "const": "Constant",
        "Num_R1_Universities": "R1 Research Universities",
        "Population_65plus": "Population Age 65+",
        "Population_85plus": "Population Age 85+",
        "Median_Income": "Median Household Income",
        "Mortality_Rate_Per_100k": "Alzheimer's Mortality Rate (per 100k)",
    }
    descriptions = {
        "const": "Intercept",
        "Num_R1_Universities": "Number of R1 research universities in state",
        "Population_65plus": "Population ages 65 and older",
        "Population_85plus": "Population ages 85 and older",
        "Median_Income": "Median household income (USD)",
        "Mortality_Rate_Per_100k": "Alzheimer's deaths per 100,000 population",
    }

    coefficients = []
    for var in X.columns:
        coefficients.append(
            {
                "variable": pretty_names.get(var, var),
                "raw_name": var,
                "description": descriptions.get(var, ""),
                "coefficient": round(float(model.params[var]), 2),
                "std_error": round(float(model.bse[var]), 2),
                "p_value": round(float(model.pvalues[var]), 4),
                "significant": bool(model.pvalues[var] < 0.05),
            }
        )

    return {
        "model_specification": (
            "Pooled OLS regression with HC3 heteroscedasticity-robust standard errors. "
            "Dependent variable: Total NIH Alzheimer's research funding (USD) per state-year."
        ),
        "n_observations": int(model.nobs),
        "r_squared": round(float(model.rsquared), 4),
        "adj_r_squared": round(float(model.rsquared_adj), 4),
        "f_statistic": round(float(model.fvalue), 2),
        "f_pvalue": float(model.f_pvalue),
        "coefficients": coefficients,
    }


def build_landing_summary(df, regional, regression):
    """Summary numbers for the Landing page hero card."""
    pooled = regional["pooled_2019_2023"]
    ne = pooled["Northeast"]["funding_per_death"]
    west = pooled["West"]["funding_per_death"]
    return {
        "northeast_funding_per_death": ne,
        "west_funding_per_death": west,
        "ne_to_west_ratio": round(ne / west, 2),
        "ne_to_west_ratio_display": f"{round(ne / west, 1)}×",
        "adj_r_squared": regression["adj_r_squared"],
        "r1_university_coefficient_millions": round(
            next(
                c["coefficient"]
                for c in regression["coefficients"]
                if c["raw_name"] == "Num_R1_Universities"
            )
            / 1e6,
            1,
        ),
        "mortality_p_value": next(
            c["p_value"]
            for c in regression["coefficients"]
            if c["raw_name"] == "Mortality_Rate_Per_100k"
        ),
    }


def build_metadata(df):
    """Metadata about the dataset and analysis."""
    return {
        "panel_years": "2019-2023",
        "panel_observations": len(df),
        "n_states": int(df["State"].nunique()),
        "n_years": int(df["Year"].nunique()),
        "data_sources": [
            {
                "name": "CDC WONDER",
                "description": "Alzheimer's disease mortality (ICD-10 G30)",
                "years": "2019-2023",
                "url": "https://wonder.cdc.gov/",
            },
            {
                "name": "NIH RePORTER",
                "description": "NIH research funding (projects tagged 'Alzheimer's Disease')",
                "years": "2019-2023",
                "url": "https://reporter.nih.gov/",
            },
            {
                "name": "NORC Dementia DataHub",
                "description": "State-level dementia prevalence estimates",
                "years": "2020",
                "url": "https://www.norc.org/research/projects/dementia-datahub.html",
            },
            {
                "name": "U.S. Census Bureau",
                "description": "State population estimates and demographics",
                "years": "2019-2023",
                "url": "https://www.census.gov/",
            },
            {
                "name": "Bureau of Labor Statistics",
                "description": "Consumer Price Index for inflation adjustment",
                "years": "2019-2023",
                "url": "https://www.bls.gov/cpi/",
            },
        ],
        "data_notes": [
            (
                "Paper headline of 'over 114,000 deaths' refers to the CDC national "
                "Alzheimer's mortality figure for 2023. The state-level analysis "
                "panel sums to fewer deaths because CDC suppresses state-year cells "
                "with counts below 10 for privacy. The regression and regional "
                "analyses are based on the state-level panel."
            ),
            (
                "Five rows in the source data had missing Region values (Alaska "
                "2019-2021, Idaho 2020-2021). These are excluded from regional "
                "aggregates to match the paper. They are included in state-level "
                "data and the regression."
            ),
            (
                "Regression coefficients reflect the final dataset. The paper PDF "
                "reports preliminary values for some coefficients from an earlier "
                "version of the analysis. Qualitative findings — particularly that "
                "mortality rate is not a statistically significant predictor of NIH "
                "funding — are identical in both."
            ),
        ],
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "schema_version": "1.0",
    }


def main():
    print("Loading data...")
    df = load_data()
    print(f"  Loaded {len(df)} rows, {df['State'].nunique()} states, "
          f"{df['Year'].nunique()} years\n")

    print("Computing state-year metrics...")
    state_year = compute_state_year_metrics(df)

    print("Computing national yearly aggregates...")
    national_yearly = compute_national_yearly(df)

    print("Computing regional aggregates...")
    regional = compute_regional_aggregates(df)

    print("Computing state rankings...")
    rankings_2023 = compute_state_rankings(df, year=2023, metric="Funding_Per_Death")
    rankings_5yr_avg = compute_state_rankings_multiyear(df, metric="Funding_Per_Death")

    print("Running regression...")
    regression = run_regression(df)
    print(f"  N = {regression['n_observations']}, "
          f"Adj R² = {regression['adj_r_squared']}")

    print("Building landing summary and metadata...")
    landing = build_landing_summary(df, regional, regression)
    metadata = build_metadata(df)

    output = {
        "metadata": metadata,
        "landing": landing,
        "national_yearly": national_yearly,
        "regional": regional,
        "state_year": state_year,
        "rankings_2023": rankings_2023,
        "rankings_5yr_avg": rankings_5yr_avg,
        "regression": regression,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    file_size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\n✓ Wrote {OUTPUT_PATH} ({file_size_kb:.1f} KB)")
    print(f"\nKey figures:")
    print(f"  Northeast funding/death (2019-2023 mean): ${landing['northeast_funding_per_death']:,.2f}")
    print(f"  West funding/death (2019-2023 mean):      ${landing['west_funding_per_death']:,.2f}")
    print(f"  Ratio:                                     {landing['ne_to_west_ratio_display']}")
    print(f"  Regression Adj R²:                         {landing['adj_r_squared']}")
    print(f"  R1 university coefficient:                 ${landing['r1_university_coefficient_millions']}M")
    print(f"  Mortality rate p-value:                    {landing['mortality_p_value']:.4f}")


if __name__ == "__main__":
    main()
