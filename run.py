#!/usr/bin/env python3
"""
Entry point for the Tournament Platform Orchestrator.

Usage:
    python run.py                    # Run orchestrator (default)
    python run.py orchestrator       # Run orchestrator explicitly
    python run.py tournament         # Run a tournament service instance

Environment Variables:
    FLASK_ENV: development or production (default: development)
    PORT: Port to run on (default: 5000 for orchestrator)
    TOURNAMENT_ID: Required for tournament service mode
    TOURNAMENT_TYPE: single_elimination or round_robin (default: single_elimination)
"""
import os
import sys


def run_orchestrator():
    """Run the orchestrator/gateway service."""
    from orchestrator.app import create_app
    
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"Starting Orchestrator on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)


def run_tournament_service():
    """Run a tournament service instance."""
    # Add project root to path for imports
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    from tournament_service.app import app
    
    port = int(os.getenv('PORT', 6001))
    tournament_id = os.getenv('TOURNAMENT_ID', 'default')
    
    print(f"Starting Tournament Service for {tournament_id} on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'orchestrator'
    
    if mode == 'orchestrator':
        run_orchestrator()
    elif mode == 'tournament':
        run_tournament_service()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python run.py [orchestrator|tournament]")
        sys.exit(1)
