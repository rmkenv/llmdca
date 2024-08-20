import streamlit as st
import google.generativeai as genai
import PyPDF2
import pandas as pd
from io import StringIO

# Sidebar with instructions
st.sidebar.title("User Instructions")
st.sidebar.markdown("""
1. Enter your Gemini API key.
2. Upload the parent document (PDF or TXT) from which requirements will be generated.
3. Review and edit the generated evaluation criteria if needed.
4. Upload the documents you want to check for compliance.
5. Click 'Analyze Documents' to start the compliance check.
6. Review the results and download the CSV report if desired.
""")

st.sidebar.markdown("---")
st.sidebar.markdown("""
For more information:
- [Gemini API Documentation](https://ai.google.dev/)
""")

# Main content
st.title("Document Compliance Analyzer")

# Prompt user to input their Gemini API key
api_key = st.text_input("Enter your Gemini API key", type="password")
st.markdown("[Get an API key with your Google Account](https://ai.google.dev/gemini-api/docs/api-key)")

# Configure Gemini API
if api_key:
  genai.configure(api_key=api_key)

def extract_text_from_pdf(file):
  pdf_reader = PyPDF2.PdfReader(file)
  text = ""
  for page in pdf_reader.pages:
      text += page.extract_text()
  return text

def generate_requirements_and_checklist(parent_doc):
  doc_text = extract_text_from_pdf(parent_doc) if parent_doc.type == "application/pdf" else parent_doc.getvalue().decode("utf-8")
  
  model = genai.GenerativeModel('gemini-pro')
  prompt = f"""
  Based on the following parent document, generate a list of requirements and a checklist for compliance:

  Parent Document:
  {doc_text}

  Please provide:
  1. A list of key requirements
  2. A numbered checklist for compliance evaluation
  """
  response = model.generate_content(prompt)
  return response.text

def analyze_document(document, checklist, reference_text):
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
  Analyze the following document against the reference text and checklist:

  Document to analyze:
  {doc_text}

  Reference text:
  {reference_text}

  Checklist:
  {checklist}

  Determine if the document conforms with the requirements from the reference text. 
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

# Step 1: Upload parent document
st.header("Step 1: Upload Parent Document")
parent_doc = st.file_uploader("Upload the parent document", type=["txt", "pdf"])

if parent_doc and api_key:
  # Generate requirements and checklist
  requirements_and_checklist = generate_requirements_and_checklist(parent_doc)
  
  # Step 2: Review and edit evaluation criteria
  st.header("Step 2: Review and Edit Evaluation Criteria")
  st.write("Generated requirements and checklist:")
  st.text_area("Edit if needed:", value=requirements_and_checklist, height=300, key="edited_criteria")
  
  # Extract checklist from the edited criteria
  checklist = [item.strip() for item in st.session_state.edited_criteria.split('\n') if item.strip().startswith(tuple('123456789'))]
  
  # Step 3: Upload documents to analyze
  st.header("Step 3: Upload Documents to Analyze")
  uploaded_files = st.file_uploader("Upload documents to check for compliance", type=["txt", "pdf"], accept_multiple_files=True)

  if uploaded_files:
      if st.button("Analyze Documents"):
          for uploaded_file in uploaded_files:
              st.write(f"Analyzing: {uploaded_file.name}")
              results, supporting_evidence, summary_statement = analyze_document(uploaded_file, checklist, st.session_state.edited_criteria)
              
              st.write(f"Supporting evidence:\n{supporting_evidence}")
              st.write(f"{summary_statement}")
              
              for item, result in results:
                  st.write(f"{item}: {result}")
                  st.divider()
              
              csv = create_csv(results, supporting_evidence, summary_statement)
              st.download_button(
                  label="Download Results as CSV",
                  data=csv,
                  file_name=f"compliance_results_{uploaded_file.name}.csv",
                  mime="text/csv"
              )
              st.divider()
  else:
      st.write("Please upload at least one document to analyze.")
elif not api_key:
  st.warning("Please enter your Gemini API key.")
else:
  st.write("Please upload the parent document to generate requirements and checklist.")
