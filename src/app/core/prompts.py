"""LLM prompting templates and helpers for SQL explanation."""
SYSTEM_PROMPT = "You are an expert PostgreSQL database engineer explaining SQL queries."
def explain_template(sql: str, ast=None, plan=None, warnings=None, metrics=None, audience="practitioner", style="concise", length="short", max_length=2000):
    """Generate a simple prompt for explaining a SQL query."""
    return f"Explain this SQL query in one sentence: {sql}"
