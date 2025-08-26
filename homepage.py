import streamlit as st
import sqlite3
from PIL import Image
from io import BytesIO
from reportlab.pdfgen import canvas

from config import DB_PATH, allowed_fractures
from auditfile import ensure_audit_table, log_audit, render_audit_page
from rulesfile import get_treatment_from_icd, check_rules
from documentlabresult import extract_patient_data
from xrayresult import preprocess_image, detect_fracture, postprocess, map_to_icd10

# Ensure audit table exists
ensure_audit_table()

# ----------------------------
# PDF Generator
# ----------------------------
def generate_pdf(patient_id, treatment, provider, rule_status, proof_status, final_decision, summary):
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.setFont("Helvetica", 12)
    c.drawString(50, 800, f"Patient ID: {patient_id}")
    c.drawString(50, 780, f"Treatment: {treatment}")
    c.drawString(50, 760, f"Provider NPI: {provider}")
    c.drawString(50, 740, f"Rule Status: {rule_status}")
    c.drawString(50, 720, f"Proof Status: {proof_status}")
    c.drawString(50, 700, f"Final Decision: {final_decision}")
    c.drawString(50, 680, f"Summary: {summary}")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

st.set_page_config(page_title="Prior Authorization and Automation", layout="wide")

# ----------------------------
# Navigation with two buttons
# ----------------------------

if "page" not in st.session_state:
    st.session_state.page = "Prior Authorization"

st.title("🏠 PRIOR AUTHORIZATION AND AUTOMATION")

col1, col2 = st.columns(2)
with col1:
    if st.button("⚖ Prior Authorization"):
        st.session_state.page = "Prior Authorization"
with col2:
    if st.button("📜 Audit Trail"):
        st.session_state.page = "Audit Trail"

st.markdown("---")

# ----------------------------
# Prior Authorization Page
# ----------------------------
if st.session_state.page == "Prior Authorization":
    st.title("⚖ Prior Authorization Approval System")

    uploaded_file = st.file_uploader("Upload PA PDF/Docx", type=["pdf","docx"])
    if uploaded_file:
        extracted = extract_patient_data(uploaded_file)
        st.subheader("✅ Extracted Info")
        st.write(extracted)

        conn = sqlite3.connect(DB_PATH)
        treatment_name = get_treatment_from_icd(conn, extracted["ICD-10_Codes"])
        rule_status, rule_summary = check_rules(conn, extracted["Patient_ID"], treatment_name, extracted["Provider_NPI"])
        st.write(f"Rule Engine Status: {rule_status}")
        st.write(f"Rule Summary: {rule_summary}")

        proof_choice = st.radio("Select Proof Type", ["Lab Report","X-ray Fracture"])
        proof_status = "PENDING"

        if proof_choice == "Lab Report":
            lab_file = st.file_uploader("Upload Lab Report", type=["pdf","docx","csv"])
            if lab_file:
                proof_status = "APPROVED"
                st.success("Lab Report Verified ✅")

        elif proof_choice == "X-ray Fracture":
            xray_file = st.file_uploader("Upload X-ray Image", type=["jpg","jpeg","png"])
            if xray_file and extracted["ICD-10_Codes"]:
                icd10_claimed = extracted["ICD-10_Codes"][0]
                image = Image.open(xray_file)
                image_np = preprocess_image(image)
                outputs = detect_fracture(image_np)
                class_ids = postprocess(outputs)
                detected_bones, predicted_icd10_codes = map_to_icd10(class_ids)

                allowed_codes = allowed_fractures.get(icd10_claimed, [icd10_claimed])
                matched_codes = [code for code in predicted_icd10_codes if code in allowed_codes]

                if matched_codes:
                    proof_status = "APPROVED"
                    st.success(f"Fracture Verified ✅ Detected: {detected_bones[0]}, Code: {matched_codes[0]}")
                else:
                    proof_status = "DENIED"
                    st.error(f"Fracture Verification Failed ❌ (Expected: {icd10_claimed}, Got: {predicted_icd10_codes})")

        if st.button("Generate Final PDF"):
            final_decision = "APPROVED" if rule_status == "APPROVED" and proof_status == "APPROVED" else "DENIED"
            st.write(f"Final Decision: {final_decision}")

            icd10_code = extracted["ICD-10_Codes"][0] if extracted.get("ICD-10_Codes") else None

            log_audit(
                extracted["Patient_ID"],
                treatment_name,
                icd10_code,
                extracted["Provider_NPI"],
                rule_status,
                proof_status,
                final_decision
            )

            pdf_buffer = generate_pdf(
                extracted["Patient_ID"],
                treatment_name,
                extracted["Provider_NPI"],
                rule_status,
                proof_status,
                final_decision,
                rule_summary
            )
            st.download_button("Download PA Result PDF",
                               data=pdf_buffer,
                               file_name="PA_Result.pdf",
                               mime="application/pdf")

        conn.close()

# ----------------------------
# Audit Trail Page
# ----------------------------
elif st.session_state.page == "Audit Trail":
    
    render_audit_page()