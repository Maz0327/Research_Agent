#!/usr/bin/env python3
"""
Migration runner for Supabase database.
Executes SQL migrations in order.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client
from config import settings

def get_supabase_client() -> Client:
    """Create Supabase client."""
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )

def run_migrations():
    """Run all SQL migrations in order."""
    migrations_dir = Path(__file__).parent
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found.")
        return

    print(f"Found {len(migration_files)} migration files.")

    # Get Supabase client
    get_supabase_client()

    # Note: Supabase Python client doesn't support raw SQL execution
    # We need to run these manually via Supabase Dashboard SQL Editor
    # or use psycopg2 to connect directly to PostgreSQL

    print("\n" + "="*80)
    print("IMPORTANT: These migrations must be run manually in Supabase SQL Editor")
    print("="*80)
    print("\nGo to: https://supabase.com/dashboard/project/your-supabase-project-ref/sql/new")
    print("\nRun these files in order:\n")

    for migration_file in migration_files:
        print(f"\n{'='*80}")
        print(f"Migration: {migration_file.name}")
        print(f"{'='*80}")
        print(migration_file.read_text())
        print()

    print("\n" + "="*80)
    print("After running migrations, press Enter to continue...")
    print("="*80)
    input()

if __name__ == "__main__":
    run_migrations()
