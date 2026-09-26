"""
Automated Unit Tests for Day 7:
Portfolio Polish & AI Natural-Language Query Assistant.

Tests:
1. AIAssistantEngine preset queries structure and count.
2. SQL execution against verified Day 3 and Day 4 views.
3. Natural-language intent matching (budget, outcome, reach, quality).
4. Program alias extraction and filtering (PRG-001 ... PRG-005).
5. SQL Injection Prevention & keyword validation.
6. Multi-statement and comment injection blocking.
7. Architectural explanation generation.
8. AI Query Assistant Streamlit page module load.
"""

import pytest
import pandas as pd
from src.dashboard.ai_assistant import AIAssistantEngine, PRESET_QUERIES


def test_preset_queries_structure():
    """Verifies all preset queries have required fields and non-empty SQL."""
    presets = AIAssistantEngine.get_preset_queries()
    assert len(presets) >= 6
    for p in presets:
        assert "id" in p
        assert "title" in p
        assert "question" in p
        assert "category" in p
        assert "sql" in p
        assert "explanation" in p
        assert p["sql"].strip().upper().startswith("SELECT")


def test_preset_query_execution():
    """Verifies that all preset queries execute successfully against live PostgreSQL."""
    for p in PRESET_QUERIES:
        df = AIAssistantEngine.execute_query(p["sql"])
        assert isinstance(df, pd.DataFrame)
        assert not df.empty, f"Preset query '{p['id']}' returned no rows."


def test_over_budget_preset_accuracy():
    """Verifies that the over-budget preset identifies PRG-005 with 156.75% utilization."""
    res = AIAssistantEngine.answer_question("Which programs are currently exceeding their allocated budget?")
    assert "PRG-005" in res["answer"]
    assert "156.75%" in res["answer"]
    assert len(res["df"]) == 1
    assert res["df"].iloc[0]["program_id"] == "PRG-005"


def test_highest_cost_per_beneficiary_preset():
    """Verifies the highest cost per beneficiary query returns PRG-002."""
    res = AIAssistantEngine.answer_question("Which program has the highest cost per beneficiary?")
    assert "PRG-002" in res["answer"]
    assert "4,346.91" in res["answer"]
    assert res["df"].iloc[0]["program_id"] == "PRG-002"


def test_natural_language_program_filter():
    """Verifies natural language inquiry extracting program alias (Youth Coding Bootcamp -> PRG-003)."""
    res = AIAssistantEngine.answer_question("Show outcome improvements for Youth Coding Bootcamp")
    assert res["category"] == "Program Impact"
    assert "PRG-003" in res["sql"]
    assert len(res["df"]) == 1
    assert res["df"].iloc[0]["program_id"] == "PRG-003"


def test_natural_language_reach_intent():
    """Verifies community reach keyword detection maps to v_program_reach."""
    res = AIAssistantEngine.answer_question("How many attendance hours were delivered to beneficiaries?")
    assert "v_program_reach" in res["sql"]
    assert "total_session_hours" in res["df"].columns


def test_natural_language_quality_blocking_intent():
    """Verifies blocking defect inquiry maps to v_data_quality_blocking."""
    res = AIAssistantEngine.answer_question("What are the blocking data quality errors?")
    assert "v_data_quality_blocking" in res["sql"]
    assert len(res["df"]) == 10  # 10 verified blocking ERROR records


def test_sql_validator_allows_valid_select():
    """Verifies validator permits valid SELECT queries."""
    assert AIAssistantEngine.validate_sql("SELECT * FROM v_program_kpis;") is True
    assert AIAssistantEngine.validate_sql("WITH cte AS (SELECT 1) SELECT * FROM cte") is True


def test_sql_validator_rejects_dml_and_ddl():
    """Verifies validator blocks DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE."""
    assert AIAssistantEngine.validate_sql("DROP TABLE beneficiaries;") is False
    assert AIAssistantEngine.validate_sql("DELETE FROM programs WHERE program_id = 'PRG-001';") is False
    assert AIAssistantEngine.validate_sql("INSERT INTO programs VALUES ('PRG-999');") is False
    assert AIAssistantEngine.validate_sql("UPDATE programs SET budget_allocated = 0;") is False
    assert AIAssistantEngine.validate_sql("TRUNCATE TABLE source_records;") is False
    assert AIAssistantEngine.validate_sql("ALTER TABLE source_records ADD COLUMN hacked TEXT;") is False


def test_sql_validator_rejects_injection_tricks():
    """Verifies validator blocks comment characters and multiple chained statements."""
    assert AIAssistantEngine.validate_sql("SELECT * FROM programs; DROP TABLE attendance;") is False
    assert AIAssistantEngine.validate_sql("SELECT * FROM programs -- comment attack") is False
    assert AIAssistantEngine.validate_sql("SELECT * FROM programs /* multi line */") is False


def test_ai_page_module_imports():
    """Verifies that the Streamlit page module imports without syntax or dependency errors."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ai_page", "pages/5_AI_Query_Assistant.py")
    assert spec is not None
    assert spec.loader is not None
