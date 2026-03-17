from openai import OpenAI
from core.config import Config


class QwenClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.QWEN_API_KEY,
            base_url=Config.QWEN_BASE_URL,
        )

    def chat(self, messages, model=None, enable_search=False):
        extra_body = {}
        if enable_search:
            extra_body = {
                "enable_search": True,
                "search_options": {"search_strategy": "turbo"},
            }
        response = self.client.chat.completions.create(
            model=model or Config.FACT_CHECK_MODEL,
            messages=messages,
            temperature=0.7,
            extra_body=extra_body,
        )
        return response.choices[0].message.content

    def search(self, query):
        return self.chat([{"role": "user", "content": query}], enable_search=True)


def create_client():
    return QwenClient()
