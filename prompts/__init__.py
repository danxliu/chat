import jinja2
from .starting import STARTING_PROMPT_TEMPLATE, IMPORTANT_INSTRUCTIONS
from .resuming import RESUMING_PROMPT_TEMPLATE
from .summarizer import SUMMARIZER_PROMPT_TEMPLATE, TITLE_SUMMARIZER_PROMPT_TEMPLATE

class RichPromptTemplate:
    """A simple compatibility layer for RichPromptTemplate using Jinja2."""
    def __init__(self, template: str):
        self.template = jinja2.Template(template)
    
    def format(self, **kwargs) -> str:
        return self.template.render(**kwargs)

__all__ = [
    "STARTING_PROMPT_TEMPLATE", 
    "IMPORTANT_INSTRUCTIONS",
    "RESUMING_PROMPT_TEMPLATE", 
    "SUMMARIZER_PROMPT_TEMPLATE",
    "TITLE_SUMMARIZER_PROMPT_TEMPLATE",
    "RichPromptTemplate"
]
