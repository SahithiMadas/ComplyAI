"""Generate gap analysis matrix and reports."""

from typing import Dict, List, Any, Optional
import pandas as pd
from .utils import save_report

class GapAnalyzer:
    def __init__(self):
        """Initialize the gap analyzer."""
        pass
    
    def generate_gap_matrix(self, comparison_results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """Generate a gap analysis matrix from comparison results.
        
        Args:
            comparison_results: Results from the compliance comparison
            
        Returns:
            DataFrame containing the gap matrix
        """
        # Prepare data for the gap matrix
        gap_data = []
        
        for control_id, result in comparison_results.items():
            control = result['control']
            
            row = {
                'Control ID': control_id,
                'Control Title': control['title'],
                'Description': control['description'],
                'Status': result['status'],
                'Confidence Score': round(result['score'], 2),
                'Evidence': result['best_match']['text'][:200] + '...' if result['best_match'] else 'No evidence found',
                'Source Document': result['best_match']['metadata']['filename'] if result['best_match'] else 'N/A',
            }
            
            gap_data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(gap_data)
        
        # Sort by Control ID
        df = df.sort_values('Control ID')
        
        return df
    
    def generate_gap_summary(self, gap_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Generate a summary of the gap analysis.
        
        Args:
            gap_matrix: Gap analysis matrix
            
        Returns:
            Dictionary with summary statistics
        """
        # Count statuses
        status_counts = gap_matrix['Status'].value_counts()
        
        # Prepare summary
        summary = {
            'total_controls': len(gap_matrix),
            'fully_addressed': status_counts.get('Fully Addressed', 0),
            'partially_addressed': status_counts.get('Partially Addressed', 0),
            'minimally_addressed': status_counts.get('Minimally Addressed', 0),
            'not_addressed': status_counts.get('Not Addressed', 0),
            'compliance_rate': round((
                status_counts.get('Fully Addressed', 0) + 
                status_counts.get('Partially Addressed', 0) * 0.5 + 
                status_counts.get('Minimally Addressed', 0) * 0.25
            ) / len(gap_matrix) * 100, 1)
        }
        
        return summary
    
    def save_gap_matrix(self, gap_matrix: pd.DataFrame, filename: str = "gap_matrix.csv") -> str:
        """Save the gap matrix to a CSV file.
        
        Args:
            gap_matrix: Gap analysis matrix
            filename: Name of the output file
            
        Returns:
            Path to the saved file
        """
        output_path = save_report(gap_matrix, filename)
        return str(output_path)
    
    def identify_priority_gaps(self, gap_matrix: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
        """Identify priority gaps to address.
        
        Args:
            gap_matrix: Gap analysis matrix
            top_n: Number of priority gaps to identify
            
        Returns:
            DataFrame with priority gaps
        """
        # Filter for not addressed or minimally addressed controls
        priority_gaps = gap_matrix[
            (gap_matrix['Status'] == 'Not Addressed') | 
            (gap_matrix['Status'] == 'Minimally Addressed')
        ]
        
        # Sort by status (Not Addressed first) and then by Control ID
        priority_gaps = priority_gaps.sort_values(['Status', 'Control ID'])
        
        # Return top N gaps
        return priority_gaps.head(top_n)