#!/usr/bin/env python
"""
Celery Configuration Verification Script for LLM Monitor Engine

This script verifies that Celery is properly configured and tasks are registered.
Run this before starting Celery workers/beat to ensure everything is set up correctly.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from celery import current_app
from django.conf import settings
from django.db import connection

def check_redis_connection():
    """Check if Redis is accessible"""
    try:
        import redis
        broker_url = settings.CELERY_BROKER_URL
        # Parse Redis URL
        if broker_url.startswith('redis://'):
            parts = broker_url.replace('redis://', '').split('/')
            host_port = parts[0].split(':')
            host = host_port[0] if host_port[0] else 'localhost'
            port = int(host_port[1]) if len(host_port) > 1 and host_port[1] else 6379
            db = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        else:
            host, port, db = 'localhost', 6379, 0
        
        r = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=2)
        r.ping()
        return True, f"Redis connection OK (host={host}, port={port}, db={db})"
    except Exception as e:
        return False, f"Redis connection failed: {str(e)}"

def check_database_connection():
    """Check if database is accessible"""
    try:
        connection.ensure_connection()
        return True, "Database connection OK"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"

def check_celery_config():
    """Check Celery configuration"""
    config = {
        'broker_url': settings.CELERY_BROKER_URL,
        'result_backend': settings.CELERY_RESULT_BACKEND,
        'timezone': settings.CELERY_TIMEZONE,
        'beat_schedule_count': len(settings.CELERY_BEAT_SCHEDULE),
    }
    return config

def check_tasks():
    """Check if required tasks are registered"""
    required_tasks = [
        'core.processing_tasks.process_integration_insights_scheduler',
        'core.processing_tasks.process_ga_insight_task',
        'core.processing_tasks.process_gsc_insight_task',
    ]
    
    registered = []
    missing = []
    
    for task_name in required_tasks:
        if task_name in current_app.tasks:
            registered.append(task_name)
        else:
            missing.append(task_name)
    
    return registered, missing

def check_beat_schedule():
    """Check Celery Beat schedule"""
    schedule = {}
    for name, config in settings.CELERY_BEAT_SCHEDULE.items():
        schedule[name] = {
            'task': config['task'],
            'schedule': str(config['schedule']),
        }
    return schedule

def main():
    print("=" * 60)
    print("Celery Configuration Verification")
    print("=" * 60)
    print()
    
    # Check Redis
    print("[1/5] Checking Redis connection...")
    redis_ok, redis_msg = check_redis_connection()
    if redis_ok:
        print(f"  ✓ {redis_msg}")
    else:
        print(f"  ✗ {redis_msg}")
    print()
    
    # Check Database
    print("[2/5] Checking database connection...")
    db_ok, db_msg = check_database_connection()
    if db_ok:
        print(f"  ✓ {db_msg}")
    else:
        print(f"  ✗ {db_msg}")
    print()
    
    # Check Celery Config
    print("[3/5] Checking Celery configuration...")
    config = check_celery_config()
    print(f"  Broker URL: {config['broker_url']}")
    print(f"  Result Backend: {config['result_backend']}")
    print(f"  Timezone: {config['timezone']}")
    print(f"  Beat Schedule Entries: {config['beat_schedule_count']}")
    print()
    
    # Check Tasks
    print("[4/5] Checking task registration...")
    registered, missing = check_tasks()
    if registered:
        print(f"  ✓ {len(registered)} required tasks registered:")
        for task in registered:
            print(f"    - {task}")
    if missing:
        print(f"  ✗ {len(missing)} required tasks missing:")
        for task in missing:
            print(f"    - {task}")
    print()
    
    # Check Beat Schedule
    print("[5/5] Checking Celery Beat schedule...")
    schedule = check_beat_schedule()
    for name, config in schedule.items():
        print(f"  {name}:")
        print(f"    Task: {config['task']}")
        print(f"    Schedule: {config['schedule']}")
    print()
    
    # Summary
    print("=" * 60)
    if redis_ok and db_ok and not missing:
        print("✓ All checks passed! Celery is ready to start.")
        print()
        print("To start Celery:")
        print("  1. Worker: python -m celery -A llm_monitor_engine worker --loglevel=info")
        print("  2. Beat:   python -m celery -A llm_monitor_engine beat --loglevel=info")
        print("  Or use: ./start-celery.sh")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
    print("=" * 60)

if __name__ == '__main__':
    main()

