from PyPDF2 import PdfReader
import docx2txt
import re
import tempfile

def get_document_text(file):
    text = ""
    if file.type == "application/pdf":
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            t = page.extract_text()
            if t: text += t + "\n"
    elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/msword"]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file.getbuffer())
            tmp_path = tmp.name
        text += docx2txt.process(tmp_path) + "\n"
    else:
        try:
            text += file.read().decode("utf-8")
        except:
            text += ""
    return text

def extract_patient_data(file):
    text = get_document_text(file)
    text = re.sub(r"\s+", " ", text)
    patient_ids = re.findall(r"Patient\s*ID[:\s\-]*([A-Za-z0-9\-_]+)", text, flags=re.I)
    npi_numbers = re.findall(r"NPI\s*(?:#|number)?\s*[:\s]*([0-9]{10})", text, flags=re.I)
    icd10_codes = re.findall(r"\b([A-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?)\b", text)
    return {
        "Patient_ID": patient_ids[0].strip() if patient_ids else None,
        "Provider_NPI": npi_numbers[0].strip() if npi_numbers else None,
        "ICD-10_Codes": list(set(icd10_codes)) if icd10_codes else []
    }