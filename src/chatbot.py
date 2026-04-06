"""RAG-based chatbot for policy documents."""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Chroma
import chromadb
from chromadb.config import Settings

# Load environment variables
load_dotenv()

class ComplianceChatbot:
    def __init__(self):
        """Initialize the compliance chatbot."""
        # Initialize the LLM
            
        self.llm = Ollama(
            model="llama2",  # You can also try "mistral", "deepseek-coder", etc.
            temperature=0.3,
            base_url="http://localhost:11434"  # default Ollama local API port
        )
        
        # Connect to Chroma
        self.chroma_client = chromadb.PersistentClient(
            path="chroma_db",
            settings=Settings(allow_reset=True)
        )
        
        try:
            self.collection = self.chroma_client.get_collection("policy_documents")
        except:
            # Collection doesn't exist yet
            self.collection = None
            
        # Initialize the retriever
        if self.collection:
            self.retriever = Chroma(
                collection_name="policy_documents",
                collection=self.collection,
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            # Create the QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.retriever,
                return_source_documents=True
            )
        else:
            self.retriever = None
            self.qa_chain = None
            
    def _format_query(self, question: str) -> str:
        """Format the question for the LLM.
        
        Args:
            question: User's question
            
        Returns:
            Formatted query
        """
        return f"""You are an AI compliance assistant. Answer the following question based ONLY on the context provided.
If you don't know the answer based on the context, say "I don't have enough information to answer that question."
Do not make up information. If the question is not about compliance or organizational policies, politely redirect the conversation.

Question: {question}"""
    
    def ask(self, question: str) -> Dict[str, Any]:
        """Ask a question to the chatbot.
        
        Args:
            question: User's question
            
        Returns:
            Dictionary with answer and sources
        """
        # Check if the QA chain is initialized
        if not self.qa_chain or not self.collection:
            return {
                "answer": "I can't answer questions yet. Please upload policy documents first.",
                "sources": []
            }
            
        # Format the query
        formatted_query = self._format_query(question)
        
        # Get the answer
        try:
            result = self.qa_chain({"query": formatted_query})
            
            # Extract sources
            sources = []
            if "source_documents" in result:
                for doc in result["source_documents"]:
                    source = {
                        "text": doc.page_content,
                        "metadata": doc.metadata
                    }
                    sources.append(source)
            
            return {
                "answer": result["result"],
                "sources": sources
            }
        except Exception as e:
            return {
                "answer": f"I encountered an error while trying to answer your question: {str(e)}",
                "sources": []
            }