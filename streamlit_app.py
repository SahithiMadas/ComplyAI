### 🛠️ Final Updated `streamlit_app.py` ###

import os
import streamlit as st
import pandas as pd
import time
import io
from dotenv import load_dotenv
from pathlib import Path

# Import ComplyAI modules
from src.utils import ensure_directories, get_available_standards
from src.extractor import DocumentExtractor
from src.comparator import ComplianceComparator
from src.gap_analyzer import GapAnalyzer
from src.chatbot import ComplianceChatbot
from src.suggestions import SuggestionGenerator

# Load environment variables
load_dotenv()

# Ensure necessary directories exist
ensure_directories()

# --- ADD THIS FUNCTION AT THE TOP (under imports) ---
def is_policy_like(text):
    policy_keywords = ["policy", "scope", "purpose", "compliance", "procedure", "audit", "access"]
    match_count = sum(1 for keyword in policy_keywords if keyword in text.lower())
    return match_count >= 3

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'extracted_chunks' not in st.session_state:
    st.session_state.extracted_chunks = []
if 'selected_standards' not in st.session_state:
    st.session_state.selected_standards = []
if 'gap_matrix' not in st.session_state:
    st.session_state.gap_matrix = None
if 'gap_summary' not in st.session_state:
    st.session_state.gap_summary = None
if 'chatbot_enabled' not in st.session_state:
    st.session_state.chatbot_enabled = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = {}
if 'priority_gaps' not in st.session_state:
    st.session_state.priority_gaps = None
if 'suggestions' not in st.session_state:
    st.session_state.suggestions = None

# Page title and description
st.title("ComplyAI - Policy Compliance Assistant")
st.markdown("""
Upload your organization's policy documents and analyze them against major compliance frameworks.
Get a detailed gap analysis and ask questions about your policies.
""")

# Create tabs for main UI sections
tab1, tab2 = st.tabs(["Document Analysis", "Compliance Chatbot"])

