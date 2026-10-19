"""部署 HTTP 边界独立于供应商配置；外部来源必须由管理员显式声明。"""

import ipaddress
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


def hostname(value):
    """规范化精确 DNS/IP；不接受通配符、URL 或有歧义的数字地址。"""
    if (
        not value
        or value != value.strip()
        or any(char.isspace() for char in value)
        or any(char in value for char in "*%")
    ):
        raise ValueError("主机名不能为空或包含空白、通配符、区域标识")
    value = value.lower()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        if (
            len(value) > 253
            or re.fullmatch(r"[\d.]+", value)
            or not all(DNS_LABEL.fullmatch(part) for part in value.split("."))
        ):
            raise ValueError("主机必须是精确 DNS 名称或 IP 地址，不能包含通配符或端口") from None
        return value


def authority(value):
    """解析 Host/Origin 的 authority，端口只校验、不用于主机白名单。"""
    if not value or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("HTTP 主机无效")
    if any(char in value for char in "\\/@?#,"):
        raise ValueError("HTTP 主机不能包含凭据或路径")
    if value.startswith("["):
        end = value.find("]")
        try:
            if "%" in value:
                raise ValueError
            address = ipaddress.ip_address(value[1:end])
            if end < 0 or address.version != 6:
                raise ValueError
        except ValueError:
            raise ValueError("HTTP IPv6 主机无效") from None
        host, suffix = str(address), value[end + 1 :]
        if suffix and not suffix.startswith(":"):
            raise ValueError("HTTP 主机无效")
        raw_port = suffix[1:] if suffix else None
    else:
        raw_host, separator, raw_port = value.partition(":")
        host = hostname(raw_host)
        raw_port = raw_port if separator else None
    if raw_port is not None and not re.fullmatch(r"[0-9]{1,5}", raw_port):
        raise ValueError("HTTP 主机端口无效")
    port = int(raw_port) if raw_port is not None else None
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("HTTP 主机端口无效")
    return host, port


def origin(value):
    if (
        not value
        or value != value.strip()
        or any(char.isspace() or ord(char) < 32 for char in value)
        or "\\" in value
    ):
        raise ValueError("来源必须是完整 HTTP/HTTPS Origin")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise ValueError("来源主机格式无效") from None
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or "?" in value
        or "#" in value
    ):
        raise ValueError("来源只允许 HTTP/HTTPS 的 scheme、主机与端口")
    host, port = authority(parsed.netloc)
    display = f"[{host}]" if ":" in host else host
    default = 443 if parsed.scheme == "https" else 80
    suffix = f":{port}" if port is not None and port != default else ""
    return f"{parsed.scheme}://{display}{suffix}", host


def configured_values(value, field):
    values = [part.strip() for part in value.split(",")]
    if not all(values):
        raise ValueError(f"{field} 不能为空或包含空项")
    return values


@dataclass(frozen=True)
class DeploymentSecurity:
    allowed_origins: frozenset[str] | None = None
    trusted_hosts: frozenset[str] | None = None

    @classmethod
    def from_environment(cls):
        origins = os.environ.get("ARKS_ALLOWED_ORIGINS")
        hosts = os.environ.get("ARKS_TRUSTED_HOSTS")
        if origins is None and hosts is None:
            return cls()
        if not origins or not hosts:
            raise ValueError("部署访问必须同时配置 ARKS_ALLOWED_ORIGINS 和 ARKS_TRUSTED_HOSTS")
        try:
            parsed_origins = [
                origin(value) for value in configured_values(origins, "ARKS_ALLOWED_ORIGINS")
            ]
            parsed_hosts = frozenset(
                hostname(value[1:-1] if value.startswith("[") and value.endswith("]") else value)
                for value in configured_values(hosts, "ARKS_TRUSTED_HOSTS")
            )
            if any(host not in parsed_hosts for _, host in parsed_origins):
                raise ValueError("每个可信 Origin 的主机必须同时列入 ARKS_TRUSTED_HOSTS")
        except ValueError as error:
            # 不回显环境原值；部署配置也可能误粘贴凭据。
            raise ValueError(f"部署 HTTP 访问配置无效：{error}") from None
        return cls(frozenset(value for value, _ in parsed_origins), parsed_hosts)

    def rejection(self, headers):
        if self.trusted_hosts is not None:
            values = headers.getlist("host")
            try:
                if len(values) != 1 or authority(values[0])[0] not in self.trusted_hosts:
                    return "请求 Host 不在部署可信主机范围内"
            except ValueError:
                return "请求 Host 无效"
        values = headers.getlist("origin")
        if not values:
            return ""
        try:
            if len(values) != 1:
                return "请求来源无效"
            normalized, host = origin(values[0])
        except ValueError:
            return "请求来源无效"
        if self.allowed_origins is None:
            return "" if host in LOOPBACK_HOSTS else "仅允许本机页面访问"
        return "" if normalized in self.allowed_origins else "请求来源不在部署可信来源范围内"

    def secure_cookie(self, scheme, request_origin=None):
        if scheme == "https":
            return True
        if self.allowed_origins is None:
            return False
        # TLS在代理终止时内部连接仍是HTTP，不能因此降级已声明的HTTPS会话。
        if all(value.startswith("https://") for value in self.allowed_origins):
            return True
        try:
            normalized, _host = origin(request_origin)
        except (TypeError, ValueError):
            return False
        return normalized.startswith("https://") and normalized in self.allowed_origins
