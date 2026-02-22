"""
_save_config 工具模块

Copyright (C) 2026 xiatianxuan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

配置管理模块。

提供配置文件的加载、保存、验证等功能。
配置文件格式为 JSON，支持热更新和配置验证。

本模块负责管理 sgents 工具的所有配置项，包括工作区路径、沙箱设置、
超时时间、输出限制等。配置文件会在首次使用时自动创建，所有修改会
立即保存到磁盘。

主要功能：
    - 自动创建默认配置文件（如果不存在）
    - 配置值验证（检查必填项和有效范围）
    - 转换为 Config 对象（与 _atomic_tools 模块集成）
    - 配置重置（恢复默认值）

配置项说明：
    workspace: 工作区根目录路径，所有文件操作限制在此目录内
    sandbox_enabled: 是否启用 Sandboxie 沙箱隔离
    sandbox_path: Sandboxie 安装路径
    command_timeout: 命令执行超时时间（秒）
    max_output_length: 命令输出最大长度（字符）
    max_file_size: 文件读取最大大小（字节）
    default_encoding: 默认文件编码

示例：
    基本用法::

        from config_manager import config_manager

        # 获取配置
        workspace = config_manager.get("workspace")
        sandbox_enabled = config_manager.get("sandbox_enabled")

        # 设置配置
        config_manager.set("sandbox_enabled", False)
        config_manager.set("command_timeout", 120)

        # 验证配置
        valid, errors = config_manager.validate()
        if not valid:
            print("配置错误：", errors)

        # 转换为 Config 对象
        config = config_manager.to_config()

    自定义配置文件路径::

        from config_manager import ConfigManager

        manager = ConfigManager("path/to/config.json")
        manager.load()

    批量更新配置::

        config_manager.update({
            "sandbox_enabled": False,
            "command_timeout": 120,
            "max_output_length": 50000
        })

    重置为默认配置::

        config_manager.reset()

作者：
    xiatianxuan

版本：
    1.0.0

最后更新：
    2026-02-22

参考：
    - PEP 257: Docstring Conventions
    - Google Python Style Guide: Comments and Docstrings
"""

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING, Final

if TYPE_CHECKING:
    from ._atomic_tools import Config


DEFAULT_CONFIG: Final[dict[str, Any]] = {
    "workspace": "./workspace",
    "sandbox_enabled": True,
    "sandbox_path": r"D:\sandboxieplus\Sandboxie-Plus",
    "command_timeout": 60,
    "max_output_length": 10000,
    "max_file_size": 1024 * 100,
    "default_encoding": "utf-8",
}
"""
默认配置字典。

包含所有配置项的默认值，在配置文件不存在或解析失败时使用。
此字典为冻结常量，不应直接修改。

配置项：
    workspace: 默认工作区路径为 "./workspace"
    sandbox_enabled: 默认启用沙箱
    sandbox_path: 默认 Sandboxie 安装路径
    command_timeout: 默认超时 60 秒
    max_output_length: 默认输出限制 10000 字符
    max_file_size: 默认文件大小限制 100KB
    default_encoding: 默认编码 UTF-8

类型：
    Final[dict[str, Any]]

注意：
    修改默认值应直接编辑此字典，不要使用 set() 方法。
"""


