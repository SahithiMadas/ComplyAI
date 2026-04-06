"""Compare policies to compliance controls."""

import os
from typing import List, Dict, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from .utils import load_compliance_standard

# Load environment variables
load_dotenv()

class ComplianceComparator:
    def __init__(self, embedding_model_name=None):
        """Initialize the compliance comparator.
        
        Args:
            embedding_model_name: Name of the embedding model to use
        """
        self.embedding_model_name = embedding_model_name or os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
    def load_standard(self, standard_name: str) -> List[Dict[str, Any]]:
        """Load a compliance standard.
        
        Args:
            standard_name: Name of the standard (e.g., 'iso_27001')
            
        Returns:
            List of controls for the specified standard
        """
        return load_compliance_standard(standard_name)
    
    def embed_controls(self, controls: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        """Create embeddings for compliance controls.
        
        Args:
            controls: List of control dictionaries
            
        Returns:
            Dictionary mapping control IDs to embeddings
        """
        control_embeddings = {}
        
        for control in controls:
            # Create a consolidated text representation of the control
            control_text = f"{control['id']}: {control['title']}\n{control['description']}"
            
            # Create the embedding
            embedding = self.embedding_model.encode(control_text)
            
            # Store the embedding with the control ID
            control_embeddings[control['id']] = embedding
            
        return control_embeddings
    
    def compute_similarity(self, chunk: Dict[str, Any], control_embeddings: Dict[str, np.ndarray]) -> List[Tuple[str, float]]:
        """Compute similarity between a chunk and all controls.
        
        Args:
            chunk: Text chunk from document
            control_embeddings: Dictionary of control embeddings
            
        Returns:
            List of (control_id, similarity_score) tuples, sorted by score
        """
        # Create chunk embedding
        chunk_embedding = self.embedding_model.encode(chunk['text'])
        
        # Compute similarities
        similarities = []
        for control_id, control_embedding in control_embeddings.items():
            # Reshape embeddings for cosine_similarity
            chunk_emb_reshaped = chunk_embedding.reshape(1, -1)
            control_emb_reshaped = control_embedding.reshape(1, -1)
            
            # Compute cosine similarity
            similarity = cosine_similarity(chunk_emb_reshaped, control_emb_reshaped)[0][0]
            
            similarities.append((control_id, similarity))
        
        # Sort by similarity score in descending order
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities
    
    def compare_chunks_to_standard(self, 
                                   chunks: List[Dict[str, Any]], 
                                   standard_name: str, 
                                   similarity_threshold: float = 0.5) -> Dict[str, Dict[str, Any]]:
        """Compare all chunks to a compliance standard.
        
        Args:
            chunks: List of document chunks
            standard_name: Name of the compliance standard
            similarity_threshold: Minimum similarity score to consider a match
            
        Returns:
            Dictionary mapping control IDs to their best matching chunks
        """
        # Load standard
        controls = self.load_standard(standard_name)
        
        # Create control embeddings
        control_embeddings = self.embed_controls(controls)
        
        # Initialize results dictionary
        results = {}
        
        # Initialize with all controls
        for control in controls:
            results[control['id']] = {
                'control': control,
                'best_match': None,
                'score': 0.0,
                'status': 'Not Addressed'
            }
        
        # Compare each chunk to all controls
        for chunk in chunks:
            similarities = self.compute_similarity(chunk, control_embeddings)
            
            # Update results with the best matches
            for control_id, score in similarities:
                if score < similarity_threshold:
                    continue
                    
                if control_id not in results or score > results[control_id]['score']:
                    results[control_id]['best_match'] = chunk
                    results[control_id]['score'] = score
                    
                    # Determine status based on score
                    if score >= 0.8:
                        results[control_id]['status'] = 'Fully Addressed'
                    elif score >= 0.6:
                        results[control_id]['status'] = 'Partially Addressed'
                    elif score >= similarity_threshold:
                        results[control_id]['status'] = 'Minimally Addressed'
        
        return results