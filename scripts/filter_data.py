#!/usr/bin/env python3
"""
Filter large OpenAgenda events JSON file to keep only:
- Events in Savoie (73), Haute-Savoie (74), or Isère (38)
- Events starting from 2023-01-01 onwards

Uses streaming JSON parsing (ijson) to handle large files efficiently.

DEPRECATION NOTE (v0.4.1+):
    This script is now largely obsolete for production use. The RAG service
    (src/api/rag_service.py) downloads pre-filtered data directly from the
    OpenDataSoft API using the 'where' parameter, which:
    - Reduces download size from 4GB to ~72MB (98% reduction)
    - Reduces download time from 5+ minutes to ~11 seconds
    - Filters by department at the API level

    This script remains useful for:
    - Manual data exploration
    - Processing locally downloaded full datasets
    - Testing/development scenarios

    For production deployments, use the auto-rebuild feature which handles
    filtering automatically.
"""

import json
import ijson
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tqdm import tqdm


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts Decimal to float."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# Configuration
RAW_DATA_PATH = Path("data/raw/evenements-publics-openagenda.json")
OUTPUT_PATH = Path("data/processed/events_filtered.json")
TARGET_DEPARTMENTS = {"Savoie", "Haute-Savoie", "Isère"}
MIN_DATE = datetime(2023, 1, 1)


def parse_date(date_str):
    """Parse ISO datetime string to datetime object (timezone-naive)."""
    if not date_str:
        return None
    try:
        # Handle ISO format like "2023-01-15T10:00:00+01:00"
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Convert to timezone-naive for comparison
        return dt.replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def filter_event(event):
    """
    Check if event matches our filtering criteria.

    Returns:
        bool: True if event should be kept, False otherwise
    """
    # Check department
    department = event.get("location_department", "")
    if department not in TARGET_DEPARTMENTS:
        return False

    # Check date
    firstdate = event.get("firstdate_begin")
    if not firstdate:
        return False

    event_date = parse_date(firstdate)
    if not event_date or event_date < MIN_DATE:
        return False

    return True


def filter_large_json():
    """
    Stream-parse large JSON file and filter events.
    Writes filtered events to output file.
    """
    print(f"Reading from: {RAW_DATA_PATH}")
    print(f"Writing to: {OUTPUT_PATH}")
    print(f"Target departments: {', '.join(TARGET_DEPARTMENTS)}")
    print(f"Minimum date: {MIN_DATE.strftime('%Y-%m-%d')}")
    print("\nProcessing...\n")

    filtered_events = []
    total_processed = 0

    # Open input file for streaming
    with open(RAW_DATA_PATH, 'rb') as f:
        # Parse JSON array items one by one
        parser = ijson.items(f, 'item')

        # Process with progress bar
        for event in tqdm(parser, desc="Filtering events", unit=" events"):
            total_processed += 1

            if filter_event(event):
                filtered_events.append(event)

    # Write filtered events to output file
    print(f"\n\nWriting {len(filtered_events)} filtered events to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(filtered_events, f, ensure_ascii=False, indent=2, cls=DecimalEncoder)

    # Print statistics
    print("\n" + "="*60)
    print("FILTERING COMPLETE")
    print("="*60)
    print(f"Total events processed: {total_processed:,}")
    print(f"Events kept: {len(filtered_events):,}")
    print(f"Events filtered out: {total_processed - len(filtered_events):,}")
    print(f"Retention rate: {len(filtered_events)/total_processed*100:.2f}%")

    # Department breakdown
    dept_counts = {}
    for event in filtered_events:
        dept = event.get("location_department", "Unknown")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    print("\nDepartment breakdown:")
    for dept, count in sorted(dept_counts.items()):
        print(f"  {dept}: {count:,} events")

    # Date range
    dates = []
    for event in filtered_events:
        date_str = event.get("firstdate_begin")
        if date_str:
            date_obj = parse_date(date_str)
            if date_obj:
                dates.append(date_obj)

    if dates:
        print(f"\nDate range:")
        print(f"  Earliest event: {min(dates).strftime('%Y-%m-%d')}")
        print(f"  Latest event: {max(dates).strftime('%Y-%m-%d')}")

    print(f"\nOutput file size: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    print("="*60)


if __name__ == "__main__":
    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Run filtering
    filter_large_json()