class ConfigManager:
    """
    配置管理器。

    负责配置文件的加载、保存、验证和更新。
    配置文件格式为 JSON。

    本类提供完整的配置生命周期管理，包括：
    - 初始化时自动加载配置文件
    - 配置不存在时自动创建默认配置
    - 配置修改后自动保存到磁盘
    - 配置值验证（检查必填项和有效范围）
    - 转换为 _atomic_tools.Config 对象

    属性：
        config_path (Path): 配置文件路径。
        config (dict[str, Any]): 当前配置字典。

    线程安全性：
        本类不是线程安全的。多线程环境下应使用锁保护。

    示例：
        使用全局实例::

            from config_manager import config_manager

            workspace = config_manager.get("workspace")
            config_manager.set("sandbox_enabled", False)

        自定义实例::

            from config_manager import ConfigManager

            manager = ConfigManager("path/to/config.json")
            manager.load()

        验证配置::

            valid, errors = config_manager.validate()
            if not valid:
                for error in errors:
                    print(f"配置错误：{error}")

        转换为 Config 对象::

            from ._atomic_tools import AtomicTools

            config = config_manager.to_config()
            tools = AtomicTools(config)

    注意：
        配置文件会在首次加载时自动创建（如果不存在）。
        所有修改会立即保存到文件。
        配置文件格式为 JSON，可手动编辑。

    参考：
        - PEP 257: Docstring Conventions
        - Google Python Style Guide: Comments and Docstrings
    """

    def __init__(self, config_path: str = "config.json") -> None:
        """
        初始化配置管理器。

        创建配置管理器实例，加载配置文件。如果配置文件不存在，
        会自动创建默认配置并保存。

        Args:
            config_path: 配置文件路径。默认为 "config.json"。
                可以是相对路径或绝对路径。

        Returns:
            None

        Raises:
            PermissionError: 如果无法创建配置文件或工作区目录。
            OSError: 如果文件系统错误。

        示例：
            默认配置路径::

                manager = ConfigManager()

            自定义配置路径::

                manager = ConfigManager("path/to/config.json")
                manager = ConfigManager("/etc/sgents/config.json")

        注意：
            此方法会自动调用 load() 加载配置。
            配置文件会在初始化时自动创建（如果不存在）。
        """
        self.config_path: Path = Path(config_path)
        self.config: dict[str, Any] = {}
        self.load()

    def load(self) -> dict[str, Any]:
        """
        加载配置文件。

        从磁盘加载配置文件。如果配置文件不存在，创建默认配置并保存。
        如果配置文件解析失败（JSON 格式错误），使用默认配置。

        Returns:
            dict[str, Any]: 配置字典。包含所有配置项的键值对。

        Raises:
            PermissionError: 如果无法读取或写入配置文件。
            OSError: 如果文件系统错误。

        示例：
            基本用法::

                config = manager.load()
                print(config)

            重新加载配置::

                # 外部修改配置文件后重新加载
                manager.load()

        注意：
            此方法会在初始化时自动调用。
            手动调用会重新加载配置（覆盖未保存的修改）。
            配置文件不存在时会自动创建。
        """
        if not self.config_path.exists():
            self.config = DEFAULT_CONFIG.copy()
            self.save()
            return self.config

        try:
            with open(self.config_path, mode="r", encoding="utf-8") as f:
                self.config = json.load(f)
        except json.JSONDecodeError:
            self.config = DEFAULT_CONFIG.copy()
            self.save()

        return self.config

    def save(self) -> None:
        """
        保存配置文件。

        将当前配置写入 JSON 文件。如果父目录不存在，会自动创建。
        配置文件格式化为带缩进的 JSON，便于人工阅读和编辑。

        Returns:
            None

        Raises:
            PermissionError: 如果无法写入配置文件。
            OSError: 如果文件系统错误。

        示例：
            自动保存::

                manager.set("workspace", "./new_workspace")
                # 自动调用 save()

            手动保存::

                manager.config["workspace"] = "./new_workspace"
                manager.save()

        注意：
            set() 方法会自动调用 save()。
            update() 方法会自动调用 save()。
            批量修改后建议手动调用一次 save()。
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, mode="w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值。

        从配置字典中获取指定键的值。如果键不存在，返回默认值。

        Args:
            key: 配置键名。例如："workspace", "sandbox_enabled"。
            default: 默认值。键不存在时返回此值。默认为 None。

        Returns:
            Any: 配置值。如果键不存在，返回默认值。

        示例：
            获取配置::

                workspace = manager.get("workspace")
                timeout = manager.get("command_timeout", 60)
                unknown = manager.get("unknown_key", "default_value")

            获取布尔值::

                sandbox_enabled = manager.get("sandbox_enabled", True)

        注意：
            此方法不会修改配置。
            返回的值是配置的引用，修改会影响原配置。
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置配置值。

        设置指定键的配置值，并立即保存到配置文件。

        Args:
            key: 配置键名。例如："workspace", "sandbox_enabled"。
            value: 配置值。可以是任何 JSON 可序列化的类型。

        Returns:
            None

        Raises:
            PermissionError: 如果无法写入配置文件。
            OSError: 如果文件系统错误。

        示例：
            设置布尔值::

                manager.set("sandbox_enabled", False)

            设置整数::

                manager.set("command_timeout", 120)

            设置字符串::

                manager.set("workspace", "./new_workspace")

        注意：
            此方法会自动保存配置到文件。
            批量修改建议使用 update() 方法（只保存一次）。
        """
        self.config[key] = value
        self.save()

    def update(self, config_dict: dict[str, Any]) -> None:
        """
        批量更新配置。

        使用提供的字典批量更新配置项，只调用一次 save()。
        适合批量修改多个配置项的场景。

        Args:
            config_dict: 配置字典。键为配置项名称，值为配置值。

        Returns:
            None

        Raises:
            PermissionError: 如果无法写入配置文件。
            OSError: 如果文件系统错误。

        示例：
            批量更新::

                manager.update({
                    "sandbox_enabled": False,
                    "command_timeout": 120,
                    "max_output_length": 50000
                })

            部分更新::

                manager.update({
                    "workspace": "./new_workspace"
                })

        注意：
            此方法只调用一次 save()，适合批量修改。
            会覆盖现有配置项，不会删除未提供的配置项。
        """
        self.config.update(config_dict)
        self.save()

    def validate(self) -> tuple[bool, list[str]]:
        """
        验证配置。

        检查配置值是否合法，返回验证结果和错误信息列表。
        验证项目包括必填项检查、数值范围检查等。

        Returns:
            tuple[bool, list[str]]: 验证结果。
                第一个元素为是否有效（True/False）。
                第二个元素为错误信息列表（有效时为空）。

        Raises:
            None: 此方法不会抛出异常，错误通过返回值报告。

        示例：
            基本用法::

                valid, errors = manager.validate()
                if not valid:
                    for error in errors:
                        print(f"配置错误：{error}")

            断言验证::

                valid, errors = manager.validate()
                assert valid, f"配置验证失败：{errors}"

        验证项目：
            workspace: 不能为空字符串
            sandbox_path: 沙箱启用时不能为空字符串
            command_timeout: 必须大于 0
            max_output_length: 必须大于 0
            max_file_size: 必须大于 0

        注意：
            此方法不会修改配置。
            验证失败时配置仍可正常使用，但可能导致运行时错误。
        """
        errors: list[str] = []

        workspace: str = self.get("workspace", "./workspace")
        if not workspace:
            errors.append("workspace 不能为空")

        if self.get("sandbox_enabled", True):
            sandbox_path: str = self.get("sandbox_path", "")
            if not sandbox_path:
                errors.append("sandbox_path 不能为空")

        timeout: int = self.get("command_timeout", 60)
        if timeout <= 0:
            errors.append("command_timeout 必须大于 0")

        max_output: int = self.get("max_output_length", 10000)
        if max_output <= 0:
            errors.append("max_output_length 必须大于 0")

        max_file: int = self.get("max_file_size", 1024 * 100)
        if max_file <= 0:
            errors.append("max_file_size 必须大于 0")

        return (len(errors) == 0, errors)

    def to_config(self) -> "Config":
        """
        转换为 _atomic_tools.Config 对象。

        将当前配置转换为 _atomic_tools 模块的 Config 数据类。
        用于与 AtomicTools 类集成。

        Returns:
            Config: _atomic_tools.Config 对象。包含所有配置项。

        Raises:
            ImportError: 如果 _atomic_tools 模块不存在。

        示例：
            基本用法::

                from ._atomic_tools import AtomicTools

                config = manager.to_config()
                tools = AtomicTools(config)

            自定义工具实例::

                config = manager.to_config()
                tools = AtomicTools(config)
                await tools.write_in_file("test.txt", "Hello")

        注意：
            此方法会导入 _atomic_tools 模块。
            确保 _atomic_tools 模块已存在。
            返回的 Config 对象是冻结的，不可修改。
        """
        from ._atomic_tools import Config

        return Config(
            workspace=Path(self.get("workspace", "./workspace")),
            sandbox_enabled=self.get("sandbox_enabled", True),
            sandbox_path=self.get("sandbox_path", r"D:\sandboxieplus\Sandboxie-Plus"),
            command_timeout=self.get("command_timeout", 60),
            max_output_length=self.get("max_output_length", 10000),
            max_file_size=self.get("max_file_size", 1024 * 100),
            default_encoding=self.get("default_encoding", "utf-8"),
        )

    def reset(self) -> None:
        """
        重置为默认配置。

        删除配置文件并重新加载默认配置。此操作不可逆，
        会丢失所有自定义配置。

        Returns:
            None

        Raises:
            PermissionError: 如果无法删除配置文件。
            OSError: 如果文件系统错误。

        示例：
            重置配置::

                manager.reset()

            重置后验证::

                manager.reset()
                valid, errors = manager.validate()
                assert valid, "默认配置验证失败"

        注意：
            此操作不可逆，会丢失所有自定义配置。
            配置文件会被删除，下次使用时重新创建。
            建议重置前备份配置文件。
        """
        if self.config_path.exists():
            self.config_path.unlink()
        self.config = DEFAULT_CONFIG.copy()
        self.save()

    def show(self) -> str:
        """
        显示当前配置。

        返回格式化的配置字符串（JSON 格式）。
        用于调试或日志输出。

        Returns:
            str: 格式化的配置字符串。JSON 格式，带缩进。

        示例：
            打印配置::

                print(manager.show())

            记录配置::

                logger.info(f"当前配置：{manager.show()}")

        注意：
            返回的字符串包含所有配置项。
            不包含敏感信息（如 API Key）。
        """
        return json.dumps(self.config, indent=2, ensure_ascii=False)


