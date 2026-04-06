"""Generate improvement suggestions for compliance gaps using Ollama."""

from typing import List, Dict, Any
import pandas as pd
from langchain_community.llms import Ollama

class SuggestionGenerator:
    def __init__(self):
        """Initialize the suggestion generator with LLaMA via Ollama."""
        self.llm = Ollama(
            model="llama2",              # Change to "mistral" or "deepseek-coder" if needed
            temperature=0.2,
            base_url="http://localhost:11434"
        )

    def generate_suggestion(self, control: Dict[str, Any]) -> str:
        """Generate a practical suggestion to address a compliance control gap.
        
        Args:
            control: Row dict from the gap matrix

        Returns:
            Suggestion string
        """
        prompt = f"""You are an expert in cybersecurity and compliance.
Given the following control that is not fully addressed in an organization's policies, provide a short and actionable recommendation for improvement.

Control ID: {control['Control ID']}
Control Title: {control['Control Title']}
Description: {control['Description']}
Current Status: {control['Status']}

Your suggestion:"""

        try:
            return self.llm.predict(prompt).strip()
        except Exception as e:
            return f"⚠️ Could not generate suggestion: {str(e)}"

    def generate_suggestions_for_gaps(self, gap_matrix: pd.DataFrame) -> pd.DataFrame:
        """Add suggestions to the gap matrix for under-addressed controls."""
        df = gap_matrix.copy()
        df['Improvement Suggestion'] = None

        for idx, row in df.iterrows():
            if row['Status'] in ['Not Addressed', 'Minimally Addressed', 'Partially Addressed']:
                suggestion = self.generate_suggestion(row)
                df.at[idx, 'Improvement Suggestion'] = suggestion
            else:
                df.at[idx, 'Improvement Suggestion'] = "✅ Control is adequately addressed."

        return df
