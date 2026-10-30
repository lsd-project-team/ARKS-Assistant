"""容器内只读健康探测；显式部署时使用已配置Host，不受代理环境变量影响。"""

import json
import os
from urllib.request import ProxyHandler, Request, build_opener


def main():
    host = os.environ.get("ARKS_TRUSTED_HOSTS", "127.0.0.1").split(",")[0].strip()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    request = Request("http://127.0.0.1:8765/api/health", headers={"Host": host})
    with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
        if response.status != 200 or json.load(response).get("ok") is not True:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
