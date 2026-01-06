#!/usr/bin/env python3
"""
Database management script for deployment.
Run this during the build/deployment pipeline to handle migrations.
"""
import os
import sys

# Add current directory to path so we can import orchestrator
sys.path.append(os.getcwd())

from orchestrator.app import create_app
from orchestrator.models import db
from flask_migrate import upgrade

def deploy():
    """Run deployment tasks."""
    print("Starting database migration...")
    app = create_app()
    with app.app_context():
        # Run Alembic upgrade to apply migrations
        try:
            upgrade()
            print("✓ Database migrations applied.")
        except Exception as e:
            print(f"Error applying migrations: {e}")
            sys.exit(1)

if __name__ == '__main__':
    deploy()
