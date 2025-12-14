"""CLI script to run research job pipeline synchronously for local debugging."""
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from backend.state import create_job
from backend.worker import run_research_job


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run research job pipeline synchronously for local debugging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m backend.scripts.run_job "Research Candace Owens claims about Charlie Kirk"

  # With channel
  python -m backend.scripts.run_job "Check @candaceowens latest livestreams about Charlie Kirk since September"

  # Full example
  python -m backend.scripts.run_job "Research topic about X, check @channelname videos from last month"
        """,
    )
    parser.add_argument(
        "slack_text",
        type=str,
        help="Research topic text (as would be sent from Slack)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    
    slack_text = args.slack_text.strip()
    if not slack_text:
        parser.error("slack_text cannot be empty")
    
    print(f"\n🚀 Starting research job pipeline...")
    print(f"📝 Topic: {slack_text}\n")
    
    try:
        # Create job
        job = create_job(topic=slack_text)
        job_id = job.job_id
        print(f"✅ Created job: {job_id}\n")
        
        # Run pipeline synchronously (no Celery)
        print("=" * 60)
        print("Running pipeline stages...")
        print("=" * 60)
        print()
        
        result = run_research_job(job_id, slack_text, slack_payload=None)
        
        print()
        print("=" * 60)
        print("Pipeline completed!")
        print("=" * 60)
        print()
        
        if result.get("status") == "completed":
            folder_url = result.get("folder_url")
            if folder_url:
                print(f"✅ Job completed successfully!")
                print(f"📁 Drive folder: {folder_url}")
                print(f"📊 Claims extracted: {result.get('claims_count', 0)}")
                print(f"📚 Sources: {result.get('sources_count', 0)} web, {result.get('youtube_videos_count', 0)} YouTube videos")
                
                if result.get("warnings_count", 0) > 0:
                    print(f"⚠️  Warnings: {result.get('warnings_count')} (check job details)")
            else:
                print(f"⚠️  Job completed but Drive upload failed")
                print(f"   Check job details for results")
        else:
            print(f"❌ Job failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
        print()
        print(f"Job ID: {job_id}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