config_manager: Final = ConfigManager()
"""
全局配置管理器实例。

使用默认配置路径（"config.json"）创建的 ConfigManager 实例。
适用于大多数单用户场景，无需手动创建配置管理器实例。

类型：
    Final[ConfigManager]

示例：
    基本用法::

        from config_manager import config_manager

        workspace = config_manager.get("workspace")
        config_manager.set("sandbox_enabled", False)

    验证配置::

        valid, errors = config_manager.validate()
        if not valid:
            print("配置错误：", errors)

    转换为 Config 对象::

        config = config_manager.to_config()

注意：
    此实例在模块导入时自动初始化。
    如果配置文件路径有问题，导入时会报错。
    多用户场景建议创建新的 ConfigManager 实例。
"""


__all__: Final = [
    "ConfigManager",
    "config_manager",
    "DEFAULT_CONFIG",
]
"""
模块导出列表。

定义使用 `from config_manager import *` 时导出的符号。
包含公共 API，不包括内部实现细节。

导出项：
    ConfigManager: 配置管理器类。
    config_manager: 全局配置管理器实例。
    DEFAULT_CONFIG: 默认配置字典。

类型：
    Final[list[str]]

注意：
    不在 __all__ 中的符号不应直接导入。
    内部函数和变量不应在模块外使用。
"""
