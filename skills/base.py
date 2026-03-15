"""Base class for all Jarvis skills."""


class Skill:
    """A skill that the LLM can invoke via tool calling.

    Subclasses must set name, description, and parameters,
    and implement execute().
    """

    name: str = ""
    description: str = ""
    parameters: dict = {}  # JSON Schema for arguments

    def execute(self, **kwargs) -> str:
        """Run the skill and return a text result for the LLM."""
        raise NotImplementedError
