# TraceImpact 2.0 — Power BI Desktop Project Package

This directory contains the complete Power BI semantic model assets, Power Query M connection scripts, centralized DAX formulas, theme styling, and data extracts for **TraceImpact 2.0**.

---

## Directory Inventory

- **`PowerQuery_M_Scripts.m`**: Ready-to-use Power Query M code for connecting Power BI Desktop directly to PostgreSQL views on `localhost:5432`.
- **`DAX_Measures.dax`**: Complete library of DAX formulas organized by the 9 dashboard pages.
- **`TraceImpact_Theme.json`**: Custom dark-mode theme (*Mission Control Void*, `#0A0F1A`) for 1-click styling in Power BI Desktop.
- **`power_bi_model_schema.json`**: Semantic model schema definition including table definitions, relationships, and metadata.
- **`data_extracts/`**: Pre-exported CSV data extracts (14 tables) generated directly from PostgreSQL for offline or instant import without a local database.

---

## 5-Minute Setup in Power BI Desktop

1. **Open Power BI Desktop** (Windows or VM).
2. **Load Data**:
   - *Direct Database*: **Get Data** ➔ **PostgreSQL database** (`localhost:5432` / `traceimpact`) and select views `v_pbi_*` and dimension tables.
   - *Offline CSVs*: **Get Data** ➔ **Folder** ➔ select `power_bi/data_extracts/`.
3. **Apply Theme**: **View** ribbon ➔ **Themes** ➔ **Browse for themes...** ➔ select `TraceImpact_Theme.json`.
4. **Create Relationships**: Ensure `Dim_Country`, `Dim_Indicator`, `Dim_Program`, `Dim_Severity`, and `Dim_Status` filter Fact tables with single cross-filter direction (`1:*`).
5. **Add DAX Measures**: Copy formulas from `DAX_Measures.dax` into a dedicated `_Measures` table.
6. **Save**: Save as `TraceImpact_2.0.pbix`.

For the complete architectural guide and validation tables, see [`docs/POWER_BI_FINAL_REPORT.md`](../docs/POWER_BI_FINAL_REPORT.md).
