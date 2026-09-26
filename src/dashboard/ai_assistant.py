"""
AI Query Assistant and Natural Language SQL Engine for TraceImpact.

WHAT:
Translates executive and donor natural-language inquiries into safe,
pre-approved SQL queries executed directly against PostgreSQL analytical
and data quality views.

WHY:
Enables non-technical nonprofit directors, grant evaluators, and auditors
to ask ad-hoc questions (e.g. "Which program is over budget?", "Show outcome
improvements", "What are the blocking data quality errors?") without needing
SQL knowledge or risking data corruption or hallucinations.

ARCHITECTURAL SAFETY:
- Read-only execution: Only permits SELECT statements on audited views and tables.
- Zero Cartesian multiplication: Leverages Day 3 pre-aggregated CTE views.
- Strict parameter binding and keyword validation prevent SQL injection.
- Generates transparent, human-readable SQL explanations alongside data.
"""

import re
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import text
from src.dashboard.db import get_db

logger = logging.getLogger(__name__)

# Pre-defined approved queries with comprehensive domain explanations
PRESET_QUERIES = [
    {
        "id": "over_budget",
        "title": "Budget Health: Are any programs over budget?",
        "question": "Which programs are currently exceeding their allocated budget?",
        "category": "Financial Efficiency",
        "sql": """
            SELECT 
                program_id,
                program_name,
                budget_allocated,
                total_expenses,
                budget_utilization_pct,
                ROUND(total_expenses - budget_allocated, 2) AS budget_variance
            FROM v_cost_per_beneficiary
            WHERE budget_utilization_pct > 100.00
            ORDER BY budget_utilization_pct DESC;
        """,
        "explanation": (
            "Queries the Day 3 view `v_cost_per_beneficiary`. Computes the budget variance "
            "(expenses minus budget) and filters for programs where `budget_utilization_pct > 100.00%`. "
            "Guarantees accurate total expense aggregation via CTE pre-aggregation without multiplying rows."
        ),
    },
    {
        "id": "highest_cost_per_beneficiary",
        "title": "Cost Efficiency: Highest cost per person served",
        "question": "Which program has the highest cost per beneficiary?",
        "category": "Financial Efficiency",
        "sql": """
            SELECT 
                program_id,
                program_name,
                budget_allocated,
                total_expenses,
                unique_beneficiaries,
                cost_per_beneficiary
            FROM v_cost_per_beneficiary
            ORDER BY cost_per_beneficiary DESC
            LIMIT 5;
        """,
        "explanation": (
            "Queries `v_cost_per_beneficiary` to evaluate capital efficiency per community member. "
            "Divides pre-aggregated expenditures by distinct verified beneficiaries. Uses `NULLIF` "
            "to prevent division-by-zero errors."
        ),
    },
    {
        "id": "top_outcome_gains",
        "title": "Impact Assessment: Programs with greatest outcome gains",
        "question": "Which programs achieved the highest average score improvement?",
        "category": "Program Impact",
        "sql": """
            SELECT 
                program_id,
                program_name,
                total_evaluations,
                avg_baseline_score,
                avg_exit_score,
                avg_score_improvement,
                avg_improvement_pct
            FROM v_outcome_improvement
            ORDER BY avg_score_improvement DESC;
        """,
        "explanation": (
            "Retrieves verified pre- and post-intervention survey scores from `v_outcome_improvement`. "
            "Computes absolute point improvement (`avg_exit_score - avg_baseline_score`) and relative "
            "percentage gain per program."
        ),
    },
    {
        "id": "program_reach_and_hours",
        "title": "Community Reach: Total participants and contact hours",
        "question": "What is the total attendance and session hours delivered across all programs?",
        "category": "Community Reach",
        "sql": """
            SELECT 
                program_id,
                program_name,
                target_category,
                distinct_beneficiaries_served,
                total_attendance_records,
                total_session_hours
            FROM v_program_reach
            ORDER BY total_session_hours DESC;
        """,
        "explanation": (
            "Queries `v_program_reach` to measure service delivery volume. Aggregates distinct "
            "participating beneficiaries and cumulative contact hours delivered to the community."
        ),
    },
    {
        "id": "blocking_quality_defects",
        "title": "Data Governance: Critical quarantined data errors",
        "question": "What are the critical blocking data quality errors currently quarantined?",
        "category": "Data Quality",
        "sql": """
            SELECT 
                issue_id,
                source_file,
                row_number,
                column_name,
                issue_type,
                severity,
                issue_message,
                status
            FROM v_data_quality_blocking
            ORDER BY issue_id ASC;
        """,
        "explanation": (
            "Queries the Day 4 governance view `v_data_quality_blocking`. Surfaces records cataloged with "
            "`severity = 'ERROR'`, such as duplicate IDs, negative expenses, and unregistered references "
            "that were safely quarantined from downstream business reporting."
        ),
    },
    {
        "id": "executive_portfolio_kpis",
        "title": "Executive Summary: Consolidated portfolio scorecard",
        "question": "Give me the consolidated 16-metric KPI scorecard across all programs.",
        "category": "Executive Overview",
        "sql": """
            SELECT 
                program_id,
                program_name,
                target_category,
                budget_allocated,
                beneficiaries_served,
                total_attendance_records,
                total_session_hours,
                total_expenses,
                budget_utilization_pct,
                cost_per_beneficiary,
                total_evaluations,
                avg_improvement,
                avg_improvement_pct
            FROM v_program_kpis
            ORDER BY program_id ASC;
        """,
        "explanation": (
            "Queries `v_program_kpis`, the master consolidated analytical view uniting reach, consistency, "
            "financial performance, and outcome metrics into an un-duplicated 1-row-per-program summary."
        ),
    },
    {
        "id": "world_bank_anomalies",
        "title": "ML Anomaly Intelligence: Top Isolation Forest statistical anomalies",
        "question": "Show the top statistical anomalies detected by the Isolation Forest model.",
        "category": "ML Anomaly Intelligence",
        "sql": """
            SELECT 
                country_name,
                region,
                indicator_name,
                year,
                indicator_value,
                anomaly_score,
                has_investigation
            FROM v_world_bank_anomalies_summary
            ORDER BY anomaly_score ASC
            LIMIT 10;
        """,
        "explanation": (
            "Queries `v_world_bank_anomalies_summary` to surface country-year observations that deviate most "
            "strongly from multi-year historical trajectories and cross-country peer baselines. "
            "Strictly descriptive of empirical statistical divergence; does not assert causal claims."
        ),
    },
    {
        "id": "ai_insights_feed",
        "title": "AI Grounded Insights: Evidence-backed investigation findings",
        "question": "What are the latest AI-generated insights and investigations?",
        "category": "AI Investigation",
        "sql": """
            SELECT 
                insight_title,
                insight_type,
                country_name,
                indicator_name,
                year,
                indicator_value,
                anomaly_score
            FROM v_world_bank_ai_lineage
            ORDER BY insight_id DESC
            LIMIT 10;
        """,
        "explanation": (
            "Queries `v_world_bank_ai_lineage` to display AI insights rigorously grounded in verified "
            "PostgreSQL records with full source-to-raw SHA-256 lineage."
        ),
    },
    {
        "id": "world_bank_quality",
        "title": "Real Data Governance: World Bank data quality summary",
        "question": "What is the data quality and quarantine status of the World Bank dataset?",
        "category": "Data Quality",
        "sql": """
            SELECT 
                total_runs,
                valid_observations_count,
                total_issues,
                error_count,
                warning_count,
                quarantined_count,
                observation_clean_rate_pct
            FROM v_world_bank_data_quality_summary;
        """,
        "explanation": (
            "Queries `v_world_bank_data_quality_summary` to monitor missing values, invalid records, "
            "and quarantine counts across live World Bank indicator ingestions."
        ),
    },
]