with tab1:
    st.header("Step 1: Upload Policy Documents")
    uploaded_files = st.file_uploader("Upload PDF policy documents", type="pdf", accept_multiple_files=True)

    if uploaded_files and st.button("Process Documents", key="process_docs"):
        with st.spinner("Processing documents..."):
            st.session_state.uploaded_files = []
            st.session_state.extracted_chunks = []
            st.session_state.gap_matrix = None
            st.session_state.gap_summary = None
            st.session_state.chatbot_enabled = False

            extractor = DocumentExtractor()
            extractor.reset_collection()

            total_chunks = 0
            for uploaded_file in uploaded_files:
                extracted_text = extractor.extract_text_from_pdf(uploaded_file)
                if not is_policy_like(extracted_text):
                    st.warning(f"'{uploaded_file.name}' does not appear to be a policy document. Skipping.")
                    continue

                try:
                    num_chunks = extractor.process_pdf(uploaded_file, uploaded_file.name)
                    st.session_state.uploaded_files.append({
                        "name": uploaded_file.name,
                        "size": uploaded_file.size,
                        "chunks": num_chunks
                    })
                    total_chunks += num_chunks
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")

            raw_chunks = extractor.collection.get(include=['documents', 'metadatas'])
            st.session_state.extracted_chunks = [
                {"text": doc, "metadata": meta}
                for doc, meta in zip(raw_chunks['documents'], raw_chunks['metadatas'])
            ]

        st.success(f"Processed {len(uploaded_files)} documents with {total_chunks} total chunks.")

    if st.session_state.uploaded_files:
        st.subheader("Processed Documents")
        for file in st.session_state.uploaded_files:
            st.write(f"📄 {file['name']} - {file['chunks']} chunks")

    st.header("Step 2: Select Compliance Standards")
    available_standards = get_available_standards()
    if not available_standards:
        st.error("No compliance standards found. Please check the compliance_db directory.")
    else:
        standard_options = {
            "iso_27001": "ISO 27001 - Information Security Management",
            "nist": "NIST 800-53 - Security Controls",
            "hipaa": "HIPAA - Health Insurance Portability and Accountability",
            "cjis": "CJIS - Criminal Justice Information Services",
            "pci": "PCI DSS - Payment Card Industry Data Security Standard"
        }
        selected_standards = []
        st.write("Select one or more compliance standards:")
        cols = st.columns(3)
        for i, standard in enumerate(available_standards):
            if standard in standard_options:
                if cols[i % 3].checkbox(standard_options[standard], key=f"std_{standard}"):
                    selected_standards.append(standard)
        st.session_state.selected_standards = selected_standards

    if (st.session_state.extracted_chunks and 
        st.session_state.selected_standards and 
        st.button("Run Compliance Analysis", key="run_analysis")):

        with st.spinner("Analyzing compliance standards..."):
            comparator = ComplianceComparator()
            gap_analyzer = GapAnalyzer()
            all_results = {}

            for standard in st.session_state.selected_standards:
                results = comparator.compare_chunks_to_standard(
                    st.session_state.extracted_chunks,
                    standard,
                    similarity_threshold=0.5
                )
                for control_id, result in results.items():
                    prefixed_id = f"{standard.upper()}_{control_id}"
                    all_results[prefixed_id] = result

            st.session_state.comparison_results = all_results
            gap_matrix = gap_analyzer.generate_gap_matrix(all_results)
            st.session_state.gap_matrix = gap_matrix
            st.session_state.gap_summary = gap_analyzer.generate_gap_summary(gap_matrix)
            st.session_state.priority_gaps = gap_analyzer.identify_priority_gaps(gap_matrix)
            suggestion_gen = SuggestionGenerator()
            st.session_state.suggestions = suggestion_gen.generate_suggestions_for_gaps(st.session_state.priority_gaps)
            st.session_state.chatbot_enabled = True

        st.success("Compliance analysis complete!")

    if st.session_state.gap_matrix is not None:
        st.header("Step 3: Compliance Gap Analysis")

        summary = st.session_state.gap_summary
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Controls", summary["total_controls"])
        col2.metric("Fully Addressed", summary["fully_addressed"])
        col3.metric("Partially Addressed", summary["partially_addressed"])
        col4.metric("Not Addressed", summary["not_addressed"] + summary["minimally_addressed"])

        st.subheader(f"Overall Compliance Rate: {summary['compliance_rate']}%")
        st.progress(summary['compliance_rate'] / 100)

        st.subheader("Gap Matrix")
        st.dataframe(st.session_state.gap_matrix)

        csv = st.session_state.gap_matrix.to_csv().encode('utf-8')
        st.download_button("Download Gap Matrix CSV", data=csv, file_name="compliance_gap_matrix.csv", mime="text/csv")

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            st.session_state.gap_matrix.to_excel(writer, index=False, sheet_name='Gap Analysis')
            writer.save()
            excel_data = excel_buffer.getvalue()

        st.download_button("Download Gap Matrix Excel", data=excel_data, file_name="compliance_gap_matrix.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if st.session_state.priority_gaps is not None:
            st.subheader("Priority Gaps to Address")
            if len(st.session_state.priority_gaps) > 0:
                for idx, row in st.session_state.suggestions.iterrows():
                    with st.expander(f"{row['Control ID']}: {row['Control Title']}"):
                        st.write(f"**Description:** {row['Description']}")
                        st.write(f"**Status:** {row['Status']}")
                        st.write(f"**Confidence Score:** {row['Confidence Score']}")
                        st.write(f"**Improvement Suggestion:** {row['Improvement Suggestion']}")
            else:
                st.write("No significant gaps found in your policies.")

with tab2:
    st.header("Compliance Chatbot")
    st.write("Ask questions about your policies and compliance requirements.")

    if not st.session_state.chatbot_enabled:
        st.info("Upload policy documents and run compliance analysis to enable the chatbot.")
    else:
        user_question = st.text_input("Ask a question about your policies:", key="user_question")

        if user_question and user_question.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            with st.spinner("Thinking..."):
                chatbot = ComplianceChatbot()
                response = chatbot.ask(user_question)
                st.session_state.chat_history.append({"role": "assistant", "content": response["answer"], "sources": response["sources"]})

        st.subheader("Conversation")
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.write(f"**You:** {message['content']}")
            else:
                st.write(f"**ComplyAI:** {message['content']}")
                if "sources" in message and message["sources"]:
                    with st.expander("View Sources"):
                        for i, source in enumerate(message["sources"]):
                            st.markdown(f"**Source {i+1}:**")
                            st.write(source["text"])
                            st.write(f"*From: {source['metadata'].get('filename', 'Unknown')}*")
                            st.write("---")

        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.experimental_rerun()

st.markdown("---")
st.markdown("ComplyAI - Helping organizations achieve compliance with AI-powered analysis.")

if __name__ == "__main__":
    pass