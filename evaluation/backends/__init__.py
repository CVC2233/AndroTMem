"""
backends/__init__.py — Backend 工厂
backends/__init__.py — backend factory

按需导入：GPT-4o 后端不会 import torch；Qwen 后端不会 import openai。
Import lazily: the GPT-4o backend does not import torch, and the Qwen backend does not import openai.
新增模型只需在此注册。
Register new models here.
"""

from base_evaluator import BaseEvaluator

_REGISTRY = {
    "gpt4o":   ("backends.gpt4o", "GPT4OBackend"),
    "qwen":    ("backends.qwen",  "QwenBackend"),
}


def get_backend(name: str, cfg: dict) -> BaseEvaluator:
    """
    按名称创建对应的 Backend 实例。
    Create the corresponding Backend instance by name.

    Args:
        name: "gpt4o" | "qwen"（后续可在 _REGISTRY 中扩展）
        name: "gpt4o" | "qwen"; extend _REGISTRY for future backends.
        cfg:  完整配置 dict
        cfg:  complete configuration dict.

    Returns:
        BaseEvaluator 子类实例
        A BaseEvaluator subclass instance.
    """
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown backend '{name}'. "
            f"Available: {list(_REGISTRY.keys())}"
        )

    module_path, class_name = _REGISTRY[name]
    import importlib
    module = importlib.import_module(module_path)
    cls    = getattr(module, class_name)
    return cls(cfg)
