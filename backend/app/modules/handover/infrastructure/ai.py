"""问题与经验命令使用的结构化模型适配。"""


def json_model(model, settings):
    if settings.protocol != "openai" or "deepseek" not in settings.model.casefold():
        return model
    if not hasattr(model, "bind"):
        return model
    # 仅约束问题与经验的结构化录入请求。
    # DeepSeek 默认开启思考；摘要用非思考 JSON 模式，避免推理耗尽输出预算。
    return model.bind(
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}},
    )
