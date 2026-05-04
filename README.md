# User Behavior & Retention Analysis

Portfolio analytics project for measuring user growth, engagement, churn, and retention using SQL and Python.

## Project Objective

This project analyzes user activity data to answer four business questions:

- How many users are active daily and monthly?
- How well do signup cohorts retain users over time?
- Where do users drop off after signup?
- What product changes could improve retention?

## Tools Used

- SQL for DAU, MAU, retention, churn, and funnel queries
- Python and Pandas for cohort analysis and metric exports
- Matplotlib and Seaborn for visual quality checks
- Power BI-ready CSV outputs for dashboard creation

## Folder Structure

```text
.
├── data/
│   ├── raw/                  # Generated source tables
│   └── processed/            # Dashboard-ready outputs
├── reports/
│   └── figures/              # Chart exports
├── scripts/
│   ├── generate_sample_data.py
│   └── retention_analysis.py
├── sql/
│   ├── dau_mau.sql
│   ├── cohort_retention.sql
│   ├── churn_analysis.sql
│   └── dropoff_funnel.sql
├── docs/
│   ├── dashboard_spec.md
│   └── insights.md
└── requirements.txt
```

## Dataset

The project uses a reproducible synthetic SaaS-style dataset with:

- `users`: user profile, signup date, acquisition channel, plan, country
- `events`: timestamped activity including signup, onboarding, feature usage, and billing events

The data intentionally includes realistic retention behavior:

- Early lifecycle drop-off after signup
- Higher retention for paid and referral users
- Seasonal activity variation
- Churn events after periods of inactivity

## Quick Start

```bash
pip install -r requirements.txt
python scripts/generate_sample_data.py
python scripts/retention_analysis.py
```

## Main Outputs

After running the scripts, `data/processed/` contains:

- `daily_active_users.csv`
- `monthly_active_users.csv`
- `cohort_retention.csv`
- `cohort_retention_matrix.csv`
- `churn_summary.csv`
- `dropoff_funnel.csv`
- `dashboard_summary.csv`

`reports/figures/` contains chart images for retention, DAU, MAU, and funnel validation.

## Dashboard Pages

The Power BI dashboard is designed around three pages:

1. **Executive Overview**
   - Total users
   - DAU and MAU trends
   - DAU/MAU stickiness
   - Latest month churn rate

2. **Cohort Retention**
   - Signup month cohort heatmap
   - Month 1, Month 3, and Month 6 retention trend
   - Filters for channel, plan, and country

3. **Engagement Drop-Off**
   - Signup to onboarding to first key action funnel
   - Drop-off rate by acquisition channel
   - Recommended retention actions

## Key Findings

See `docs/insights.md` for the generated analysis narrative and recommended retention improvements.
