"""
Dummy LLM provider that returns deterministic responses.

This provider is useful for testing and development when a real LLM
is not needed or available.
"""

from typing import Optional
from app.core.llm_adapter import LLMProvider

class DummyLLMProvider(LLMProvider):
    """
    Dummy LLM provider that returns fixed responses based on input length.
    Useful for testing and development.
    """
    
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Return a deterministic response based on prompt characteristics.
        
        Args:
            prompt: The input prompt
            system: Optional system context (ignored in dummy provider)
        
        Returns:
            A fixed response that roughly matches the expected format
        """
        # Use prompt length to determine response type (for variety in testing)
        words = len(prompt.split())
        
        if "SELECT" not in prompt and "CREATE" not in prompt:
            return (
                "I can only explain SQL queries. The input doesn't appear to "
                "contain a SQL statement."
            )
        
        if words < 10:
            return (
                "This is a simple query that retrieves data from the database. "
                "The execution plan is straightforward with no major performance concerns."
            )
            
        if words < 30:
            return (
                "This query joins multiple tables to aggregate data. The execution "
                "plan shows a mix of sequential and index scans. Consider adding an "
                "index if this query runs frequently. The estimated row count suggests "
                "moderate data volume."
            )
            
        # Long/complex query
        return (
            "This is a complex query involving multiple joins and subqueries. "
            "The execution plan reveals several potential optimization opportunities:\n"
            "1. Consider adding an index on the join columns\n"
            "2. The nested loop join might benefit from a hash join instead\n"
            "3. Some predicates could be pushed down for better filtering\n\n"
            "The query processes a significant amount of data, so these optimizations "
            "could improve performance substantially."
        )

    def is_available(self) -> bool:  # compat for structure tests
        return True

    def generate(self, prompt: str) -> str:  # compat shim
        return self.complete(prompt)