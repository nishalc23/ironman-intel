"""
Imports your full Hevy workout history from a CSV export.

Usage:
    make import-hevy CSV=/Users/you/Downloads/workouts.csv

Hevy exports one row per set. This script groups them into workouts,
converts lbs → kg, and writes everything to the gym_workouts table.
Re-running is safe — duplicates are skipped.
"""
import csv
import sys
import os
from datetime import datetime
from collections import defaultdict, OrderedDict

sys.path.insert(0, "/app")

from dotenv import load_dotenv
load_dotenv()

from db.database import create_tables, get_db
from db.models import Athlete, GymWorkout

LBS_TO_KG = 0.453592


def parse_hevy_time(s: str) -> datetime:
    # Format: "May 18, 2026, 6:06 PM"
    return datetime.strptime(s.strip(), "%B %d, %Y, %I:%M %p")


def parse_set(row: dict) -> dict:
    s = {}
    s["set_type"] = row.get("set_type", "normal") or "normal"

    reps = row.get("reps", "").strip()
    if reps:
        s["reps"] = int(reps)

    weight = row.get("weight_lbs", "").strip()
    if weight:
        s["weight_kg"] = round(float(weight) * LBS_TO_KG, 1)

    duration = row.get("duration_seconds", "").strip()
    if duration:
        s["duration_seconds"] = int(duration)

    distance = row.get("distance_miles", "").strip()
    if distance:
        s["distance_km"] = round(float(distance) * 1.60934, 2)

    rpe = row.get("rpe", "").strip()
    if rpe:
        s["rpe"] = float(rpe)

    return s


def group_into_workouts(rows: list[dict]) -> list[dict]:
    # Use OrderedDict to preserve CSV order (most recent first in Hevy exports)
    groups: dict[tuple, list] = OrderedDict()

    for row in rows:
        key = (row["title"], row["start_time"])
        if key not in groups:
            groups[key] = []
        groups[key].append(row)

    workouts = []
    for (title, start_str), sets in groups.items():
        start = parse_hevy_time(start_str)

        end_str = sets[0].get("end_time", "").strip()
        end = parse_hevy_time(end_str) if end_str else None
        duration_min = int((end - start).total_seconds() / 60) if end else None

        description = sets[0].get("description", "").strip()

        # Group sets by exercise, preserving order of first appearance
        exercise_sets: dict[str, list] = OrderedDict()
        for row in sets:
            ex_name = row["exercise_title"].strip()
            if ex_name not in exercise_sets:
                exercise_sets[ex_name] = []
            exercise_sets[ex_name].append(row)

        exercises = []
        for ex_name, ex_rows in exercise_sets.items():
            sorted_rows = sorted(ex_rows, key=lambda r: int(r.get("set_index", 0) or 0))
            parsed_sets = [parse_set(r) for r in sorted_rows]
            exercises.append({"name": ex_name, "sets": parsed_sets})

        workouts.append({
            "title": title,
            "start": start,
            "duration_minutes": duration_min,
            "notes": description or title,
            "exercises": exercises,
            "hevy_id": f"hevy::{title}::{start.isoformat()}",
        })

    return workouts


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_hevy_csv.py /path/to/workouts.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"Reading {csv_path}...")

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"  {len(rows)} set rows found")
    workouts = group_into_workouts(rows)
    print(f"  {len(workouts)} unique workout sessions")

    create_tables()

    imported = 0
    skipped = 0

    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            print("\nNo athlete in DB yet. Run 'make sync' first to initialize, then retry.")
            sys.exit(1)

        for w in workouts:
            existing = db.query(GymWorkout).filter_by(hevy_workout_id=w["hevy_id"]).first()
            if existing:
                skipped += 1
                continue

            db.add(GymWorkout(
                athlete_id=athlete.id,
                hevy_workout_id=w["hevy_id"],
                date=w["start"].date(),
                duration_minutes=w["duration_minutes"],
                notes=w["notes"],
                exercises=w["exercises"],
            ))
            imported += 1

    print(f"\nDone — {imported} imported, {skipped} already existed")
    if imported:
        print("Your Hevy history is now in the dashboard and Claude will see it in your training plan.")


if __name__ == "__main__":
    main()
