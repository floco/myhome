from datetime import datetime, timezone

from myhome.chore_scheduling import next_due_from_schedule
from myhome.models_chores import Chore


def _chore(**overrides) -> Chore:
    base = dict(
        id="c1", name="Test", emoji="🧹", periodDays=7.0,
        frequencyType="interval", frequency=7, frequencyMetadata={"unit": "days"},
        nextDueDate="2026-07-04T00:00:00Z",
    )
    base.update(overrides)
    return Chore(**base)


def test_interval_days_advances_by_frequency():
    chore = _chore(frequencyType="interval", frequency=3, frequencyMetadata={"unit": "days"})
    from_dt = datetime(2026, 7, 4, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 7, tzinfo=timezone.utc)


def test_weekly_advances_by_weeks():
    chore = _chore(frequencyType="weekly", frequency=2)
    from_dt = datetime(2026, 7, 4, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 18, tzinfo=timezone.utc)


def test_monthly_advances_by_months():
    chore = _chore(frequencyType="monthly", frequency=1)
    from_dt = datetime(2026, 1, 31, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result.month == 2
    assert result.day == 28  # clamped to Feb's last day
