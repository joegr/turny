#!/usr/bin/env python3
"""
Entry point for the Tournament Platform (Monolith).

Usage:
    python run.py                    # Run application
"""
import os
import sys


def run_app():
    """Run the monolithic application."""
    from orchestrator.app import create_app
    
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"Starting Tournament Platform on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    run_app()
