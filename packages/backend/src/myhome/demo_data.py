from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from .demo_content import CHORES
from .demo_geometry import room_centroid
from .models import HouseDocument, Room
from .models_chores import Assignment, ChoreDocument, Chore, CompletionRecord, Position


def _find_room(house: HouseDocument, label: str) -> Room:
    for floor in house.floors:
        for room in floor.rooms:
            if room.label == label:
                return room
    # Fall back to any room so a typo'd hint never crashes generation.
    return house.floors[0].rooms[0]


def _floor_id_for_room(house: HouseDocument, room_id: str) -> str:
    for floor in house.floors:
        if any(r.id == room_id for r in floor.rooms):
            return floor.id
    return house.floors[0].id


def _jittered_position(room: Room, rng: random.Random) -> Position:
    cx, cy = room_centroid(room)
    return Position(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8))


def generate_demo_chores(house: HouseDocument, rng: random.Random) -> ChoreDocument:
    now = datetime.now(timezone.utc)
    chores: list[Chore] = []
    assignments: list[Assignment] = []
    completions: list[CompletionRecord] = []

    shuffled = CHORES[:]
    rng.shuffle(shuffled)
    overdue_count = round(len(shuffled) * 0.2)
    due_soon_count = round(len(shuffled) * 0.3)

    for i, (name, emoji, period_days, room_hint) in enumerate(shuffled):
        jitter = rng.uniform(0.8, 1.2)
        period = round(period_days * jitter, 1)

        if i < overdue_count:
            due = now - timedelta(days=rng.randint(1, 30))
        elif i < overdue_count + due_soon_count:
            due = now + timedelta(days=rng.randint(0, 7))
        else:
            due = now + timedelta(days=rng.randint(8, max(9, int(period))))

        chore = Chore(
            id=str(uuid.uuid4()),
            name=name,
            emoji=emoji,
            periodDays=period,
            frequency=max(1, round(period)),
            frequencyMetadata={"unit": "days"},
            nextDueDate=due.isoformat(),
        )
        chores.append(chore)

        for _ in range(rng.randint(0, 4)):
            completed_at = now - timedelta(days=rng.randint(1, 90))
            scheduled_due = completed_at - timedelta(days=rng.randint(0, 5))
            completions.append(CompletionRecord(
                id=str(uuid.uuid4()), choreId=chore.id,
                completedAt=completed_at.isoformat(),
                scheduledDue=scheduled_due.isoformat(),
            ))

        if i < 20:
            room = _find_room(house, room_hint)
            assignments.append(Assignment(
                id=str(uuid.uuid4()), choreId=chore.id, roomId=room.id,
                position=_jittered_position(room, rng), nextDueDate=due.isoformat(),
            ))

    return ChoreDocument(chores=chores, assignments=assignments, completions=completions)
