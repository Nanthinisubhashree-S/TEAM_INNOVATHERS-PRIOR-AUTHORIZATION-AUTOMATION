import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from config import DB_PATH
from datetime import datetime
import pytz

def get_ist_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

def ensure_audit_table():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                patient_id TEXT,
                treatment_name TEXT,
                icd10_code TEXT,
                provider_npi TEXT,
                rule_status TEXT,
                proof_status TEXT,
                final_decision TEXT
            )
        """)
        conn.commit()

def log_audit(patient_id, treatment_name, icd10_code, provider_npi,
              rule_status, proof_status, final_decision):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_log
            (timestamp, patient_id, treatment_name, icd10_code, provider_npi, rule_status, proof_status, final_decision)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            get_ist_time(),
            patient_id or "",
            treatment_name or "",
            icd10_code or "",
            provider_npi or "",
            rule_status or "",
            proof_status or "",
            final_decision or ""
        ))
        conn.commit()

def render_audit_page():
    st.title("📄 Audit Log Viewer")
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM audit_log ORDER BY timestamp DESC", conn)

    if df.empty:
        st.warning("No audit logs found!")
        return

    st.sidebar.header("Filters")
    patient_filter = st.sidebar.text_input("Filter by Patient ID")
    provider_filter = st.sidebar.text_input("Filter by Provider NPI")
    final_decision_filter = st.sidebar.selectbox(
        "Filter by Final Decision", 
        ["All"] + df['final_decision'].dropna().unique().tolist()
    )

    if patient_filter:
        df = df[df['patient_id'].str.contains(patient_filter, case=False, na=False)]
    if provider_filter:
        df = df[df['provider_npi'].str.contains(provider_filter, case=False, na=False)]
    if final_decision_filter != "All":
        df = df[df['final_decision'] == final_decision_filter]

    st.write(f"Total Records: {len(df)}")
    st.dataframe(df)

    st.download_button(
        label="Download Audit Logs as CSV",
        data=df.to_csv(index=False),
        file_name="audit_logs.csv",
        mime="text/csv"
    )
