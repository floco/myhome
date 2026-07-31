from datetime import datetime, timezone

from myhome.chore_scheduling import adaptive_period_days, next_due_from_schedule
from myhome.models_chores import Chore, CompletionRecord


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


def test_weekly_advances_by_one_week_regardless_of_frequency():
    """Donetick's own scheduler ignores `frequency` for the literal "weekly"
    type (always advances by exactly 1 week) -- the multiplier only applies
    to the "interval" type. A stray `frequency` value must not change this."""
    chore = _chore(frequencyType="weekly", frequency=2)
    from_dt = datetime(2026, 7, 4, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 11, tzinfo=timezone.utc)


def test_monthly_advances_by_months():
    chore = _chore(frequencyType="monthly", frequency=1)
    from_dt = datetime(2026, 1, 31, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result.month == 2
    assert result.day == 28  # clamped to Feb's last day


def test_daily_advances_by_one_day():
    chore = _chore(frequencyType="daily", frequency=1, frequencyMetadata={})
    from_dt = datetime(2026, 7, 4, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_adaptive_period_days_falls_back_to_period_days_with_no_completions():
    chore = _chore(frequencyType="adaptive", periodDays=21.0, frequencyMetadata={})
    assert adaptive_period_days(chore, []) == 21.0


def test_adaptive_period_days_falls_back_to_period_days_with_one_completion():
    chore = _chore(frequencyType="adaptive", periodDays=21.0, frequencyMetadata={})
    completions = [CompletionRecord(id="r1", choreId="c1", completedAt="2026-06-01T00:00:00Z", scheduledDue="")]
    assert adaptive_period_days(chore, completions) == 21.0


def test_adaptive_period_days_averages_last_five_gaps():
    chore = _chore(frequencyType="adaptive", periodDays=21.0, frequencyMetadata={})
    # Gaps between consecutive completions: 10, 20, 30, 40, 50, 60 days.
    # Only the last 5 (20, 30, 40, 50, 60) should count -- average = 40.
    completions = [
        CompletionRecord(id="r1", choreId="c1", completedAt="2026-01-01T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r2", choreId="c1", completedAt="2026-01-11T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r3", choreId="c1", completedAt="2026-01-31T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r4", choreId="c1", completedAt="2026-03-02T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r5", choreId="c1", completedAt="2026-04-11T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r6", choreId="c1", completedAt="2026-05-31T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r7", choreId="c1", completedAt="2026-07-30T00:00:00Z", scheduledDue=""),
    ]
    assert adaptive_period_days(chore, completions) == 40.0


def test_adaptive_next_due_uses_averaged_gap():
    chore = _chore(frequencyType="adaptive", periodDays=21.0, frequencyMetadata={})
    completions = [
        CompletionRecord(id="r1", choreId="c1", completedAt="2026-01-01T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r2", choreId="c1", completedAt="2026-01-11T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r3", choreId="c1", completedAt="2026-01-31T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r4", choreId="c1", completedAt="2026-03-02T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r5", choreId="c1", completedAt="2026-04-11T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r6", choreId="c1", completedAt="2026-05-31T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r7", choreId="c1", completedAt="2026-07-30T00:00:00Z", scheduledDue=""),
    ]
    from_dt = datetime(2026, 7, 30, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt, completions)
    assert result == datetime(2026, 9, 8, tzinfo=timezone.utc)  # 2026-07-30 + 40 days
