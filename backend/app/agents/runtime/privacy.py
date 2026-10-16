"""供应商边界的常见密钥脱敏；保留行号，源码原件和本地差异不被改写。"""

import json
import re

SECRET_KEYS = {
    "apikey",
    "accesstoken",
    "refreshtoken",
    "password",
    "pwd",
    "clientsecret",
    "secretkey",
    "authorization",
    "privatekey",
    "accesskey",
    "secretaccesskey",
}
MASK = "[敏感值已隐藏]"
KEY_PATTERN = (
    r"(?:[A-Za-z][A-Za-z0-9_]*[_-])?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|pwd|"
    r"client[_-]?secret|secret[_-]?key|authorization|private[_-]?key|"
    r"access[_-]?key|secret[_-]?access[_-]?key)"
)
ASSIGNMENT = re.compile(
    rf"(?i)(\b(?:{KEY_PATTERN})\b[\"']?\s*[:=]\s*)([\"'])((?:\\.|(?!\2)[^\r\n\\])*)\2"
)
UNQUOTED_ASSIGNMENT = re.compile(rf"(?im)(\b(?:{KEY_PATTERN})\b\s*=\s*)(?![\"'])([^\r\n;\s]+)")
CONNECTION_PASSWORD = re.compile(r"(?i)(\b(?:password|pwd)\s*=\s*)([^;\s\"']+)")
BEARER = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/-]+")
PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----.*?-----END (?:[A-Z ]+ )?PRIVATE KEY-----", re.S
)
JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
XML_VALUE = re.compile(
    rf"(?i)(<(?:add|setting)\b[^>]*\b(?:key|name)\s*=\s*[\"'](?:{KEY_PATTERN})[\"']"
    r"[^>]*\bvalue\s*=\s*)([\"'])(.*?)\2"
)
XML_ELEMENT = re.compile(rf"(?is)(<(?:{KEY_PATTERN})\s*>)(.*?)(</(?:{KEY_PATTERN})\s*>)")


def normalized_key(value):
    return re.sub(r"[^a-z]", "", str(value).casefold())


def is_secret_key(value):
    normalized = normalized_key(value)
    return any(normalized.endswith(name) for name in SECRET_KEYS)


def mask_lines(value):
    """CRLF、LF 和空行均保持原位，引用仍指向原文件的同一行。"""
    return re.sub(r"[^\r\n]+", MASK, value) if value else MASK


def _plain_text(value):
    value = PRIVATE_KEY.sub(lambda match: mask_lines(match[0]), value)
    value = XML_VALUE.sub(lambda match: match[1] + match[2] + MASK + match[2], value)
    value = XML_ELEMENT.sub(lambda match: match[1] + mask_lines(match[2]) + match[3], value)
    value = ASSIGNMENT.sub(lambda match: match[1] + match[2] + MASK + match[2], value)
    value = UNQUOTED_ASSIGNMENT.sub(lambda match: match[1] + MASK, value)
    value = CONNECTION_PASSWORD.sub(lambda match: match[1] + MASK, value)
    return BEARER.sub(lambda match: match[1] + MASK, value)


def _json_text(value, depth):
    try:
        json.loads(value)
    except (ValueError, RecursionError):
        return None
    # 只替换发生脱敏的词法片段；不得重序列化整份 JSON 并改变源码排版与行号。
    decoder, pieces, cursor = json.JSONDecoder(), [], 0
    for token in JSON_STRING.finditer(value):
        if token.start() < cursor:
            continue
        text = json.loads(token[0])
        after = token.end()
        while after < len(value) and value[after].isspace():
            after += 1
        if after < len(value) and value[after] == ":":
            if not is_secret_key(text):
                continue
            start = after + 1
            while start < len(value) and value[start].isspace():
                start += 1
            child, end = decoder.raw_decode(value, start)
            if child is None or child == "":
                continue
            replacement = json.dumps(mask_lines(child) if isinstance(child, str) else MASK)
            # 对象型敏感值整体隐藏时，也保留原有的实际换行。
            replacement += "".join(re.findall(r"\r\n|\r|\n", value[start:end]))
        else:
            child = redact(text, depth=depth + 1)
            if child == text:
                continue
            start, end = token.span()
            replacement = json.dumps(child, ensure_ascii=False)
        pieces.extend((value[cursor:start], replacement))
        cursor = end
    return "".join((*pieces, value[cursor:]))


def redact(value, *, key="", depth=0):
    if is_secret_key(key) and value is not None and value != "":
        return mask_lines(value) if isinstance(value, str) else MASK
    if depth > 12:
        # 深层协议包装不能成为绕开脱敏或耗尽递归的通道。
        return mask_lines(value) if isinstance(value, str) else MASK
    if isinstance(value, dict):
        return {name: redact(child, key=name, depth=depth + 1) for name, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(child, depth=depth + 1) for child in value]
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("{", "[")):
        structured = _json_text(value, depth)
        if structured is not None:
            return structured
    return _plain_text(value)


def redact_messages(messages):
    result = []
    for message in messages:
        fields = {"content": redact(message.content)}
        # 工具调用参数也会在后续请求中发回供应商，不能只检查可见正文。
        for name in ("tool_calls", "invalid_tool_calls", "additional_kwargs"):
            if value := getattr(message, name, None):
                fields[name] = redact(value)
        result.append(message.model_copy(update=fields))
    return result
