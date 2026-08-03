import os

from jinja2 import Environment
from pydantic import TypeAdapter
import yaml

from messages.filters import ALL_FILTERS
from messages.schemas import Message


TEMPLATES_DIR = 'messages/templates'
TEMPLATES: dict[str, dict[str, Message]] = {}

for template_file in os.listdir(TEMPLATES_DIR):
    if template_file.endswith('.yml'):
        with open(os.path.join(TEMPLATES_DIR, template_file), 'r', encoding='utf-8') as f:
            messages_data = yaml.safe_load(f)
            TEMPLATES[template_file[:-4]] = TypeAdapter(dict[str, Message]).validate_python(messages_data)
            


class MessageRenderer:
    def __init__(self, language: str):
        self.language = language
        self.env = Environment()
        self.env.filters.update({f.__name__: f for f in ALL_FILTERS})

    def render(self, key: str, **kwargs) -> dict[str, str | None]:
        message = TEMPLATES.get(self.language, {}).get(key)
        if not message:
            raise ValueError(f"Message not found for key: {key}")
        template = self.env.from_string(message.template)
        return {
            'text': template.render(**kwargs),
            'parse_mode': 'MarkdownV2' if message.markdown else None
        }
