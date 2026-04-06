"""Extract and process text from PDF documents."""

import os
import pdfplumber
import PyPDF2
from typing import List, Dict, Any, Optional
import tempfile
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chromadb.config import Settings
import chromadb
import hashlib
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DocumentExtractor:
    def __init__(self, 
                 chunk_size: int = int(os.getenv("CHUNK_SIZE", "500")),
                 chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))):
        """Initialize the document extractor.
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        # Initialize embedding model
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        # Initialize Chroma client
        self.chroma_client = chromadb.PersistentClient(
            path="chroma_db",
            settings=Settings(allow_reset=True)
        )
        
        # Create or get collection
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name="policy_documents",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            # Reset if there's an issue with the existing collection
            self.chroma_client.reset()
            self.collection = self.chroma_client.get_or_create_collection(
                name="policy_documents",
                metadata={"hnsw:space": "cosine"}
            )

    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from a PDF file.
        
        Args:
            pdf_file: PDF file object (from Streamlit)
            
        Returns:
            Extracted text from the PDF
        """
        # Save temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(pdf_file.getvalue())
            temp_path = temp_file.name
        
        try:
            # Extract text using pdfplumber
            all_text = ""
            with pdfplumber.open(temp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    all_text += text + "\n\n"
            
            # Fallback to PyPDF2 if pdfplumber extracts no text
            if not all_text.strip():
                with open(temp_path, "rb") as file:
                    reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(reader.pages)):
                        text = reader.pages[page_num].extract_text() or ""
                        all_text += text + "\n\n"
                        
            return all_text
        finally:
            # Remove temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into chunks.
        
        Args:
            text: Text to split
            metadata: Metadata for the document
            
        Returns:
            List of chunks with metadata
        """
        texts = self.text_splitter.split_text(text)
        
        # Create chunks with metadata
        chunks = []
        for i, chunk_text in enumerate(texts):
            chunk = {
                "text": chunk_text,
                "metadata": {
                    "chunk_id": i,
                    **(metadata or {})
                }
            }
            chunks.append(chunk)
            
        return chunks

    def get_document_hash(self, text: str) -> str:
        """Create a hash for document text to use as ID.
        
        Args:
            text: Document text
            
        Returns:
            Hash string
        """
        return hashlib.md5(text.encode()).hexdigest()

    def process_pdf(self, pdf_file, filename: str) -> int:
        """Process a PDF file: extract text, chunk, and store in Chroma.
        
        Args:
            pdf_file: PDF file object
            filename: Name of the PDF file
            
        Returns:
            Number of chunks stored
        """
        # Extract text
        text = self.extract_text_from_pdf(pdf_file)
        
        # Skip if no text was extracted
        if not text or len(text.strip()) < 50:
            raise ValueError(f"Could not extract sufficient text from {filename}")
        
        # Create document metadata
        doc_id = self.get_document_hash(text)
        metadata = {
            "filename": filename,
            "doc_id": doc_id,
            "source": "uploaded_pdf"
        }
        
        # Chunk the text
        chunks = self.chunk_text(text, metadata)
        
        # Store chunks in Chroma
        for chunk in chunks:
            # Create embeddings using sentence transformers
            embedding = self.embedding_model.encode(chunk["text"])
            
            # Create unique ID for chunk
            chunk_id = f"{doc_id}_{chunk['metadata']['chunk_id']}"
            
            # Add to collection
            self.collection.add(
                ids=[chunk_id],
                embeddings=[embedding.tolist()],
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]]
            )
        
        return len(chunks)

    def get_relevant_chunks(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Get chunks relevant to a query.
        
        Args:
            query: Query text
            n_results: Number of results to return
            
        Returns:
            List of relevant chunks
        """
        # Create embedding for query
        query_embedding = self.embedding_model.encode(query)
        
        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results
        )
        
        # Format the results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i]
            })
            
        return formatted_results

    def reset_collection(self):
        """Reset the Chroma collection."""
        try:
            self.chroma_client.delete_collection("policy_documents")
        except:
            pass
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="policy_documents",
            metadata={"hnsw:space": "cosine"}
        )