"""
Resilient HTTP Client with Retries, Exponential Backoff, and Metadata Tracking.
Designed for robust external public API ingestion.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class APIClient:
    """
    Robust HTTP client for public REST APIs.
    Supports timeouts, exponential backoff, user-agent configuration, and raw payload hashing.
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        user_agent: str = "TraceImpact-DataPipeline/2.0",
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json",
        })

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, bytes, Dict[str, Any], str]:
        """
        Executes a GET request with automatic retry and exponential backoff.
        
        Returns:
            Tuple of:
            - status_code (int)
            - raw_bytes (bytes)
            - parsed_json (dict or list)
            - sha256_hash (str)
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if self.base_url else endpoint
        params = params or {}

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("HTTP GET %s (attempt %d/%d, params=%s)", url, attempt, self.max_retries, params)
                resp = self.session.get(url, params=params, timeout=self.timeout)

                # Check for HTTP 429 (rate limiting) or 5xx (server errors)
                if resp.status_code in (429, 500, 502, 503, 504):
                    logger.warning("HTTP %d received from %s. Backing off...", resp.status_code, url)
                    time.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                    continue

                raw_bytes = resp.content
                resp_hash = hashlib.sha256(raw_bytes).hexdigest()

                try:
                    parsed_json = resp.json()
                except Exception as json_err:
                    logger.error("Failed to parse JSON response from %s: %s", url, json_err)
                    parsed_json = {}

                return resp.status_code, raw_bytes, parsed_json, resp_hash

            except (requests.exceptions.RequestException, Exception) as e:
                last_exception = e
                wait_time = self.backoff_factor * (2 ** (attempt - 1))
                logger.warning("Request to %s failed (%s). Retrying in %.2f seconds...", url, e, wait_time)
                time.sleep(wait_time)

        error_msg = f"Failed to fetch {url} after {self.max_retries} attempts: {last_exception}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
