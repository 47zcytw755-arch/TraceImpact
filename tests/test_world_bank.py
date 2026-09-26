"""
Test Suite for TraceImpact 2.0 World Bank Public Data Ingestion Pipeline.
Covers API client, pagination, response validation, bronze storage, silver loading,
idempotency, lineage, and analytical views without requiring live internet.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import text
from src.database.connection import engine
from src.ingestion.api_client import APIClient
from src.ingestion.world_bank import WorldBankIngester, CURATED_INDICATORS
from src.quality.world_bank_quality import WorldBankValidator, WorldBankDQIssue
from src.dashboard.queries import (
    get_world_bank_kpis,
    get_world_bank_indicators_list,
    get_world_bank_countries_list,
    get_world_bank_trend_data,
    get_world_bank_indicator_summary_df,
    get_world_bank_latest_table,
    get_world_bank_lineage,
)


@pytest.fixture
def mock_api_page_1():
    """Mocked first page response from World Bank API."""
    return [
        {
            "page": 1,
            "pages": 2,
            "per_page": 2,
            "total": 4,
            "sourceid": "2",
            "lastupdated": "2026-07-13",
        },
        [
            {
                "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita (current US$)"},
                "country": {"id": "IN", "value": "India"},
                "countryiso3code": "IND",
                "date": "2021",
                "value": 2239.61,
                "unit": "",
                "obs_status": "",
                "decimal": 1,
            },
            {
                "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita (current US$)"},
                "country": {"id": "US", "value": "United States"},
                "countryiso3code": "USA",
                "date": "2021",
                "value": 70248.63,
                "unit": "",
                "obs_status": "",
                "decimal": 1,
            },
        ],
    ]


@pytest.fixture
def mock_api_page_2():
    """Mocked second page response from World Bank API."""
    return [
        {
            "page": 2,
            "pages": 2,
            "per_page": 2,
            "total": 4,
            "sourceid": "2",
            "lastupdated": "2026-07-13",
        },
        [
            {
                "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita (current US$)"},
                "country": {"id": "IN", "value": "India"},
                "countryiso3code": "IND",
                "date": "2020",
                "value": 1933.10,
                "unit": "",
                "obs_status": "",
                "decimal": 1,
            },
            {
                "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita (current US$)"},
                "country": {"id": "US", "value": "United States"},
                "countryiso3code": "USA",
                "date": "2020",
                "value": 63528.58,
                "unit": "",
                "obs_status": "",
                "decimal": 1,
            },
        ],
    ]


# -----------------------------------------------------------------------------
# 1. API Client & Resiliency Tests
# -----------------------------------------------------------------------------

def test_api_client_initialization():
    client = APIClient(base_url="http://api.worldbank.org/v2", timeout=15)
    assert client.base_url == "http://api.worldbank.org/v2"
    assert client.timeout == 15
    assert "User-Agent" in client.session.headers


def test_api_client_successful_get(mock_api_page_1):
    client = APIClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = json.dumps(mock_api_page_1).encode("utf-8")
    mock_resp.json.return_value = mock_api_page_1

    with patch.object(client.session, "get", return_value=mock_resp):
        status, raw_bytes, parsed, sha = client.get("http://example.com/test")
        assert status == 200
        assert len(sha) == 64
        assert parsed[0]["page"] == 1
        assert len(parsed[1]) == 2


def test_api_client_retry_and_timeout():
    client = APIClient(max_retries=2, backoff_factor=0.01)
    with patch.object(client.session, "get", side_effect=Exception("Connection refused")):
        with pytest.raises(RuntimeError):
            client.get("http://example.com/timeout")


# -----------------------------------------------------------------------------
# 2. Validation & Data Quality Tests
# -----------------------------------------------------------------------------

def test_validator_valid_observation():
    valid_raw = {
        "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
        "country": {"id": "IN", "value": "India"},
        "countryiso3code": "IND",
        "date": "2021",
        "value": 2239.61,
    }
    is_valid, issues, cleaned = WorldBankValidator.validate_observation(valid_raw)
    assert is_valid is True
    assert len(issues) == 0
    assert cleaned["country_code"] == "IN"
    assert cleaned["indicator_value"] == 2239.61
    assert cleaned["year"] == 2021


def test_validator_missing_value_non_blocking():
    null_raw = {
        "indicator": {"id": "SP.POP.TOTL", "value": "Population"},
        "country": {"id": "IN", "value": "India"},
        "countryiso3code": "IND",
        "date": "2021",
        "value": None,
    }
    is_valid, issues, cleaned = WorldBankValidator.validate_observation(null_raw)
    assert is_valid is False  # Cannot insert null value observation into facts
    assert len(issues) == 1
    assert issues[0].issue_type == "MISSING_VALUE"
    assert issues[0].severity == "INFO"


def test_validator_invalid_numeric_quarantine():
    bad_num_raw = {
        "indicator": {"id": "SP.POP.TOTL", "value": "Population"},
        "country": {"id": "IN", "value": "India"},
        "countryiso3code": "IND",
        "date": "2021",
        "value": "NOT_A_NUMBER",
    }
    is_valid, issues, cleaned = WorldBankValidator.validate_observation(bad_num_raw)
    assert is_valid is False
    assert any(i.severity == "ERROR" and i.issue_type == "INVALID_NUMERIC" for i in issues)


def test_validator_missing_country_and_indicator():
    bad_rec = {"date": "2021", "value": 100.0}
    is_valid, issues, cleaned = WorldBankValidator.validate_observation(bad_rec)
    assert is_valid is False
    types = [i.issue_type for i in issues]
    assert "MISSING_COUNTRY" in types
    assert "MISSING_INDICATOR" in types


# -----------------------------------------------------------------------------
# 3. Ingestion Pipeline & Pagination Mock Tests
# -----------------------------------------------------------------------------

def test_ingestion_pipeline_with_mocked_pagination(mock_api_page_1, mock_api_page_2):
    ingester = WorldBankIngester(per_page=2)
    ingester.seed_indicators()

    def mock_get(endpoint, params=None):
        page = params.get("page", 1)
        data = mock_api_page_1 if page == 1 else mock_api_page_2
        raw_b = json.dumps(data).encode("utf-8")
        import hashlib
        h = hashlib.sha256(raw_b).hexdigest()
        return 200, raw_b, data, h

    with patch.object(ingester.api_client, "get", side_effect=mock_get):
        result = ingester.ingest_indicator("NY.GDP.PCAP.CD", start_year=2020, end_year=2021)
        assert result["status"] == "COMPLETED"
        assert result["pages"] == 2
        assert result["total_records"] == 4
        assert (result["inserted"] + result["updated"]) == 4


# -----------------------------------------------------------------------------
# 4. Idempotency & Database Verification Tests
# -----------------------------------------------------------------------------

def test_world_bank_database_tables_exist():
    with engine.connect() as conn:
        tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'api_ingestion_runs',
                'api_raw_responses',
                'world_bank_countries',
                'world_bank_indicators',
                'world_bank_observations',
                'world_bank_data_quality_issues'
            );
        """)).scalars().all()
        assert len(tables) == 6


