"""
Base LLM interface
"""

from abc import ABC, abstractmethod

class LLMInterface(ABC):
    """Abstract base class for LLM interfaces"""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: any) -> str:
        """Generate text from a prompt"""
        pass
