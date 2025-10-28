#!/usr/bin/env python
"""
Startup script for the LLM Monitor Engine
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
    django.setup()
    
    # Start the domain processor
    from core.domain_processor import DomainProcessor
    
    print("Starting LLM Monitor Engine...")
    print("Domain Processing Engine initialized")
    print("API endpoints available at: http://localhost:8001/api/")
    print("Press Ctrl+C to stop")
    
    processor = DomainProcessor()
    
    try:
        processor.start_processing_loop()
    except KeyboardInterrupt:
        print("\nShutting down LLM Monitor Engine...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
