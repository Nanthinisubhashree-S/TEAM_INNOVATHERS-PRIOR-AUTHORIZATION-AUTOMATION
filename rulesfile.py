import sqlite3
from datetime import datetime, date
import re
from config import DB_PATH

def to_int(x, default=0):
    try:
        if x is None: return default
        if isinstance(x, int): return x
        s = str(x).strip().replace(",", "")
        m = re.search(r"[-+]?\d+", s)
        return int(m.group(0)) if m else default
    except: return default

def parse_date_any(s):
    if not s: return None
    s = str(s).strip()
    fmts = ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y.%m.%d"]
    for f in fmts:
        try: return datetime.strptime(s[:10], f).date()
        except: continue
    return None

def get_treatment_from_icd(conn, icd_codes):
    cur = conn.cursor()
    for code in icd_codes:
        cur.execute("SELECT treatment_name FROM treatment_table WHERE icd10_code=?", (code,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0].strip()
    return None

def check_rules(conn, patient_id, treatment_name, provider_npi):
    cur = conn.cursor()
    reasons = []
    provider_npi_int = int(provider_npi)

    # Rule 0: Patient exists
    cur.execute("SELECT Age, Insurance_ID FROM patient_table WHERE Patient_ID=?", (patient_id,))
    p = cur.fetchone()
    if not p: reasons.append("Patient not found"); patient_age=None; insurance_id=None
    else: patient_age, insurance_id = to_int(p[0]), p[1]

    # Rule 5: Claim date within policy term (3 years)
    claim_date = None
    if insurance_id:
        cur.execute("SELECT Claim_Date FROM insurance_table WHERE Insurance_ID=?", (insurance_id,))
        ins = cur.fetchone()
        claim_date = parse_date_any(ins[0]) if ins else None
        if not claim_date or (date.today() - claim_date).days > 365*3:
            reasons.append("Claim date outside 3 years")

    # Rule 8: Provider active
    cur.execute("SELECT Start_date, End_date, Rndrng_Prvdr_Type FROM provider_table WHERE Rndrng_NPI=?", (provider_npi_int,))
    prov = cur.fetchone()
    if prov:
        prov_start = parse_date_any(prov[0])
        prov_end = parse_date_any(prov[1])
        prov_type = prov[2].strip() if prov[2] else None
        if not (prov_start and prov_end and claim_date and prov_start <= claim_date <= prov_end):
            reasons.append("Provider not active on claim date")
    else:
        reasons.append("Provider not found")
        prov_type = None

    # Rule 9: Valid treatment
    cur.execute("SELECT COUNT(1) FROM treatment_table WHERE treatment_name=?", (treatment_name,))
    if cur.fetchone()[0] <= 0:
        reasons.append(f"Treatment '{treatment_name}' not authorized")

    # Rule 9b: Provider services should not exceed beneficiaries
    cur.execute("SELECT Tot_Srvcs, Tot_Benes FROM provider_table WHERE Rndrng_NPI=?", (provider_npi_int,))
    row = cur.fetchone()
    if row:
        tot_srvcs, tot_benes = to_int(row[0]), to_int(row[1])
        if tot_srvcs > tot_benes:
            reasons.append("Provider services exceed beneficiaries.")
    else:
        reasons.append("Provider service/beneficiary data not found")

    # Rule 10: Provider type matches treatment
    treatment_provider_map = {
        "Dialysis": "Nephrologist",
        "Chemotherapy": "Oncologist",
        "Angioplasty": "Cardiologist",
        "Cataract": "Ophthalmologist",
        "Fracture": "Orthologist"
    }
    expected_type = treatment_provider_map.get(treatment_name)
    if expected_type and prov_type and prov_type.lower() != expected_type.lower():
        reasons.append(f"Provider type '{prov_type}' does not match treatment '{treatment_name}'")

    overall_decision = "APPROVED" if not reasons else "DENIED"
    summary = "; ".join(reasons) if reasons else "All rules passed"
    return overall_decision, summary