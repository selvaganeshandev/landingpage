#!/usr/bin/env python3
import os
import sys
import django

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from prompts.models import PromptAnalytics, PromptGroup

print('PromptAnalytics records:')
for pa in PromptAnalytics.objects.all():
    print(f'  ID: {pa.id}, Platform: {pa.platform}, Is Mention: {pa.is_mention}, Is Published: {pa.is_published}, Track Status: {pa.track_status}')

print('\nPromptGroup records:')
for pg in PromptGroup.objects.all():
    print(f'  ID: {pg.id}, Track Status: {pg.track_status}, Is Published: {pg.is_published}')

print('\nMentions count:', PromptAnalytics.objects.filter(is_mention=True).count())
print('Published mentions count:', PromptAnalytics.objects.filter(is_mention=True, is_published=True).count())
