"""按用户问题确定分析范围；限制值和判定原因随运行保存。"""

import re

DEEP_QUESTION = re.compile(
    r"全面|全项目|整个项目|全部模块|完整(?![的地]?(?:原文|记录文字|记录正文)).{0,12}(流程|分析|调用链)|"
    r"项目.{0,20}(未完成|没完成|进度|工作流程|模块)|"
    r"(未完成|没完成|进度).{0,15}项目|project\s+(?:progress|audit)|full\s+workflow",
    re.I,
)
CONTINUE_QUESTION = re.compile(
    r"^(?:(?:好的?|对|可以)[，, ]*)?(?:继续|接着|继续核查|继续分析|继续未完成的部分"
    r"|开始|现在开始|动手|continue)[吧。.!！ ]*$",
    re.I,
)
GENERATION_ACTION = re.compile(
    r"从零|生成|实现|开发|编写|创建|搭建|制作|做一个|做个", re.I
)
GENERATION_TARGET = re.compile(
    r"系统|上位机|程序|应用|软件|工具|项目|界面|骨架|WinForms|WinForm|窗体", re.I
)


def is_generation_request(question):
    """只有明确要求做系统/程序时，空项目才进入从零生成；普通提问不受门禁约束。"""
    text = question or ""
    return bool(GENERATION_ACTION.search(text) and GENERATION_TARGET.search(text))


WINDOW_APP = re.compile(r"winforms?|winform|c#|上位机|窗体|桌面程序|桌面软件", re.I)


def wants_winforms(question):
    """明确提到 WinForms/C#/上位机/窗体时，生成模式自动准备 WinForms 骨架。"""
    return bool(WINDOW_APP.search(question or ""))

REPORT_GUIDANCE = """项目进度问题先给当前可确认的进度和主要缺口，再按模块说明影响与下一步。
未实现或停用、待测试验证、待工艺确认、标定及配置前置条件必须分开。
TODO、Obsolete、默认参数或标定提示不能单独证明交付功能未完成。
提前返回只证明该方法该路径；需核对调用位置、替代实现和其他防护。
默认值与可修改配置要区分，错误提示前的集合访问和执行顺序必须核对。
没有需求清单和验收记录时不能编造完成率或排期。未核实线索放在末尾，不能作为结论证据。
系统预算和来源复核消息是内部控制，不要以“收到核对结果/预算说明”开场。
先规划候选项并调用 plan_source_checks，按模块去重；使用 read_source_batch 合并相邻读取。
复用同版本已读资料，把剩余预算用于关键结论及其调用路径；不要反复检索已覆盖内容。
"""


def analysis_policy(settings, question, previous=None):
    configured = settings.analysis
    continuing = bool(CONTINUE_QUESTION.fullmatch(question.strip())) and bool(previous)
    deep = configured.mode == "deep" or (
        configured.mode == "auto"
        and (
            bool(DEEP_QUESTION.search(question)) or (continuing and previous.get("mode") == "deep")
        )
    )
    limit = configured.deep_calls if deep else configured.standard_calls
    output = settings.model.output_tokens
    if deep:
        # 回复长度取模型上下文扣除输入预留后的最大值；输入预留避免压缩后仍无空间。
        input_reserve = min(
            settings.model.context_tokens - 1024,
            max(8192, settings.model.context_tokens * 5 // 8),
        )
        output = max(1024, settings.model.context_tokens - input_reserve)
    return {
        "mode": "deep" if deep else "standard",
        "reason": "继续此前分析" if continuing else "项目范围分析" if deep else "普通问题",
        "limit": limit,
        "reserve": configured.verification_reserve,
        "output_tokens": output,
        "max_continuations": configured.max_continuations,
        "continuing": continuing,
        "question": previous.get("question", question) if continuing else question,
    }


def configured_analysis(settings, question, previous=None):
    policy = analysis_policy(settings, question, previous)
    profiles = [
        profile.model_copy(
            update={
                "config": profile.config.model_copy(
                    update={"output_tokens": policy["output_tokens"]}
                )
            }
        )
        if profile.id == settings.active_profile_id
        else profile
        for profile in settings.model_profiles
    ]
    model = next(profile.config for profile in profiles if profile.id == settings.active_profile_id)
    return settings.model_copy(update={"model": model, "model_profiles": profiles}), policy
