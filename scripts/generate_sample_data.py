from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


def month_start(value: pd.Timestamp) -> pd.Timestamp:
    return value.to_period("M").to_timestamp()


def generate_users(seed: int = 42, n_users: int = 2500) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    signup_dates = pd.to_datetime(
        rng.choice(pd.date_range("2024-01-01", "2025-12-31", freq="D"), size=n_users)
    )

    channels = rng.choice(
        ["Organic Search", "Paid Search", "Referral", "Social", "Email"],
        p=[0.34, 0.22, 0.18, 0.16, 0.10],
        size=n_users,
    )
    plans = rng.choice(["Free", "Starter", "Pro"], p=[0.62, 0.28, 0.10], size=n_users)
    countries = rng.choice(
        ["United States", "India", "United Kingdom", "Canada", "Australia", "Germany"],
        p=[0.34, 0.24, 0.13, 0.11, 0.09, 0.09],
        size=n_users,
    )

    users = pd.DataFrame(
        {
            "user_id": np.arange(1, n_users + 1),
            "signup_date": signup_dates,
            "signup_month": [month_start(date) for date in signup_dates],
            "channel": channels,
            "plan": plans,
            "country": countries,
        }
    ).sort_values("signup_date")

    return users.reset_index(drop=True)


def retention_probability(user: pd.Series, month_index: int) -> float:
    base = 0.82 * np.exp(-0.22 * month_index)
    plan_lift = {"Free": -0.05, "Starter": 0.05, "Pro": 0.11}[user["plan"]]
    channel_lift = {
        "Referral": 0.08,
        "Organic Search": 0.03,
        "Email": 0.01,
        "Paid Search": -0.04,
        "Social": -0.06,
    }[user["channel"]]
    return float(np.clip(base + plan_lift + channel_lift, 0.06, 0.94))


def generate_events(users: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    end_date = pd.Timestamp("2026-03-31")
    events: list[dict[str, object]] = []

    for user in users.itertuples(index=False):
        signup_date = pd.Timestamp(user.signup_date)
        user_record = {
            "plan": user.plan,
            "channel": user.channel,
        }

        events.append(
            {
                "user_id": user.user_id,
                "event_time": signup_date + pd.Timedelta(hours=int(rng.integers(0, 24))),
                "event_type": "signup",
                "feature": "account",
            }
        )

        completed_onboarding = rng.random() < (
            0.72
            + (0.08 if user.plan != "Free" else 0)
            + (0.07 if user.channel == "Referral" else 0)
            - (0.05 if user.channel == "Social" else 0)
        )
        if completed_onboarding:
            events.append(
                {
                    "user_id": user.user_id,
                    "event_time": signup_date + pd.Timedelta(days=int(rng.integers(0, 4))),
                    "event_type": "onboarding_completed",
                    "feature": "activation",
                }
            )

        first_key_action = completed_onboarding and rng.random() < (
            0.66 + (0.12 if user.plan == "Pro" else 0) + (0.06 if user.channel == "Referral" else 0)
        )
        if first_key_action:
            events.append(
                {
                    "user_id": user.user_id,
                    "event_time": signup_date + pd.Timedelta(days=int(rng.integers(1, 8))),
                    "event_type": "first_key_action",
                    "feature": "workspace",
                }
            )

        active_month = month_start(signup_date)
        month_index = 0
        last_active_date = signup_date

        while active_month <= month_start(end_date):
            probability = retention_probability(pd.Series(user_record), month_index)
            if first_key_action:
                probability += 0.06
            if rng.random() < probability:
                days_in_month = pd.Period(active_month, freq="M").days_in_month
                activity_days = int(
                    rng.poisson({"Free": 3, "Starter": 6, "Pro": 10}[user.plan]) + 1
                )
                activity_days = min(activity_days, days_in_month)
                selected_days = rng.choice(np.arange(days_in_month), size=activity_days, replace=False)

                for day_offset in selected_days:
                    event_date = active_month + pd.Timedelta(days=int(day_offset))
                    if event_date < signup_date or event_date > end_date:
                        continue
                    event_count = int(rng.integers(1, 4))
                    for _ in range(event_count):
                        events.append(
                            {
                                "user_id": user.user_id,
                                "event_time": event_date
                                + pd.Timedelta(hours=int(rng.integers(7, 23)))
                                + pd.Timedelta(minutes=int(rng.integers(0, 60))),
                                "event_type": rng.choice(
                                    ["session_start", "feature_used", "report_viewed", "project_updated"],
                                    p=[0.42, 0.34, 0.14, 0.10],
                                ),
                                "feature": rng.choice(
                                    ["dashboard", "workspace", "automation", "reporting"],
                                    p=[0.36, 0.34, 0.16, 0.14],
                                ),
                            }
                        )
                    last_active_date = max(last_active_date, event_date)

            active_month = active_month + pd.DateOffset(months=1)
            month_index += 1

        inactive_days = (end_date - last_active_date).days
        if inactive_days >= 45 and rng.random() < 0.22:
            churn_date = last_active_date + pd.Timedelta(days=int(rng.integers(31, min(inactive_days, 90) + 1)))
            events.append(
                {
                    "user_id": user.user_id,
                    "event_time": churn_date,
                    "event_type": "churned",
                    "feature": "account",
                }
            )

    return pd.DataFrame(events).sort_values(["event_time", "user_id"]).reset_index(drop=True)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    users = generate_users()
    events = generate_events(users)

    users.to_csv(RAW_DIR / "users.csv", index=False)
    events.to_csv(RAW_DIR / "events.csv", index=False)

    print(f"Generated {len(users):,} users")
    print(f"Generated {len(events):,} events")
    print(f"Wrote files to {RAW_DIR}")


if __name__ == "__main__":
    main()
