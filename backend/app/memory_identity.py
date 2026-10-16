"""账号上下文随请求和运行任务传播，缓存服务不能持有可变的当前用户。"""

from app.auth.context import request_identity


def user_memory_owner():
    identity = request_identity.get()
    return str(identity["user"]["id"]) if identity else None


def user_memory_key():
    owner = user_memory_owner()
    # 无请求上下文的旧脚本仍能维护旧数据；登录账号绝不隐式继承公共记忆。
    return f"user:{owner}" if owner else "user"