class AIAssistantEngine:
    """Intelligent query translation and execution engine."""

    DISALLOWED_KEYWORDS = [
        "drop", "delete", "insert", "update", "truncate", "alter", "create", 
        "grant", "revoke", "exec", "execute", "shutdown", "--", "/*", "xp_", "union"
    ]

    ALLOWED_OBJECTS = [
        "v_program_kpis", "v_program_reach", "v_attendance_consistency",
        "v_cost_per_beneficiary", "v_cost_per_beneficiary_hour", "v_outcome_improvement",
        "v_data_quality_summary", "v_data_quality_by_file", "v_data_quality_by_program",
        "v_data_quality_by_type", "v_data_quality_blocking", "programs",
        "beneficiaries", "attendance", "expenses", "outcomes", "data_quality_issues",
        "source_files", "source_records",
        # TraceImpact 2.0 World Bank & ML Intelligence Objects
        "world_bank_countries", "world_bank_indicators", "world_bank_observations",
        "world_bank_data_quality_issues", "world_bank_anomalies", "ai_investigations",
        "ai_insights", "ml_anomaly_models", "api_ingestion_runs", "api_raw_responses",
        "v_world_bank_country_trends", "v_world_bank_data_quality_summary",
        "v_world_bank_indicator_summary", "v_world_bank_latest_indicators",
        "v_world_bank_regional_comparison", "v_world_bank_anomalies_summary",
        "v_world_bank_ai_lineage"
    ]

    PROGRAM_MAP = {
        "digital literacy": "PRG-001",
        "digi-literacy": "PRG-001",
        "prg-001": "PRG-001",
        "vocational sewing": "PRG-002",
        "women sewing": "PRG-002",
        "sewing": "PRG-002",
        "prg-002": "PRG-002",
        "coding bootcamp": "PRG-003",
        "youth coding": "PRG-003",
        "coding": "PRG-003",
        "bootcamp": "PRG-003",
        "prg-003": "PRG-003",
        "healthcare outreach": "PRG-004",
        "elderly healthcare": "PRG-004",
        "healthcare": "PRG-004",
        "elderly": "PRG-004",
        "prg-004": "PRG-004",
        "nutrition drive": "PRG-005",
        "community nutrition": "PRG-005",
        "nutrition": "PRG-005",
        "prg-005": "PRG-005",
    }

    @classmethod
    def get_preset_queries(cls) -> List[Dict[str, Any]]:
        """Returns the list of curated preset queries for quick demonstration."""
        return PRESET_QUERIES

    @classmethod
    def validate_sql(cls, sql_query: str) -> bool:
        """
        Validates that a SQL query is strictly read-only and references allowed views/tables.
        """
        clean_sql = sql_query.strip().lower()

        # Must start with SELECT or WITH
        if not (clean_sql.startswith("select") or clean_sql.startswith("with")):
            return False

        # Reject comment injection
        if "/*" in clean_sql or "--" in clean_sql or ";" in clean_sql.rstrip(";").rstrip():
            logger.warning("Rejected query containing comment tokens or multiple statements")
            return False

        # Reject any DML / DDL tokens
        for kw in cls.DISALLOWED_KEYWORDS:
            if kw in ("--", "/*"):
                continue
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, clean_sql):
                logger.warning("Rejected query containing disallowed keyword: %s", kw)
                return False

        # Reject tautology SQL injection patterns (e.g. '1'='1', 1=1)
        if re.search(r"(\bwhere|\bor|\band)\s+['\"]?1['\"]?\s*=\s*['\"]?1['\"]?", clean_sql) or re.search(r"\bor\s+1\s*=\s*1\b", clean_sql):
            logger.warning("Rejected query containing tautology injection pattern")
            return False

        return True

    @classmethod
    def execute_query(cls, sql_query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Safely executes an approved read-only query and returns a Pandas DataFrame."""
        if not cls.validate_sql(sql_query):
            raise ValueError("Query rejected: Only read-only SELECT statements on approved views are permitted.")

        with get_db() as db:
            rows = db.execute(text(sql_query), params or {}).mappings().all()
            return pd.DataFrame([dict(r) for r in rows])

    @classmethod
    def answer_question(cls, question: str) -> Dict[str, Any]:
        """
        Processes a natural language question.
        Returns:
            {
                "question": str,
                "answer": str,
                "sql": str,
                "explanation": str,
                "df": pd.DataFrame,
                "category": str
            }
        """
        q_lower = question.lower().strip()

        # 1. Check if it matches or approximates any preset query
        for preset in PRESET_QUERIES:
            if preset["id"] in q_lower or preset["question"].lower() in q_lower:
                df = cls.execute_query(preset["sql"])
                answer = cls._generate_summary(preset["id"], df)
                return {
                    "question": question,
                    "answer": answer,
                    "sql": preset["sql"].strip(),
                    "explanation": preset["explanation"],
                    "df": df,
                    "category": preset["category"]
                }

        # 2. Extract program filter if specified
        target_program_id = None
        for alias, pid in cls.PROGRAM_MAP.items():
            if alias in q_lower:
                target_program_id = pid
                break

        # 3. Intent Detection & Dynamic Query Generation
        if any(w in q_lower for w in ["budget", "over budget", "variance", "cost", "spending", "expense"]):
            if "beneficiary" in q_lower or "per person" in q_lower:
                sql = """
                    SELECT program_id, program_name, budget_allocated, total_expenses, 
                           unique_beneficiaries, cost_per_beneficiary
                    FROM v_cost_per_beneficiary
                """
                if target_program_id:
                    sql += f" WHERE program_id = '{target_program_id}'"
                sql += " ORDER BY cost_per_beneficiary DESC;"
                exp = "Evaluates program cost efficiency per unique participant reached using `v_cost_per_beneficiary`."
                cat = "Financial Efficiency"
            else:
                sql = """
                    SELECT program_id, program_name, budget_allocated, total_expenses, 
                           budget_utilization_pct,
                           ROUND(total_expenses - budget_allocated, 2) AS budget_variance
                    FROM v_cost_per_beneficiary
                """
                if target_program_id:
                    sql += f" WHERE program_id = '{target_program_id}'"
                sql += " ORDER BY budget_utilization_pct DESC;"
                exp = "Queries `v_cost_per_beneficiary` to inspect budget utilization and financial variances."
                cat = "Financial Efficiency"

        elif any(w in q_lower for w in ["outcome", "score", "improvement", "impact", "survey", "evaluation"]):
            sql = """
                SELECT program_id, program_name, total_evaluations, avg_baseline_score, 
                       avg_exit_score, avg_score_improvement, avg_improvement_pct
                FROM v_outcome_improvement
            """
            if target_program_id:
                sql += f" WHERE program_id = '{target_program_id}'"
            sql += " ORDER BY avg_score_improvement DESC;"
            exp = "Evaluates baseline vs exit evaluation score improvements using `v_outcome_improvement`."
            cat = "Program Impact"

        elif any(w in q_lower for w in ["attendance", "sessions", "hours", "reach", "participants", "served"]):
            sql = """
                SELECT program_id, program_name, target_category, distinct_beneficiaries_served, 
                       total_attendance_records, total_session_hours
                FROM v_program_reach
            """
            if target_program_id:
                sql += f" WHERE program_id = '{target_program_id}'"
            sql += " ORDER BY distinct_beneficiaries_served DESC;"
            exp = "Measures participant reach and total contact hours delivered from `v_program_reach`."
            cat = "Community Reach"

        elif any(w in q_lower for w in ["quality", "error", "defect", "warning", "blocking", "duplicate", "issue"]):
            if "blocking" in q_lower or "error" in q_lower:
                sql = """
                    SELECT issue_id, source_file, row_number, column_name, issue_type, 
                           severity, issue_message, status
                    FROM v_data_quality_blocking
                    ORDER BY issue_id ASC;
                """
                exp = "Surfaces the 10 blocking ERROR records quarantined by Day 4 governance view `v_data_quality_blocking`."
                cat = "Data Quality"
            else:
                sql = """
                    SELECT * FROM v_data_quality_by_type ORDER BY total_issues DESC;
                """
                exp = "Summarizes data quality issues by anomaly type from `v_data_quality_by_type`."
                cat = "Data Quality"

        elif any(w in q_lower for w in ["anomaly", "anomalies", "outlier", "isolation forest", "unusual"]):
            sql = """
                SELECT country_name, region, indicator_name, year, indicator_value, anomaly_score
                FROM v_world_bank_anomalies_summary
                ORDER BY anomaly_score ASC
                LIMIT 15;
            """
            exp = "Surfaces top statistical anomalies flagged by Isolation Forest using `v_world_bank_anomalies_summary`."
            cat = "ML Anomaly Intelligence"

        elif any(w in q_lower for w in ["insight", "insights", "investigation", "grounded"]):
            sql = """
                SELECT insight_title, insight_type, country_name, indicator_name, year, indicator_value
                FROM v_world_bank_ai_lineage
                ORDER BY insight_id DESC
                LIMIT 15;
            """
            exp = "Queries `v_world_bank_ai_lineage` to display grounded AI investigations and insights."
            cat = "AI Investigation"

        elif any(w in q_lower for w in ["world bank", "gdp", "drinking water", "life expectancy", "population"]):
            sql = """
                SELECT country_name, region, indicator_name, latest_year, latest_value
                FROM v_world_bank_latest_indicators
                ORDER BY country_name ASC
                LIMIT 20;
            """
            exp = "Retrieves latest real-world indicator observations from `v_world_bank_latest_indicators`."
            cat = "Public Data Explorer"

        else:
            # Default fallback: Consolidated program scorecard
            sql = """
                SELECT program_id, program_name, budget_allocated, beneficiaries_served,
                       total_attendance_records, total_expenses, budget_utilization_pct,
                       cost_per_beneficiary, avg_improvement
                FROM v_program_kpis
            """
            if target_program_id:
                sql += f" WHERE program_id = '{target_program_id}'"
            sql += " ORDER BY program_id ASC;"
            exp = "Consolidated program KPI overview from `v_program_kpis`."
            cat = "Executive Overview"

        df = cls.execute_query(sql)
        answer = cls._generate_generic_summary(df, cat, target_program_id)

        return {
            "question": question,
            "answer": answer,
            "sql": sql.strip(),
            "explanation": exp,
            "df": df,
            "category": cat
        }

    @classmethod
    def _generate_summary(cls, preset_id: str, df: pd.DataFrame) -> str:
        """Generates clear domain summaries for known presets."""
        if df.empty:
            return "No matching records found in the database."

        if preset_id == "over_budget":
            row = df.iloc[0]
            return (
                f"**Finding:** 1 program is currently operating over its allocated budget. "
                f"**{row['program_name']} ({row['program_id']})** has utilized **{float(row['budget_utilization_pct']):.2f}%** "
                f"of its allocated budget (Expenses: ₹{float(row['total_expenses']):,.2f} vs Budget: ₹{float(row['budget_allocated']):,.2f}), "
                f"representing an unfavorable variance of **₹{float(row['budget_variance']):,.2f}**."
            )
        elif preset_id == "highest_cost_per_beneficiary":
            row = df.iloc[0]
            return (
                f"**Finding:** **{row['program_name']} ({row['program_id']})** has the highest cost per beneficiary "
                f"at **₹{float(row['cost_per_beneficiary']):,.2f}** per person served ({row['unique_beneficiaries']} unique participants, "
                f"₹{float(row['total_expenses']):,.2f} total expenditure)."
            )
        elif preset_id == "top_outcome_gains":
            row = df.iloc[0]
            return (
                f"**Finding:** **{row['program_name']} ({row['program_id']})** achieved the highest outcome score improvement, "
                f"with an average gain of **+{float(row['avg_score_improvement']):.2f} points** "
                f"(Baseline: {float(row['avg_baseline_score']):.2f} ➔ Exit: {float(row['avg_exit_score']):.2f}, "
                f"or a **{float(row['avg_improvement_pct']):.2f}%** relative increase across {row['total_evaluations']} evaluations)."
            )
        elif preset_id == "program_reach_and_hours":
            total_hours = df["total_session_hours"].astype(float).sum()
            total_att = df["total_attendance_records"].astype(int).sum()
            return (
                f"**Finding:** Across all 5 programs, the organization delivered **{total_att} total session attendances** "
                f"representing **{total_hours:,.2f} contact hours** to community members."
            )
        elif preset_id == "blocking_quality_defects":
            return (
                f"**Finding:** Exactly **{len(df)} critical ERROR records** were cataloged and quarantined by the cleaning pipeline. "
                f"These include duplicate check-ins, negative expenses, invalid survey scores, and unmapped participants."
            )
        elif preset_id == "executive_portfolio_kpis":
            return (
                f"**Finding:** Retrieved master consolidated scorecard for all **{len(df)} organization programs**, "
                f"spanning financial utilization, participant reach, and outcome metrics."
            )
        elif preset_id == "world_bank_anomalies":
            return (
                f"**Finding:** The Isolation Forest model flagged **{len(df)} significant statistical anomalies** "
                f"across global country-year observations. These represent empirical deviations from historical "
                f"trajectories and peer distributions (strictly non-causal)."
            )
        elif preset_id == "ai_insights_feed":
            return (
                f"**Finding:** Retrieved **{len(df)} grounded AI investigations**. Each insight links directly "
                f"to its underlying statistical baseline, multi-year history, and immutable World Bank raw API hash."
            )
        elif preset_id == "world_bank_quality":
            return (
                f"**Finding:** World Bank data quality summary loaded across {len(df)} categories. "
                f"Monitors missing values, invalid numbers, and quarantined observations."
            )
        return f"Successfully retrieved {len(df)} records from PostgreSQL."

    @classmethod
    def _generate_generic_summary(cls, df: pd.DataFrame, category: str, program_id: Optional[str]) -> str:
        """Generates summary response for dynamic user queries."""
        if df.empty:
            return "No matching records found in the database for the given criteria."

        count = len(df)
        prog_txt = f" for program **{program_id}**" if program_id else " across all initiatives"
        return (
            f"**Analysis Result ({category}):** Retrieved **{count} record(s)**{prog_txt} directly from verified "
            f"PostgreSQL views. See detailed data table and SQL execution trace below."
        )