def test_world_bank_analytical_views_exist():
    with engine.connect() as conn:
        views = conn.execute(text("""
            SELECT table_name FROM information_schema.views 
            WHERE table_schema = 'public'
            AND table_name LIKE 'v_world_bank_%';
        """)).scalars().all()
        expected = {
            "v_world_bank_latest_indicators",
            "v_world_bank_country_trends",
            "v_world_bank_indicator_summary",
            "v_world_bank_regional_comparison",
            "v_world_bank_data_quality_summary",
        }
        assert expected.issubset(set(views))


def test_world_bank_kpis_and_query_layer():
    kpis = get_world_bank_kpis()
    assert kpis["total_countries"] > 0
    assert kpis["total_indicators"] >= 4
    assert kpis["total_observations"] > 0
    assert kpis["total_pages_ingested"] > 0

    indicators = get_world_bank_indicators_list()
    assert len(indicators) >= 4
    codes = [i["indicator_code"] for i in indicators]
    assert "NY.GDP.PCAP.CD" in codes

    countries = get_world_bank_countries_list()
    assert len(countries) > 0


def test_world_bank_lineage_retrieval():
    # Verify India GDP per capita lineage
    lineage = get_world_bank_lineage(country_code="IN", indicator_code="NY.GDP.PCAP.CD", year=2021)
    assert lineage is not None
    assert lineage["country_name"] == "India"
    assert lineage["indicator_code"] == "NY.GDP.PCAP.CD"
    assert lineage["year"] == 2021
    assert lineage["raw_response_id"] is not None
    assert len(lineage["response_hash"]) == 64
    assert lineage["raw_json_record"] is not None
    assert lineage["raw_json_record"]["country"]["id"] == "IN"


# -----------------------------------------------------------------------------
# 5. Automated Scheduler & Idempotency Update Tests
# -----------------------------------------------------------------------------

def test_pipeline_scheduler_initialization():
    from src.ingestion.scheduler import PipelineScheduler
    sched = PipelineScheduler(interval_hours=12.0, lookback_years=4, run_on_startup=False)
    assert sched.interval_seconds == 12.0 * 3600.0
    assert sched.lookback_years == 4
    assert sched.run_on_startup is False
    start_yr, end_yr = sched.get_year_range()
    assert end_yr >= start_yr
    assert (end_yr - start_yr + 1) == 4


def test_pipeline_scheduler_single_pass_mock(mock_api_page_1):
    from src.ingestion.scheduler import PipelineScheduler
    sched = PipelineScheduler(interval_hours=24.0, lookback_years=2, run_on_startup=False)

    with patch("src.ingestion.scheduler.run_pipeline") as mock_run:
        mock_run.return_value = {"status": "COMPLETED", "total_inserted": 2, "total_updated": 0}
        res = sched.execute_scheduled_run(max_pages=1)
        assert res["status"] == "COMPLETED"
        assert res["total_inserted"] == 2
        mock_run.assert_called_once()


def test_idempotent_ingestion_updates_existing_records(mock_api_page_1):
    """Verifies that re-ingesting the exact same observations increments updated count without duplicating rows."""
    ingester = WorldBankIngester(per_page=2)

    def mock_get(endpoint, params=None):
        raw_b = json.dumps(mock_api_page_1).encode("utf-8")
        import hashlib
        h = hashlib.sha256(raw_b).hexdigest()
        return 200, raw_b, mock_api_page_1, h

    with patch.object(ingester.api_client, "get", side_effect=mock_get):
        # First ingestion
        res1 = ingester.ingest_indicator("NY.GDP.PCAP.CD", start_year=2021, end_year=2021, max_pages=1)
        assert res1["status"] == "COMPLETED"

        # Second ingestion of the same data
        res2 = ingester.ingest_indicator("NY.GDP.PCAP.CD", start_year=2021, end_year=2021, max_pages=1)
        assert res2["status"] == "COMPLETED"
        assert res2["updated"] >= 2
        assert res2["inserted"] == 0


def test_api_ingestion_runs_history_query():
    from src.dashboard.queries import get_api_ingestion_runs_history
    history_df = get_api_ingestion_runs_history(limit=5)
    assert not history_df.empty
    assert "run_id" in history_df.columns
    assert "status" in history_df.columns
    assert "run_type" in history_df.columns
    assert "duration_seconds" in history_df.columns

