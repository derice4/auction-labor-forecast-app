"""
ai_summary.py
Calls the Claude API to generate a plain-English supervisor briefing
based on the structured forecast context produced by forecast_engine.py.
"""

import os
import json
import requests
from typing import Optional

API_URL = "https://api.anthropic.com/v1/messages"
MODEL   = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """
You are an operations analyst assistant for an auto auction facility.
Your job is to turn structured forecast data into a clear, concise
daily staffing briefing that a floor supervisor can read in 30 seconds.

Guidelines:
- Write in plain English, no jargon
- Lead with the most important number (total staff needed today)
- Call out sale days, high volume, or unusual variances
- Keep it to 4–6 sentences
- End with one actionable recommendation if the data warrants it
- Do not include headers or bullet points — write it as a paragraph
"""


def _build_prompt(context: dict) -> str:
    return f"""
Here is today's forecast data for the auction facility:

Date: {context['date']} ({context['day_of_week']})
Sale Day: {'Yes' if context['is_sale_day'] else 'No'}
Planned Vehicle Volume: {context['planned_volume']} cars
Actual Volume (if known): {context['actual_volume']} cars

Staffing Breakdown (planned):
  - Check-In:       {context['staff_breakdown']['check_in']} staff
  - Detailing:      {context['staff_breakdown']['detailing']} staff
  - Transport:      {context['staff_breakdown']['transport']} staff
  - Title/Admin:    {context['staff_breakdown']['title_admin']} staff
  - Lane Support:   {context['staff_breakdown']['lane_support']} staff
  - TOTAL:          {context['total_planned_staff']} staff

Actual Staff Who Showed: {context['total_actual_staff']}
Staff Variance (actual - planned): {context['variance_staff']:+d}

Recent 4-Week Avg Variance: {context['recent_avg_variance_pct']:+.1f}%
High-Variance Days in Last Month: {context['anomaly_days_last_month']}

Write the supervisor briefing now.
""".strip()


def generate_summary(context: dict, api_key: Optional[str] = None) -> str:
    """
    Generate a natural language staffing summary using the Claude API.

    Args:
        context:  Dict produced by forecast_engine.build_forecast_context()
        api_key:  Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        Plain-text summary string.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return (
            "⚠️  No API key found. Set the ANTHROPIC_API_KEY environment "
            "variable or pass api_key= to generate_summary()."
        )

    payload = {
        "model":      MODEL,
        "max_tokens": 300,
        "system":     SYSTEM_PROMPT,
        "messages":   [{"role": "user", "content": _build_prompt(context)}],
    }

    headers = {
        "x-api-key":         key,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
    except requests.exceptions.HTTPError as e:
        return f"API error {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Unexpected error: {e}"


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from forecast.forecast_engine import build_forecast_context
    from datetime import date

    ctx = build_forecast_context(date(2024, 4, 2))   # a Tuesday (sale day)
    print("=== Forecast Context ===")
    print(json.dumps(ctx, indent=2))
    print("\n=== AI Summary ===")
    print(generate_summary(ctx))
