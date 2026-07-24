"""
向后兼容模块 — 旧版 SandboxManager 别名。

推荐使用 create_sandbox() 工厂函数，避免直接引用此模块。
"""

from app.sandbox.docker import DockerSandbox

# 保持旧名可用，避免遗留引用报错
SandboxManager = DockerSandbox

__all__ = ["SandboxManager"]
