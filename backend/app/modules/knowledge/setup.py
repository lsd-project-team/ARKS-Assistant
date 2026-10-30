"""显式准备本机检索模型；正常问答只加载已下载的模型。"""

from fastembed import TextEmbedding

from app.modules.knowledge.semantic import MODEL, MODEL_CACHE


def prepare():
    MODEL_CACHE.mkdir(parents=True, exist_ok=True)
    options = {
        "model_name": MODEL,
        "cache_dir": str(MODEL_CACHE),
        "threads": 2,
        "providers": ["CPUExecutionProvider"],
    }
    try:
        encoder = TextEmbedding(**options, local_files_only=True)
    except (OSError, ValueError, RuntimeError):
        encoder = TextEmbedding(**options)
    vector = next(encoder.embed(["核对本机语义检索模型"]))
    if len(vector) != 384:
        raise RuntimeError("检索模型输出维度不符合预期")
    print(f"本机多语言检索模型已准备：{MODEL}，384 维")


if __name__ == "__main__":
    prepare()
