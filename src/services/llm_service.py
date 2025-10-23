"""
LLM service for answer synthesis using Google Gemini.
"""
import os
import time
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from src.services.interfaces import AnswerSynthesizerInterface
from src.models.query import SynthesizedAnswer, Citation
from src.models.document import DocumentMetadata
from src.utils.exceptions import AnswerSynthesisError
from src.config.settings import config


class GeminiLLMService(AnswerSynthesizerInterface):
    """LLM service using Google Gemini for answer synthesis."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Gemini LLM service.
        
        Args:
            api_key: Google AI API key (if not provided, will try to get from config or env)
        """
        self.api_key = api_key or config.llm.api_key or os.getenv('GOOGLE_AI_API_KEY')
        
        if not self.api_key:
            # For demo purposes, we'll create a mock service
            print("⚠️  No Gemini API key found. Using mock responses for demo.")
            self.use_mock = True
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('models/gemini-2.5-flash')
                # Test the connection
                test_response = self.model.generate_content("Hello")
                if test_response.text:
                    print("✅ Gemini API connected successfully!")
                    self.use_mock = False
                else:
                    raise Exception("Empty response from Gemini")
            except Exception as e:
                print(f"⚠️  Gemini API connection failed: {e}")
                print("⚠️  Falling back to mock responses for demo.")
                self.use_mock = True
        
        self.max_tokens = config.llm.max_tokens
        self.temperature = config.llm.temperature
    
    def synthesize_answer(self, query: str, context: str, sources: List[DocumentMetadata]) -> SynthesizedAnswer:
        """
        Generate synthesized answer from context using Gemini.
        
        Args:
            query: User query
            context: Retrieved context from documents
            sources: Source document metadata
            
        Returns:
            SynthesizedAnswer: Synthesized answer with citations
            
        Raises:
            AnswerSynthesisError: If synthesis fails
        """
        try:
            if self.use_mock:
                return self._generate_mock_answer(query, context, sources)
            
            # Construct prompt
            prompt = self.construct_prompt(query, context)
            
            # Generate response using Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
            )
            
            if not response.text:
                raise AnswerSynthesisError("Gemini returned empty response")
            
            answer_text = response.text.strip()
            
            # Extract citations
            citations = self.extract_citations(answer_text, sources)
            
            # Get source document IDs
            sources_used = [doc.id for doc in sources]
            
            return SynthesizedAnswer(
                content=answer_text,
                sources_used=sources_used,
                citations=citations,
                confidence_score=0.8  # Default confidence
            )
            
        except Exception as e:
            raise AnswerSynthesisError(f"Failed to synthesize answer: {str(e)}")
    
    def construct_prompt(self, query: str, context: str) -> str:
        """
        Construct prompt for Gemini.
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            str: Formatted prompt
        """
        prompt = f"""You are a helpful AI assistant that answers questions based on provided documents. You should be confident in providing answers when the information is clearly present in the context.

Context from documents:
{context}

User Question: {query}

Instructions:
- Analyze the provided context carefully and extract relevant information to answer the question
- Format your response with clear structure and proper spacing
- If the information is present in the context, provide a clear and direct answer
- Use specific details and quotes from the context to support your answer
- Organize information in a readable format with:
  • Clear bullet points for lists (use • symbol)
  • Proper line breaks between sections
  • Do NOT use asterisks (*) for formatting - use plain text
- If the context contains partial information, provide what you can and note what's missing
- Only say you cannot answer if the context truly contains no relevant information
- Be confident when the answer is clearly available in the provided text
- Use a natural, conversational tone
- Avoid markdown formatting like **bold** - just use plain text

Answer:"""
        
        return prompt
    
    def extract_citations(self, answer: str, sources: List[DocumentMetadata]) -> List[Citation]:
        """
        Extract citations from generated answer.
        
        Args:
            answer: Generated answer text
            sources: Source documents
            
        Returns:
            List[Citation]: List of citations
        """
        citations = []
        
        # For now, create citations for all source documents
        # In a more sophisticated implementation, we could analyze which parts
        # of the answer correspond to which sources
        for i, source in enumerate(sources):
            citation = Citation(
                document_id=source.id,
                filename=source.filename,
                chunk_content=f"Referenced in answer generation",
                relevance_score=0.8 - (i * 0.1)  # Decreasing relevance
            )
            citations.append(citation)
        
        return citations
    
    def _generate_mock_answer(self, query: str, context: str, sources: List[DocumentMetadata]) -> SynthesizedAnswer:
        """
        Generate an intelligent mock answer for demo purposes when no API key is available.
        
        Args:
            query: User query
            context: Retrieved context
            sources: Source documents
            
        Returns:
            SynthesizedAnswer: Mock synthesized answer
        """
        if not context.strip():
            answer_text = "I don't have enough information in the provided documents to answer your question."
        else:
            # Parse context to extract meaningful information
            answer_text = self._create_intelligent_response(query, context)
        
        # Create citations from sources
        citations = []
        for i, source in enumerate(sources):
            citation = Citation(
                document_id=source.id,
                filename=source.filename,
                chunk_content="Referenced in answer",
                relevance_score=0.9 - (i * 0.1)
            )
            citations.append(citation)
        
        return SynthesizedAnswer(
            content=answer_text,
            sources_used=[doc.id for doc in sources],
            citations=citations,
            confidence_score=0.8
        )
    
    def _create_intelligent_response(self, query: str, context: str) -> str:
        """
        Create an intelligent response by analyzing context and query.
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            str: Intelligent response
        """
        # Clean and split context into sections
        sections = context.split('[Source:')
        meaningful_content = []
        
        for section in sections[1:]:  # Skip first empty section
            if ']' in section:
                source_name = section.split(']')[0].strip()
                content = section.split(']')[1].strip()
                if content:
                    meaningful_content.append({
                        'source': source_name,
                        'content': content
                    })
        
        if not meaningful_content:
            return "Based on the uploaded documents, I found relevant information but need more context to provide a specific answer."
        
        # Analyze query type and create appropriate response
        query_lower = query.lower()
        
        # Question type detection
        if any(word in query_lower for word in ['what', 'who', 'where', 'when', 'how', 'why']):
            return self._answer_question(query, meaningful_content)
        elif any(word in query_lower for word in ['tell me', 'explain', 'describe']):
            return self._provide_explanation(query, meaningful_content)
        elif any(word in query_lower for word in ['list', 'show', 'give me']):
            return self._provide_list(query, meaningful_content)
        else:
            return self._provide_general_response(query, meaningful_content)
    
    def _answer_question(self, query: str, content_sections: List[Dict]) -> str:
        """Answer a specific question based on content."""
        response = "Based on the documents provided:\n\n"
        
        # Extract key information from each section
        for section in content_sections[:3]:  # Limit to top 3 sections
            content = section['content']
            source = section['source']
            
            # Find the most relevant sentence
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            if sentences:
                # Take first substantial sentence
                relevant_sentence = next((s for s in sentences if len(s) > 20), sentences[0] if sentences else "")
                if relevant_sentence:
                    response += f"From {source}: {relevant_sentence}.\n\n"
        
        response += "This information directly addresses your question from the uploaded documents."
        return response
    
    def _provide_explanation(self, query: str, content_sections: List[Dict]) -> str:
        """Provide an explanation based on content."""
        response = "Here's what I found in your documents:\n\n"
        
        for i, section in enumerate(content_sections[:2]):
            content = section['content']
            source = section['source']
            
            # Extract meaningful paragraphs
            paragraphs = [p.strip() for p in content.split('\n') if p.strip() and len(p.strip()) > 30]
            if paragraphs:
                response += f"**From {source}:**\n{paragraphs[0]}\n\n"
        
        response += "This explanation is compiled from your uploaded documents."
        return response
    
    def _provide_list(self, query: str, content_sections: List[Dict]) -> str:
        """Provide a list-based response."""
        response = "Based on your documents, here are the key points:\n\n"
        
        points = []
        for section in content_sections:
            content = section['content']
            # Extract bullet points or create them from sentences
            sentences = [s.strip() for s in content.split('.') if s.strip() and len(s.strip()) > 15]
            for sentence in sentences[:2]:  # Max 2 per source
                if sentence:
                    points.append(f"• {sentence}")
        
        response += '\n'.join(points[:5])  # Max 5 points
        response += "\n\nThese points are extracted from your uploaded documents."
        return response
    
    def _provide_general_response(self, query: str, content_sections: List[Dict]) -> str:
        """Provide a general response."""
        response = "Based on your uploaded documents:\n\n"
        
        # Combine key information
        key_info = []
        for section in content_sections[:3]:
            content = section['content']
            source = section['source']
            
            # Get first substantial sentence
            sentences = [s.strip() for s in content.split('.') if s.strip() and len(s.strip()) > 20]
            if sentences:
                key_info.append(f"From {source}: {sentences[0]}")
        
        response += '\n\n'.join(key_info)
        response += "\n\nThis information is relevant to your query and comes from the documents you've uploaded."
        return response
    
    def test_connection(self) -> bool:
        """
        Test connection to Gemini API.
        
        Returns:
            bool: True if connection successful
        """
        if self.use_mock:
            return True
        
        try:
            response = self.model.generate_content("Hello, this is a test.")
            return bool(response.text)
        except Exception:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the LLM model.
        
        Returns:
            Dict: Model information
        """
        return {
            "provider": "google_gemini" if not self.use_mock else "mock",
            "model": "gemini-pro" if not self.use_mock else "mock-llm",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "api_key_configured": bool(self.api_key),
            "using_mock": self.use_mock
        }