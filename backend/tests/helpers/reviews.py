"""只替换外部复核模型，记录它实际收到的结构化资料。"""

import json

from langchain_core.messages import AIMessage


class CapturingReviewer:
    def __init__(self):
        self.requests = []

    async def ainvoke(self, messages, **_kwargs):
        self.requests.append(json.loads(messages[-1].text))
        return AIMessage(content='{"verdict":"passed","issues":[]}')
