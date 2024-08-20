import streamlit as st
import google.generativeai as genai
import PyPDF2
import pandas as pd
from io import StringIO

# Title and description
st.title("FOA Document Compliance Analyzer")
st.markdown("""
For more information on the related regulations and requirements, you can refer to [COMAR 14.26.02 - Green Building Tax Credit Program](https://github.com/MEADecarb/FOAChat/blob/main/COMAR%2014.26.02%20%20Green%20Building%20Tax%20Credit%20Program.md).
""")

st.markdown("""
For more details on MD's DoIT AI guidelines, you can refer to [Interim General AI Guidance](https://doit.maryland.gov/policies/Pages/InterimGenAIGuidance.aspx).
""")

# Prompt user to input their Gemini API key
api_key = st.text_input("Enter your Gemini API key", type="password")
st.markdown("[Get an API key with your Google Account](https://ai.google.dev/gemini-api/docs/api-key)")

# Configure Gemini API
if api_key:
    genai.configure(api_key=api_key)

# Numbered checklist based on Section 14.26.02.04 and Section 14.26.02.05
checklist = [
    "1. The Administration shall publish on its website a FOA for each grant offered by the Administration.",
    "2. Each initial FOA shall include an application period of at least 30 calendar days.",
    "3. Each FOA shall explain each of the following when applicable:",
    "3.1 Name and purpose",
    "3.2 Duration and schedule",
    "3.3 Requirements",
    "3.4 Deadlines",
    "3.5 Anticipated funding amount at the time the FOA is published",
    "3.6 Designation as a competitive or a noncompetitive grant",
    "3.7 Evaluation criteria",
    "3.8 Method for determining a grant amount under the FOA and whether an amount other than the requested amount may be offered",
    "3.9 The required form and manner in which to submit a complete application",
    "3.10 Limitations on the offer of a grant, including the amount for an individual grant or the number of grants an applicant may receive",
    "3.11 Evaluation process",
    "3.12 Other information the Administration determines is appropriate",
]

# Reference text directly from COMAR 14.26.02
reference_text = """
COMAR 14.26.02 - Green Building Tax Credit Program:
2. Each initial FOA shall include an application period of at least 30 calendar days.
3. Each FOA shall explain each of the following when applicable:
   3.1 Name and purpose
   3.2 Duration and schedule
   3.3 Requirements
   3.4 Deadlines
   3.5 Anticipated funding amount at the time the FOA is published
   3.6 Designation as a competitive or a noncompetitive grant
   3.7 Evaluation criteria
   3.8 Method for determining a grant amount under the FOA and whether an amount other than the requested amount may be offered
   3.9 The required form and manner in which to submit a complete application
   3.10 Limitations on the offer of a grant, including the amount for an individual grant or the number of grants an applicant may receive
   3.11 Evaluation process
   3.12 Other information the Administration determines is appropriate
"""

def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def analyze_document(document, reference_text):
    doc_text = extract_text_from_pdf(document) if document.type == "application/pdf" else document.getvalue().decode("utf-8")

    # Perform checklist verification
    results = []
    for item in checklist:
        if item.lower() in doc_text.lower():
            results.append((item, "Yes"))
        else:
            results.append((item, "No"))

    # Use Gemini to provide supporting evidence
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    Analyze the following document against the reference law and intent:

    Document to analyze:
    {doc_text}

    Reference law and intent:
    {reference_text}

    Determine if the document conforms with the intent and law from the reference. 
    Provide supporting evidence for each checklist item.

    Additionally, provide an overall summary statement about suggested improvements for the document.
    """
    response = model.generate_content(prompt)
    supporting_evidence = response.text

    # Extract the formatted supporting evidence and summary statement
    summary_start = supporting_evidence.find("Overall Summary Statement")
    if summary_start != -1:
        supporting_evidence_formatted = supporting_evidence[:summary_start].strip()
        summary_statement = supporting_evidence[summary_start:].strip()
    else:
        supporting_evidence_formatted = supporting_evidence.strip()
        summary_statement = "No summary provided."

    return results, supporting_evidence_formatted, summary_statement

def create_csv(results, supporting_evidence, summary_statement):
    df = pd.DataFrame(results, columns=["Checklist Item", "Compliance"])
    df["Supporting Evidence"] = [""] * len(df)
    df.loc[0, "Supporting Evidence"] = supporting_evidence  # Add supporting evidence to the first row
    df["Summary Statement"] = summary_statement
    csv = df.to_csv(index=False)
    return csv

# Upload documents to analyze
uploaded_files = st.file_uploader("Upload documents to analyze", type=["txt", "pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("Analyze Documents") and api_key:
        for uploaded_file in uploaded_files:
            st.write(f"Analyzing: {uploaded_file.name}")
            results, supporting_evidence, summary_statement = analyze_document(uploaded_file, reference_text)
            
            st.write(f"Supporting evidence:\n{supporting_evidence}")
            st.write(f"{summary_statement}")
            
            for item, result in results:
                st.write(f"{item}: {result}")
                st.divider()
            
            csv = create_csv(results, supporting_evidence, summary_statement)
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name="compliance_results.csv",
                mime="text/csv"
            )
            st.divider()
    elif not api_key:
        st.warning("Please enter your Gemini API key.")
else:
    st.write("Please upload at least one document to analyze.")
