#!/usr/bin/env python3
import os
import sys
import django

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from shared_models.models import PromptAnalytics, PromptGroup

print('PromptAnalytics is_published status:')
for pa in PromptAnalytics.objects.all()[:5]:
    print(f'  ID: {pa.id}, Platform: {pa.platform}, Track Status: {pa.track_status}, Is Published: {pa.is_published}')

print('\nPromptGroup is_published status:')
for pg in PromptGroup.objects.all()[:5]:
    print(f'  ID: {pg.id}, Track Status: {pg.track_status}, Is Published: {pg.is_published}')

print('\nCompleted analytics count:', PromptAnalytics.objects.filter(track_status='COMP', is_published=True).count())
print('Completed groups count:', PromptGroup.objects.filter(track_status='COMP', is_published=True).count())
