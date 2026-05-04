from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "reports" / "figures"
DOCS_DIR = ROOT / "docs"

ENGAGEMENT_EVENTS = ["session_start", "feature_used", "report_viewed", "project_updated"]


def month_start(series: pd.Series) -> pd.Series:
    return series.dt.to_period("M").dt.to_timestamp()


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    users_path = RAW_DIR / "users.csv"
    events_path = RAW_DIR / "events.csv"

    if not users_path.exists() or not events_path.exists():
        raise FileNotFoundError(
            "Missing raw data. Run `python scripts/generate_sample_data.py` first."
        )

    users = pd.read_csv(users_path, parse_dates=["signup_date", "signup_month"])
    events = pd.read_csv(events_path, parse_dates=["event_time"])
    events["event_date"] = events["event_time"].dt.date
    events["activity_month"] = month_start(events["event_time"])

    return users, events


def calculate_dau_mau(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    engagement = events[events["event_type"].isin(ENGAGEMENT_EVENTS)].copy()

    dau = (
        engagement.groupby("event_date")["user_id"]
        .nunique()
        .reset_index(name="dau")
        .rename(columns={"event_date": "activity_date"})
    )
    dau["activity_date"] = pd.to_datetime(dau["activity_date"])
    dau["activity_month"] = month_start(dau["activity_date"])

    mau = (
        engagement.groupby("activity_month")["user_id"]
        .nunique()
        .reset_index(name="mau")
        .sort_values("activity_month")
    )

    dau = dau.merge(mau, on="activity_month", how="left")
    dau["dau_mau_stickiness"] = (dau["dau"] / dau["mau"]).round(4)

    return dau, mau


def calculate_cohort_retention(users: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    engagement = events[events["event_type"].isin(ENGAGEMENT_EVENTS)].copy()
    activity = engagement[["user_id", "activity_month"]].drop_duplicates()

    cohorts = users[["user_id", "signup_month", "channel", "plan", "country"]].rename(
        columns={"signup_month": "cohort_month"}
    )
    cohort_activity = activity.merge(cohorts, on="user_id", how="inner")
    cohort_activity = cohort_activity[cohort_activity["activity_month"] >= cohort_activity["cohort_month"]]
    cohort_activity["months_since_signup"] = (
        (cohort_activity["activity_month"].dt.year - cohort_activity["cohort_month"].dt.year) * 12
        + (cohort_activity["activity_month"].dt.month - cohort_activity["cohort_month"].dt.month)
    )

    cohort_size = cohorts.groupby("cohort_month")["user_id"].nunique().reset_index(name="cohort_users")
    retention = (
        cohort_activity.groupby(["cohort_month", "months_since_signup"])["user_id"]
        .nunique()
        .reset_index(name="active_users")
        .merge(cohort_size, on="cohort_month", how="left")
    )
    retention["retention_rate"] = (retention["active_users"] / retention["cohort_users"]).round(4)
    retention = retention[
        ["cohort_month", "months_since_signup", "cohort_users", "active_users", "retention_rate"]
    ].sort_values(["cohort_month", "months_since_signup"])

    matrix = retention.pivot(
        index="cohort_month", columns="months_since_signup", values="retention_rate"
    ).reset_index()
    matrix.columns = ["cohort_month"] + [f"month_{int(col)}" for col in matrix.columns[1:]]

    return retention, matrix


def calculate_churn(events: pd.DataFrame) -> pd.DataFrame:
    engagement = events[events["event_type"].isin(ENGAGEMENT_EVENTS)].copy()

    active_users = (
        engagement.groupby("activity_month")["user_id"]
        .nunique()
        .reset_index(name="active_users")
        .sort_values("activity_month")
    )
    churned = (
        events[events["event_type"] == "churned"]
        .groupby("activity_month")["user_id"]
        .nunique()
        .reset_index(name="churned_users")
    )

    churn = active_users.merge(churned, on="activity_month", how="left").fillna({"churned_users": 0})
    churn["churned_users"] = churn["churned_users"].astype(int)
    churn["prior_month_active_users"] = churn["active_users"].shift(1)
    churn["churn_rate"] = (
        churn["churned_users"] / churn["prior_month_active_users"].replace({0: pd.NA})
    ).fillna(0).round(4)

    return churn


def calculate_dropoff(users: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    stage_flags = (
        events.assign(value=1)
        .pivot_table(index="user_id", columns="event_type", values="value", aggfunc="max", fill_value=0)
        .reset_index()
    )

    for column in ["signup", "onboarding_completed", "first_key_action"]:
        if column not in stage_flags:
            stage_flags[column] = 0

    active_flags = (
        events[events["event_type"].isin(ENGAGEMENT_EVENTS)]
        .groupby("user_id")
        .size()
        .reset_index(name="engagement_events")
    )
    stage_flags = stage_flags.merge(active_flags, on="user_id", how="left").fillna({"engagement_events": 0})
    stage_flags["became_active"] = (stage_flags["engagement_events"] > 0).astype(int)

    user_stages = users[["user_id", "channel", "plan", "country"]].merge(stage_flags, on="user_id", how="left")
    stage_columns = {
        "Signed up": "signup",
        "Completed onboarding": "onboarding_completed",
        "First key action": "first_key_action",
        "Became active": "became_active",
    }

    rows = []
    for segment_name, segment_df in [("All Users", user_stages)] + list(user_stages.groupby("channel")):
        signed_up = int(segment_df["signup"].sum())
        for order, (stage_label, source_column) in enumerate(stage_columns.items(), start=1):
            users_at_stage = int(segment_df[source_column].sum())
            conversion = users_at_stage / signed_up if signed_up else 0
            rows.append(
                {
                    "segment": segment_name,
                    "stage_order": order,
                    "stage": stage_label,
                    "users": users_at_stage,
                    "conversion_from_signup": round(conversion, 4),
                    "dropoff_rate_from_signup": round(1 - conversion, 4),
                }
            )

    return pd.DataFrame(rows)


def create_dashboard_summary(
    users: pd.DataFrame,
    dau: pd.DataFrame,
    mau: pd.DataFrame,
    retention: pd.DataFrame,
    churn: pd.DataFrame,
    dropoff: pd.DataFrame,
) -> pd.DataFrame:
    latest_dau = int(dau.sort_values("activity_date").iloc[-1]["dau"])
    latest_mau = int(mau.sort_values("activity_month").iloc[-1]["mau"])
    latest_churn = float(churn.sort_values("activity_month").iloc[-1]["churn_rate"])
    month_1_retention = float(retention[retention["months_since_signup"] == 1]["retention_rate"].mean())
    month_3_retention = float(retention[retention["months_since_signup"] == 3]["retention_rate"].mean())
    all_users_key_action = dropoff[
        (dropoff["segment"] == "All Users") & (dropoff["stage"] == "First key action")
    ].iloc[0]

    return pd.DataFrame(
        [
            {
                "total_users": len(users),
                "latest_dau": latest_dau,
                "latest_mau": latest_mau,
                "latest_dau_mau_stickiness": round(latest_dau / latest_mau, 4),
                "average_month_1_retention": round(month_1_retention, 4),
                "average_month_3_retention": round(month_3_retention, 4),
                "latest_month_churn_rate": latest_churn,
                "first_key_action_conversion": all_users_key_action["conversion_from_signup"],
            }
        ]
    )


def save_figures(
    dau: pd.DataFrame,
    mau: pd.DataFrame,
    retention: pd.DataFrame,
    matrix: pd.DataFrame,
    dropoff: pd.DataFrame,
) -> None:
    sns.set_theme(style="whitegrid")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(12, 5))
    sns.lineplot(data=dau, x="activity_date", y="dau", color="#2563eb")
    plt.title("Daily Active Users")
    plt.xlabel("Date")
    plt.ylabel("DAU")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "daily_active_users.png", dpi=160)
    plt.close()

    plt.figure(figsize=(10, 5))
    sns.lineplot(data=mau, x="activity_month", y="mau", marker="o", color="#0891b2")
    plt.title("Monthly Active Users")
    plt.xlabel("Month")
    plt.ylabel("MAU")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "monthly_active_users.png", dpi=160)
    plt.close()

    heatmap_data = matrix.set_index("cohort_month").drop(columns=[], errors="ignore")
    heatmap_data.index = heatmap_data.index.strftime("%Y-%m")
    plt.figure(figsize=(13, 8))
    sns.heatmap(heatmap_data, cmap="YlGnBu", annot=False, vmin=0, vmax=1)
    plt.title("Signup Cohort Retention")
    plt.xlabel("Months Since Signup")
    plt.ylabel("Signup Cohort")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "cohort_retention_heatmap.png", dpi=160)
    plt.close()

    funnel = dropoff[dropoff["segment"] == "All Users"].sort_values("stage_order")
    plt.figure(figsize=(9, 5))
    sns.barplot(data=funnel, x="stage", y="users", color="#f97316")
    plt.title("Activation Funnel")
    plt.xlabel("")
    plt.ylabel("Users")
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "activation_funnel.png", dpi=160)
    plt.close()


