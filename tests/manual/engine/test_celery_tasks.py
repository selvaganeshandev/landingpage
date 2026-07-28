#!/usr/bin/env python
"""Test script to verify Celery tasks are registered"""
import os
import sys
import django
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[3] / 'engine'
sys.path.insert(0, str(ENGINE_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from celery import current_app
from llm_monitor_engine.celery import app

print("=" * 60)
print("Checking Celery Task Registration")
print("=" * 60)

# Get all registered tasks
all_tasks = list(current_app.tasks.keys())
print(f"\nTotal registered tasks: {len(all_tasks)}")

# Filter integration-related tasks
integration_tasks = [
    t for t in all_tasks 
    if 'integration' in t.lower() or 'ga_insight' in t.lower() or 'gsc_insight' in t.lower()
]

print(f"\nIntegration-related tasks: {len(integration_tasks)}")
if integration_tasks:
    print("\nIntegration tasks found:")
    for task in sorted(integration_tasks):
        print(f"  ✓ {task}")
else:
    print("\n❌ No integration tasks found!")
    print("\nTrying to import tasks explicitly...")
    try:
        import core.processing_tasks
        print("✓ core.processing_tasks imported successfully")
        
        # Check again
        all_tasks_after = list(current_app.tasks.keys())
        integration_tasks_after = [
            t for t in all_tasks_after 
            if 'integration' in t.lower() or 'ga_insight' in t.lower() or 'gsc_insight' in t.lower()
        ]
        print(f"\nAfter import - Integration tasks: {len(integration_tasks_after)}")
        if integration_tasks_after:
            for task in sorted(integration_tasks_after):
                print(f"  ✓ {task}")
    except Exception as e:
        print(f"❌ Error importing: {e}")

# Check specific task names
expected_tasks = [
    'core.processing_tasks.process_ga_insight_task',
    'core.processing_tasks.process_gsc_insight_task',
    'core.processing_tasks.process_integration_insights_scheduler',
]

print("\n" + "=" * 60)
print("Checking for expected task names:")
print("=" * 60)
for task_name in expected_tasks:
    if task_name in all_tasks:
        print(f"  ✓ {task_name}")
    else:
        print(f"  ❌ {task_name} - NOT FOUND")

print("\n" + "=" * 60)

