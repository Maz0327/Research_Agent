"""Factory for creating JobStore instances."""
from functools import lru_cache

from loguru import logger

from backend.config import get_settings
from backend.state.impl.in_memory import InMemoryJobStore
from backend.state.impl.supabase_store import SupabaseJobStore
from backend.state.interface import JobStore


@lru_cache()
def get_job_store() -> JobStore:
    """
    Get the appropriate JobStore implementation based on environment.
    
    Returns SupabaseJobStore if Supabase env vars are set,
    otherwise returns InMemoryJobStore for local development.
    """
    settings = get_settings()
    
    if settings.supabase_url and settings.supabase_service_role_key:
        logger.info("Using SupabaseJobStore")
        return SupabaseJobStore()
    else:
        logger.info("Using InMemoryJobStore (Supabase not configured)")
        return InMemoryJobStore()

