"""定义路径管理模块，所有模块中需要访问的路径，都通过此模块进行管理"""

from __future__ import annotations
import os
from pathlib import Path

def _find_project_root(start: Path) -> Path:
    cur = start
    while True:
        if (cur / "pyproject.toml").exists():
            return cur
        if cur.parent == cur:
            raise RuntimeError("Cannot locate project root (no pyproject.toml found).")
        cur = cur.parent

def get_project_root() -> Path:
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    # resolve relative to this file to be robust from anywhere
    return _find_project_root(Path(__file__).resolve())

PROJECT_ROOT = get_project_root()
CONFIG_FILE_PATH = PROJECT_ROOT / "src" / "config.yaml"

if __name__ == "__main__":
    print(PROJECT_ROOT)
    print(f"配置文件路径：{CONFIG_FILE_PATH}")