def write_insights(summary: pd.DataFrame, retention: pd.DataFrame, dropoff: pd.DataFrame, churn: pd.DataFrame) -> None:
    metrics = summary.iloc[0]
    month_1 = metrics["average_month_1_retention"]
    month_3 = metrics["average_month_3_retention"]

    latest_churn = churn.sort_values("activity_month").iloc[-1]
    funnel = dropoff[dropoff["segment"] == "All Users"].sort_values("stage_order")
    onboarding = funnel[funnel["stage"] == "Completed onboarding"].iloc[0]
    key_action = funnel[funnel["stage"] == "First key action"].iloc[0]

    channel_key_actions = dropoff[dropoff["stage"] == "First key action"].copy()
    channel_key_actions = channel_key_actions[channel_key_actions["segment"] != "All Users"]
    weakest_channel = channel_key_actions.sort_values("conversion_from_signup").iloc[0]
    strongest_channel = channel_key_actions.sort_values("conversion_from_signup", ascending=False).iloc[0]

    cohort_recent = retention[retention["months_since_signup"] == 1].sort_values("cohort_month").tail(6)
    recent_month_1 = cohort_recent["retention_rate"].mean()

    content = f"""# Retention Insights

## Executive Summary

The analysis covers {int(metrics["total_users"]):,} users and shows a latest DAU of {int(metrics["latest_dau"]):,}, latest MAU of {int(metrics["latest_mau"]):,}, and DAU/MAU stickiness of {metrics["latest_dau_mau_stickiness"]:.1%}.

Average Month 1 retention is {month_1:.1%}; average Month 3 retention is {month_3:.1%}. The latest observed monthly churn rate is {latest_churn["churn_rate"]:.1%}.

## Cohort Retention

Signup cohorts retain best in the first month, then decline steadily through Month 3 and Month 6. The most recent six cohorts have average Month 1 retention of {recent_month_1:.1%}, which should be monitored as the leading indicator for long-term retention.

## Engagement Drop-Off

The largest early lifecycle risk is before the first key action:

- Onboarding completion rate: {onboarding["conversion_from_signup"]:.1%}
- First key action conversion rate: {key_action["conversion_from_signup"]:.1%}
- Drop-off before first key action: {key_action["dropoff_rate_from_signup"]:.1%}

By channel, `{weakest_channel["segment"]}` has the weakest first-key-action conversion at {weakest_channel["conversion_from_signup"]:.1%}, while `{strongest_channel["segment"]}` performs best at {strongest_channel["conversion_from_signup"]:.1%}.

## Recommendations

1. Improve the first-session activation path with a shorter onboarding flow and clearer next best action.
2. Trigger lifecycle emails or in-app nudges for users who sign up but do not complete onboarding within 24 hours.
3. Create channel-specific onboarding for lower-converting acquisition sources, especially `{weakest_channel["segment"]}`.
4. Study successful behaviors from `{strongest_channel["segment"]}` users and reuse those prompts in weaker channels.
5. Track Month 1 retention as the north-star early retention metric, with supporting KPIs for onboarding completion and first key action conversion.
"""
    (DOCS_DIR / "insights.md").write_text(content, encoding="utf-8")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    users, events = load_data()
    dau, mau = calculate_dau_mau(events)
    retention, matrix = calculate_cohort_retention(users, events)
    churn = calculate_churn(events)
    dropoff = calculate_dropoff(users, events)
    summary = create_dashboard_summary(users, dau, mau, retention, churn, dropoff)

    dau.to_csv(PROCESSED_DIR / "daily_active_users.csv", index=False)
    mau.to_csv(PROCESSED_DIR / "monthly_active_users.csv", index=False)
    retention.to_csv(PROCESSED_DIR / "cohort_retention.csv", index=False)
    matrix.to_csv(PROCESSED_DIR / "cohort_retention_matrix.csv", index=False)
    churn.to_csv(PROCESSED_DIR / "churn_summary.csv", index=False)
    dropoff.to_csv(PROCESSED_DIR / "dropoff_funnel.csv", index=False)
    summary.to_csv(PROCESSED_DIR / "dashboard_summary.csv", index=False)

    save_figures(dau, mau, retention, matrix, dropoff)
    write_insights(summary, retention, dropoff, churn)

    print("Analysis complete")
    print(summary.to_string(index=False))
    print(f"Processed files: {PROCESSED_DIR}")
    print(f"Figures: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
