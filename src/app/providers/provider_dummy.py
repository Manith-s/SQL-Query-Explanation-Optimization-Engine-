"""
Dummy LLM provider that returns deterministic responses.

This provider is useful for testing and development when a real LLM
is not needed or available.
"""

from typing import Optional, Dict, Any, List
import os
from app.core.llm_adapter import LLMProvider

_TEMPLATES: Dict[str, str] | None = None

def _load_templates() -> Dict[str, str]:
    global _TEMPLATES
    if _TEMPLATES is not None:
        return _TEMPLATES
    tmpl: Dict[str, str] = {}
    try:
        base = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(base, "resources", "nl_templates.yaml")
        if os.path.exists(path):
            for line in open(path, "r", encoding="utf-8"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    tmpl[k.strip()] = v.strip().strip('"')
    except Exception:
        tmpl = {}
    _TEMPLATES = tmpl
    return tmpl

def _walk_plan_nodes(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    if not isinstance(plan, dict):
        return nodes
    root = plan.get("Plan", plan)
    def _rec(n: Dict[str, Any]):
        nodes.append(n)
        for ch in (n.get("Plans") or []):
            if isinstance(ch, dict):
                _rec(ch)
    if isinstance(root, dict):
        _rec(root)
    return nodes

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
        # Template-driven fallback if resources are available
        try:
            templates = _load_templates()
            if templates:
                lines: List[str] = []
                for k, msg in templates.items():
                    if k.lower() in prompt.lower():
                        lines.append(f"- {msg}")
                if lines:
                    return "\n".join(["Plan overview:"] + lines)
        except Exception:
            pass
        # Deterministic simple fallbacks
        words = len(prompt.split())
        if words < 20:
            return "Simple plan with minimal cost; no major issues detected."
        if words < 60:
            return "Mixed scans and joins observed; consider indexing join/filter columns for frequent queries."
        return "Complex plan with multiple joins and sorts; adding appropriate indexes and pushing down filters may help."

    def is_available(self) -> bool:  # compat for structure tests
        return True

    def generate(self, prompt: str) -> str:  # compat shim
        return self.complete(prompt)