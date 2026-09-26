"""
Automated Pipeline Scheduler for TraceImpact 2.0.
Executes scheduled background ingestion runs with configurable intervals,
one-shot execution mode for testing, and graceful shutdown handling.
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Optional
from src.config import (
    PIPELINE_SCHEDULE_INTERVAL_HOURS,
    PIPELINE_RUN_ON_STARTUP,
    PIPELINE_LOOKBACK_YEARS,
)
from src.ingestion.world_bank import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s")
logger = logging.getLogger("Scheduler")


class PipelineScheduler:
    """
    Automated background scheduler for TraceImpact public data ingestion.
    Supports configurable interval loops, run-on-startup flags, signal handling,
    and single-pass execution mode for testing and CI/CD pipelines.
    """

    def __init__(
        self,
        interval_hours: float = PIPELINE_SCHEDULE_INTERVAL_HOURS,
        lookback_years: int = PIPELINE_LOOKBACK_YEARS,
        run_on_startup: bool = PIPELINE_RUN_ON_STARTUP,
    ):
        self.interval_seconds = max(interval_hours * 3600.0, 1.0)
        self.lookback_years = lookback_years
        self.run_on_startup = run_on_startup
        self._running = False
        self._setup_signals()

    def _setup_signals(self) -> None:
        """Configures clean POSIX signal handlers for graceful shutdown."""
        try:
            signal.signal(signal.SIGINT, self._handle_exit)
            signal.signal(signal.SIGTERM, self._handle_exit)
        except (ValueError, AttributeError):
            # Not supported in non-main threads or some environments
            pass

    def _handle_exit(self, signum, frame) -> None:
        logger.info("Received termination signal (%d). Shutting down scheduler gracefully...", signum)
        self._running = False

    def get_year_range(self) -> tuple[int, int]:
        """Calculates dynamic start and end years based on lookback setting."""
        current_year = datetime.now().year
        # World Bank data usually has 1-year reporting lag, so end_year is current_year - 1
        end_year = max(current_year - 1, 2021)
        start_year = end_year - self.lookback_years + 1
        return start_year, end_year

    def execute_scheduled_run(self, max_pages: Optional[int] = None) -> dict:
        """Executes a single scheduled ingestion run."""
        start_year, end_year = self.get_year_range()
        logger.info(
            "Executing automated ingestion run (horizon: %d-%d, lookback: %d years)...",
            start_year, end_year, self.lookback_years
        )
        try:
            res = run_pipeline(
                start_year=start_year,
                end_year=end_year,
                max_pages=max_pages,
                run_type="SCHEDULED",
            )
            logger.info("Scheduled ingestion run completed successfully: %s", res)
            return res
        except Exception as e:
            logger.error("Scheduled ingestion run failed: %s", e)
            return {"error": str(e)}

    def run_forever(self, poll_interval_seconds: float = 5.0) -> None:
        """
        Runs the continuous scheduling loop until interrupted.
        """
        self._running = True
        logger.info(
            "TraceImpact 2.0 Automated Scheduler started. Interval: %.2f hours (%.0fs).",
            self.interval_seconds / 3600.0, self.interval_seconds
        )

        if self.run_on_startup:
            logger.info("run_on_startup=True: executing immediate initial ingestion...")
            self.execute_scheduled_run()

        next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
        logger.info("Next scheduled run at: %s", next_run.strftime("%Y-%m-%d %H:%M:%S"))

        while self._running:
            now = datetime.now()
            if now >= next_run:
                self.execute_scheduled_run()
                next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
                logger.info("Next scheduled run at: %s", next_run.strftime("%Y-%m-%d %H:%M:%S"))

            time.sleep(poll_interval_seconds)

        logger.info("Scheduler loop terminated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TraceImpact 2.0 Automated Pipeline Scheduler")
    parser.add_argument(
        "--once", action="store_true", help="Execute exactly one scheduled run and exit immediately (safe test mode)"
    )
    parser.add_argument(
        "--interval-hours", type=float, default=PIPELINE_SCHEDULE_INTERVAL_HOURS,
        help="Scheduled interval in hours between runs (default: from PIPELINE_SCHEDULE_INTERVAL_HOURS or 24.0)"
    )
    parser.add_argument(
        "--lookback-years", type=int, default=PIPELINE_LOOKBACK_YEARS,
        help="Number of historical years to ingest (default: 3)"
    )
    parser.add_argument(
        "--max-pages", type=int, default=None, help="Maximum pages per indicator for quick testing"
    )
    args = parser.parse_args()

    scheduler = PipelineScheduler(
        interval_hours=args.interval_hours,
        lookback_years=args.lookback_years,
        run_on_startup=True,
    )

    if args.once:
        logger.info("Running in single-pass mode (--once)...")
        scheduler.execute_scheduled_run(max_pages=args.max_pages)
    else:
        scheduler.run_forever()
