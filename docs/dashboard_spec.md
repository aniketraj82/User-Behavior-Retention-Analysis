# Power BI Dashboard Specification

## Data Model

Import all CSV files from `data/processed/`.

Recommended relationships:

- `cohort_retention[cohort_month]` can be used as a cohort axis.
- `daily_active_users[activity_date]` and `monthly_active_users[activity_month]` should connect to a calendar table.
- `dropoff_funnel[segment]` supports channel-level funnel comparison.

## Measures

Create these DAX measures after loading the processed CSVs.

```DAX
Total Users = MAX(dashboard_summary[total_users])

Latest DAU = MAX(dashboard_summary[latest_dau])

Latest MAU = MAX(dashboard_summary[latest_mau])

DAU MAU Stickiness = DIVIDE([Latest DAU], [Latest MAU])

Latest Month Churn Rate = MAX(dashboard_summary[latest_month_churn_rate])

Month 1 Retention =
CALCULATE(
    AVERAGE(cohort_retention[retention_rate]),
    cohort_retention[months_since_signup] = 1
)

Month 3 Retention =
CALCULATE(
    AVERAGE(cohort_retention[retention_rate]),
    cohort_retention[months_since_signup] = 3
)
```

## Page 1: Executive Overview

Recommended visuals:

- KPI cards: Total Users, Latest DAU, Latest MAU, DAU/MAU Stickiness, Latest Month Churn Rate
- Line chart: DAU by activity date
- Line chart: MAU by activity month
- Column chart: monthly new users

## Page 2: Cohort Retention

Recommended visuals:

- Matrix heatmap:
  - Rows: `cohort_month`
  - Columns: `months_since_signup`
  - Values: `retention_rate`
- Line chart:
  - Axis: `cohort_month`
  - Values: Month 1, Month 3, Month 6 retention
- Slicers:
  - Channel
  - Plan
  - Country

## Page 3: Engagement Drop-Off

Recommended visuals:

- Funnel chart:
  - Group: `segment`
  - Stage: `stage`
  - Value: `users`
- Bar chart:
  - Axis: `segment`
  - Value: `dropoff_rate_from_signup`
- Table:
  - Segment
  - Users
  - Conversion from signup
  - Drop-off from signup

## Suggested Dashboard Theme

- Use a restrained business analytics style.
- Prefer white or near-white canvas.
- Use one accent color for primary trends and a contrasting warm color for churn/drop-off.
- Keep cohort heatmaps readable with conditional formatting from low retention to high retention.
