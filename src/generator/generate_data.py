"""
Synthetic Data Generator for TraceImpact.

Generates 5 realistic synthetic nonprofit datasets and saves them into data/raw/.
CRITICAL: Deliberate, realistic data-quality anomalies are introduced here
to simulate real-world nonprofit spreadsheet fragmentation.

Datasets Generated:
1. programs.csv       - Organization's active community programs and budgets.
2. beneficiaries.csv  - Individual participants/clients with demographics.
3. attendance.csv     - Daily/weekly workshop and session attendance logs.
4. expenses.csv       - Operational and program expenditures.
5. outcomes.csv       - Pre- and post-intervention survey scores.
"""

import os
import random
from pathlib import Path
import pandas as pd
from faker import Faker
from src.config import DATA_RAW_DIR

# Seed for reproducible synthetic data generation
random.seed(42)
fake = Faker(locale="en_IN")  # Realistic synthetic Indian community names and places
Faker.seed(42)


def generate_all_raw_datasets():
    """Generates all 5 raw CSV datasets with deliberate real-world flaws."""
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Generating synthetic nonprofit datasets...")

    # -------------------------------------------------------------
    # 1. PROGRAMS DATASET
    # -------------------------------------------------------------
    programs_data = [
        {"program_id": "PRG-001", "program_name": "Digital Literacy Initiative", "target_category": "Education", "budget_allocated": 150000.0, "start_date": "2024-01-10", "end_date": "2024-12-20"},
        {"program_id": "PRG-002", "program_name": "Women Vocational Sewing", "target_category": "Livelihood", "budget_allocated": 220000.0, "start_date": "2024-02-01", "end_date": "2024-11-30"},
        {"program_id": "PRG-003", "program_name": "Youth Coding Bootcamp", "target_category": "Skill Development", "budget_allocated": 180000.0, "start_date": "2024-03-01", "end_date": "2024-09-30"},
        {"program_id": "PRG-004", "program_name": "Elderly Healthcare Outreach", "target_category": "Healthcare", "budget_allocated": 120000.0, "start_date": "2024-01-15", "end_date": "2024-12-15"},
        {"program_id": "PRG-005", "program_name": "Community Nutrition Drive", "target_category": "Health & Nutrition", "budget_allocated": 95000.0, "start_date": "2024-04-01", "end_date": "2024-10-31"},
    ]
    df_programs = pd.DataFrame(programs_data)
    df_programs.to_csv(DATA_RAW_DIR / "programs.csv", index=False)
    print(f" -> Created {DATA_RAW_DIR / 'programs.csv'} ({len(df_programs)} rows)")

    # -------------------------------------------------------------
    # 2. BENEFICIARIES DATASET (with duplicates, missing age, dirty locations)
    # -------------------------------------------------------------
    beneficiaries_records = []
    locations_pool = ["New Delhi", "new delhi", "Delhi", "N. Delhi", "Noida", "noida", "Gurugram", "Gurgaon", "GURGAON", "Faridabad"]
    
    # Generate 50 standard beneficiaries
    for i in range(1, 51):
        b_id = f"BEN-{i:03d}"
        first_name = fake.first_name()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"
        gender = random.choice(["Female", "Male", "Non-Binary", "F", "M"])
        age = random.choice([16, 18, 21, 24, 28, 32, 35, 42, 50, 62, None, ""])
        location = random.choice(locations_pool)
        
        # Mix date formats: ISO format, Slash format, or None
        date_pick = random.random()
        if date_pick < 0.7:
            signup_date = f"2024-{random.randint(1, 4):02d}-{random.randint(1, 28):02d}"
        elif date_pick < 0.9:
            signup_date = f"{random.randint(1, 28):02d}/{random.randint(1, 4):02d}/2024"
        else:
            signup_date = None  # Missing signup date

        phone = fake.phone_number() if random.random() > 0.15 else ""

        beneficiaries_records.append({
            "beneficiary_id": b_id,
            "full_name": full_name,
            "gender": gender,
            "age": age,
            "city_location": location,
            "registration_date": signup_date,
            "contact_phone": phone
        })

    # INTENTIONAL ANOMALY: Duplicate records with slight spelling & formatting differences
    beneficiaries_records.append({
        "beneficiary_id": "BEN-012",  # Duplicate ID with different casing/spelling
        "full_name": beneficiaries_records[11]["full_name"].lower(),
        "gender": beneficiaries_records[11]["gender"],
        "age": beneficiaries_records[11]["age"],
        "city_location": "Delhi NCR",
        "registration_date": "2024-02-15",
        "contact_phone": beneficiaries_records[11]["contact_phone"]
    })
    
    beneficiaries_records.append({
        "beneficiary_id": "BEN-099",  # Different ID but exact duplicate person
        "full_name": beneficiaries_records[4]["full_name"],
        "gender": beneficiaries_records[4]["gender"],
        "age": beneficiaries_records[4]["age"],
        "city_location": beneficiaries_records[4]["city_location"],
        "registration_date": "2024-03-01",
        "contact_phone": beneficiaries_records[4]["contact_phone"]
    })

    df_beneficiaries = pd.DataFrame(beneficiaries_records)
    # Column naming inconsistency: in some files staff named it "participant_code"
    df_beneficiaries.to_csv(DATA_RAW_DIR / "beneficiaries.csv", index=False)
    print(f" -> Created {DATA_RAW_DIR / 'beneficiaries.csv'} ({len(df_beneficiaries)} rows)")

    # -------------------------------------------------------------
    # 3. ATTENDANCE DATASET (with inconsistent program names & duplicate check-ins)
    # -------------------------------------------------------------
    attendance_records = []
    # Program name variations used by different field staff
    program_name_variations = {
        "PRG-001": ["Digital Literacy Initiative", "digital literacy", "Digital-Literacy", "Digi-Literacy"],
        "PRG-002": ["Women Vocational Sewing", "vocational sewing", "Women Sewing Workshop"],
        "PRG-003": ["Youth Coding Bootcamp", "Youth-Coding", "coding bootcamp"],
        "PRG-004": ["Elderly Healthcare Outreach", "Elderly Health", "Health Outreach"],
        "PRG-005": ["Community Nutrition Drive", "Nutrition Drive", "community-nutrition"],
    }

    session_dates = [f"2024-02-{d:02d}" for d in range(1, 29, 3)] + [f"2024-03-{d:02d}" for d in range(1, 30, 3)]

    att_id = 1
    for s_date in session_dates:
        for prg_id, variations in program_name_variations.items():
            # Randomly pick 4-8 attendees per session
            attendees = random.sample(range(1, 45), k=random.randint(4, 8))
            for b_idx in attendees:
                b_id = f"BEN-{b_idx:03d}"
                prg_name = random.choice(variations)
                status = random.choice(["Present", "Present", "present", "P", "Attended"])
                
                attendance_records.append({
                    "attendance_id": f"ATT-{att_id:04d}",
                    "participant_id": b_id,  # Notice column name: participant_id instead of beneficiary_id
                    "program_title": prg_name, # Notice column name: program_title instead of program_name
                    "session_date": s_date,
                    "attendance_status": status,
                    "session_hours": random.choice([2.0, 2.5, 3.0, "2 hrs", None]) # Inconsistent numeric format
                })
                att_id += 1

    # INTENTIONAL ANOMALY: Duplicate attendance records (double logging by staff)
    for _ in range(5):
        dup = attendance_records[random.randint(0, 20)].copy()
        dup["attendance_id"] = f"ATT-{att_id:04d}"
        att_id += 1
        attendance_records.append(dup)

    # INTENTIONAL ANOMALY: Orphan attendance record (unregistered participant ID)
    attendance_records.append({
        "attendance_id": f"ATT-{att_id:04d}",
        "participant_id": "BEN-999",  # Does NOT exist in beneficiaries.csv
        "program_title": "Digital Literacy Initiative",
        "session_date": "2024-02-14",
        "attendance_status": "Present",
        "session_hours": 2.0
    })

    df_attendance = pd.DataFrame(attendance_records)
    df_attendance.to_csv(DATA_RAW_DIR / "attendance.csv", index=False)
    print(f" -> Created {DATA_RAW_DIR / 'attendance.csv'} ({len(df_attendance)} rows)")

    # -------------------------------------------------------------
    # 4. EXPENSES DATASET (with formatted currency strings, negative values, missing categories)
    # -------------------------------------------------------------
    expense_records = []
    expense_categories = ["Trainer Stipend", "Equipment & Laptops", "Refreshments", "Venue Rental", "Learning Materials", "Travel & Field"]
    
    exp_id = 1
    for m in range(1, 5):
        for prg in programs_data:
            # 2 to 4 expense entries per program per month
            for _ in range(random.randint(2, 4)):
                cat = random.choice(expense_categories)
                amt = round(random.uniform(1500.0, 18000.0), 2)
                exp_date = f"2024-{m:02d}-{random.randint(1, 28):02d}"
                
                # Introduce formatted string representation in some rows: "₹12,500.00"
                if random.random() < 0.2:
                    amt_str = f"₹{amt:,.2f}"
                else:
                    amt_str = amt

                expense_records.append({
                    "expense_ref": f"EXP-{exp_id:04d}",
                    "program_code": prg["program_id"],
                    "expense_category": cat if random.random() > 0.08 else None, # Missing category
                    "amount_spent": amt_str,
                    "incurred_date": exp_date,
                    "receipt_verified": random.choice(["Yes", "Y", "True", "No", "Pending"])
                })
                exp_id += 1

    # INTENTIONAL ANOMALY: Negative expense amount (data entry error)
    expense_records.append({
        "expense_ref": f"EXP-{exp_id:04d}",
        "program_code": "PRG-001",
        "expense_category": "Refreshments",
        "amount_spent": -4500.00,
        "incurred_date": "2024-03-12",
        "receipt_verified": "Yes"
    })
    exp_id += 1

    # INTENTIONAL ANOMALY: Missing program attribution
    expense_records.append({
        "expense_ref": f"EXP-{exp_id:04d}",
        "program_code": "",  # Blank program
        "expense_category": "Office Supplies",
        "amount_spent": 3200.00,
        "incurred_date": "2024-02-18",
        "receipt_verified": "Pending"
    })

    df_expenses = pd.DataFrame(expense_records)
    df_expenses.to_csv(DATA_RAW_DIR / "expenses.csv", index=False)
    print(f" -> Created {DATA_RAW_DIR / 'expenses.csv'} ({len(df_expenses)} rows)")

    # -------------------------------------------------------------
    # 5. OUTCOMES DATASET (with out-of-range scores and missing baseline scores)
    # -------------------------------------------------------------
    outcome_records = []
    indicators = ["Digital Skill Proficiency", "Employment Readiness", "Confidence Score", "Health Knowledge Index"]
    
    out_id = 1
    for b_idx in range(1, 40):
        b_id = f"BEN-{b_idx:03d}"
        prg_id = random.choice(["PRG-001", "PRG-002", "PRG-003", "PRG-004", "PRG-005"])
        indicator = random.choice(indicators)
        baseline = round(random.uniform(20.0, 55.0), 1)
        exit_score = round(baseline + random.uniform(15.0, 40.0), 1)
        survey_date = f"2024-04-{random.randint(1, 28):02d}"

        outcome_records.append({
            "survey_id": f"SURV-{out_id:04d}",
            "client_identifier": b_id,  # Column naming variance: client_identifier
            "program_id": prg_id,
            "metric_name": indicator,
            "baseline_score": baseline if random.random() > 0.1 else None, # Missing baseline
            "exit_score": exit_score,
            "evaluation_date": survey_date
        })
        out_id += 1

    # INTENTIONAL ANOMALY: Exit score exceeding valid max range of 100
    outcome_records.append({
        "survey_id": f"SURV-{out_id:04d}",
        "client_identifier": "BEN-007",
        "program_id": "PRG-001",
        "metric_name": "Digital Skill Proficiency",
        "baseline_score": 45.0,
        "exit_score": 145.0,  # Invalid: max is 100
        "evaluation_date": "2024-04-15"
    })

    df_outcomes = pd.DataFrame(outcome_records)
    df_outcomes.to_csv(DATA_RAW_DIR / "outcomes.csv", index=False)
    print(f" -> Created {DATA_RAW_DIR / 'outcomes.csv'} ({len(df_outcomes)} rows)")
    print("All synthetic raw datasets generated successfully in data/raw/")


if __name__ == "__main__":
    generate_all_raw_datasets()
