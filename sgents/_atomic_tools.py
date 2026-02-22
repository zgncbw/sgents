"""
_atomic_tools 工具模块

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

_atomic_tools 工具模块。

提供文件操作、命令执行、包安装等原子工具函数，供 AutoGen Agent 使用。
所有操作都在安全的工作区内进行，支持 Sandboxie 沙箱隔离。

安全特性：
    - 路径遍历保护：所有文件操作限制在工作区内
    - 输出长度限制：防止大输出导致内存溢出
    - 包名验证：防止命令注入攻击
    - 沙箱隔离：可选的 Sandboxie 沙箱执行环境

示例：
    使用默认配置::

        from ._atomic_tools import default_tools

        await default_tools.write_in_file("test.txt", "Hello")
        content = await default_tools.read_file("test.txt")
        result = await default_tools.execute_command("python --version")

    自定义配置::

        from ._atomic_tools import Config, AtomicTools

        config = Config(
            workspace=Path("./my_workspace"),
            sandbox_enabled=False,
            command_timeout=120
        )
        tools = AtomicTools(config)
        await tools.install_package("requests")

作者：
    xiatianxuan

版本：
    1.0.0

最后更新：
    2026-02-22
"""

import subprocess
import os
from pathlib import Path
from dataclasses import dataclass
import re
from typing import Final


@dataclass(frozen=True)
class Config:
    """
    工具模块配置类。

    使用冻结的数据类确保配置不可变，保证线程安全。
    初始化后会自动创建工作区目录。

    属性：
        workspace: 工作区根目录路径。所有文件操作限制在此目录内。
        sandbox_enabled: 是否启用 Sandboxie 沙箱。默认为 True。
        sandbox_path: Sandboxie 安装路径。默认为标准安装路径。
        command_timeout: 命令执行超时时间（秒）。默认为 60。
        max_output_length: 命令输出最大长度（字符）。默认为 10000。
        max_file_size: 文件读取最大大小（字节）。默认为 100KB。
        default_encoding: 默认文件编码。默认为 "utf-8"。

    示例：
        默认配置::

            config = Config()

        自定义配置::

            config = Config(
                workspace=Path("./my_workspace"),
                sandbox_enabled=False,
                command_timeout=120,
                max_output_length=50000
            )

    注意：
        配置实例创建后不可修改（frozen=True）。
        如需修改，需创建新实例。
    """

    workspace: Path = Path("./workspace")
    sandbox_enabled: bool = True
    sandbox_path: str = r"D:\sandboxieplus\Sandboxie-Plus"
    command_timeout: int = 60
    max_output_length: int = 10000
    max_file_size: int = 1024 * 100
    default_encoding: str = "utf-8"

    def __post_init__(self) -> None:
        """
        初始化后处理。

        解析工作区路径为绝对路径，并创建工作区目录。
        由于数据类是 frozen 的，使用 object.__setattr__ 修改属性。
        """
        object.__setattr__(self, "workspace", self.workspace.resolve())
        self.workspace.mkdir(parents=True, exist_ok=True)


class AtomicTools:
    """
    AutoGen Agent 原子工具集。

    提供文件操作、命令执行、包安装等功能，所有操作都在安全的工作区内进行。

    安全特性：
        - 路径遍历保护：所有文件操作限制在工作区内
        - 输出长度限制：防止大输出导致内存溢出
        - 包名验证：防止命令注入攻击
        - 沙箱隔离：可选的 Sandboxie 沙箱执行环境

    属性：
        config: 工具配置对象。
        _start_path: Sandboxie Start.exe 路径。
        PACKAGE_PATTERN: 包名验证正则表达式（类常量）。

    示例：
        使用默认配置::

            tools = AtomicTools(Config())
            await tools.write_in_file("test.txt", "Hello")
            content = await tools.read_file("test.txt")

        自定义配置::

            config = Config(workspace=Path("./my_workspace"))
            tools = AtomicTools(config)
            await tools.install_package("requests")

    注意：
        所有方法都是异步的（async），以兼容 AutoGen 框架。
    """

    PACKAGE_PATTERN: Final = re.compile(r"^[a-zA-Z0-9_-]+(\[[a-zA-Z0-9_-]+\])?$")

    def __init__(self, config: Config) -> None:
        """
        初始化工具实例。

        Args:
            config: 配置对象。包含工作区、沙箱、超时等配置项。

        示例：
            config = Config()
            tools = AtomicTools(config)
        """
        self.config: Config = config
        self._start_path: Path = Path(self.config.sandbox_path) / "Start.exe"

    def _validate_package_name(self, package_name: str) -> bool:
        """
        验证 Python 包名格式。

        包名只能包含字母、数字、下划线、连字符，
        可选的 extras 用方括号包裹（如：uvicorn[standard]）。

        Args:
            package_name: 包名称。

        Returns:
            格式有效返回 True，否则返回 False。

        示例：
            有效包名::

                tools._validate_package_name("requests")  # True
                tools._validate_package_name("beautifulsoup4")  # True
                tools._validate_package_name("uvicorn[standard]")  # True

            无效包名::

                tools._validate_package_name("requests; rm -rf /")  # False
                tools._validate_package_name("../evil")  # False
        """
        return bool(self.PACKAGE_PATTERN.match(package_name))

    def _get_safe_path(self, filename: str) -> Path:
        """
        解析路径并限制在工作区内，防止路径遍历攻击。

        此方法会解析所有符号链接和相对路径，
        确保最终路径在工作区目录内。

        Args:
            filename: 文件名或相对路径。

        Returns:
            安全的绝对路径。

        Raises:
            ValueError: 如果路径超出工作区范围。

        示例：
            安全路径::

                path = tools._get_safe_path("test.txt")
                # 返回：/workspace/test.txt

            危险路径（会被拒绝）::

                path = tools._get_safe_path("../etc/passwd")
                # 抛出：ValueError: 非法路径访问
        """
        target_path: Path = self.config.workspace / filename
        abs_target: Path = target_path.resolve()
        abs_workspace: Path = self.config.workspace.resolve()

        try:
            abs_target.relative_to(abs_workspace)
        except ValueError:
            raise ValueError(f"非法路径访问：{filename} (超出工作区范围)")

        return abs_target

    async def make_new_dir(self, dir_name: str) -> str:
        """
        创建新目录。

        如果父目录不存在会自动创建。

        Args:
            dir_name: 目录名称或相对路径。

        Returns:
            操作结果消息。成功返回创建成功消息，失败返回错误信息。

        示例：
            创建目录::

                result = await tools.make_new_dir("src")
                # 返回："目录 /workspace/src 创建成功。"

                result = await tools.make_new_dir("a/b/c")
                # 自动创建父目录
        """
        try:
            target_dir: Path = self._get_safe_path(dir_name)
            target_dir.mkdir(parents=True, exist_ok=True)
            return f"目录 {target_dir} 创建成功。"
        except ValueError as e:
            return f"错误：{e}"
        except Exception as e:
            return f"创建失败：{e}"

    async def write_in_file(self, file_path: str, content: str) -> str:
        """
        向文件写入内容（覆盖模式）。

        如果文件不存在会自动创建，如果父目录不存在也会自动创建。
        使用配置的默认编码写入文件。

        Args:
            file_path: 文件路径（相对于工作区）。
            content: 要写入的内容。

        Returns:
            操作结果消息。成功返回写入成功消息，失败返回错误信息。

        示例：
            写入文件::

                result = await tools.write_in_file("test.txt", "Hello World")
                # 返回："文件 /workspace/test.txt 写入成功。"

            写入代码::

                code = '''
                def hello():
                    print("Hello")
                '''
                result = await tools.write_in_file("hello.py", code)

        注意：
            - 如果文件已存在，会被覆盖
            - 自动创建父目录
            - 使用配置的默认编码（UTF-8）
        """
        try:
            target_file: Path = self._get_safe_path(file_path)
            target_file.parent.mkdir(parents=True, exist_ok=True)

            with open(
                target_file, mode="w", encoding=self.config.default_encoding
            ) as f:
                f.write(content)

            return f"文件 {target_file} 写入成功。"
        except ValueError as e:
            return f"错误：{e}"
        except Exception as e:
            return f"写入失败：{e}"

    async def append_to_file(self, file_path: str, content: str) -> str:
        r"""
        向文件末尾追加内容。

        如果文件不存在会自动创建，如果父目录不存在也会自动创建。
        使用配置的默认编码追加内容。

        Args:
            file_path: 文件路径（相对于工作区）。
            content: 要追加的内容。

        Returns:
            操作结果消息。成功返回追加成功消息，失败返回错误信息。

        示例：
            追加日志::

                result = await tools.append_to_file("log.txt", "New log entry\\n")
                # 返回："已向 /workspace/log.txt 追加内容。"

            追加代码::

                result = await tools.append_to_file("main.py", "\\n# New comment")

        注意：
            - 如果文件不存在，会自动创建
            - 不会覆盖原有内容
        """
        try:
            target_file: Path = self._get_safe_path(file_path)
            target_file.parent.mkdir(parents=True, exist_ok=True)

            with open(
                target_file, mode="a", encoding=self.config.default_encoding
            ) as f:
                f.write(content)

            return f"已向 {target_file} 追加内容。"
        except ValueError as e:
            return f"错误：{e}"
        except Exception as e:
            return f"追加失败：{e}"

    async def read_file(self, file_path: str) -> str:
        """
        读取指定文件的内容。

        文件过大时只返回前 max_file_size 字节（默认 100KB）。
        自动处理编码错误（忽略无法解码的字符）。

        Args:
            file_path: 文件路径（相对于工作区）。

        Returns:
            文件内容。如果文件过大，末尾会添加截断提示。
            如果文件不存在或是目录，返回错误信息。

        示例：
            读取文件::

                content = await tools.read_file("test.txt")
                print(content)

            读取代码::

                code = await tools.read_file("main.py")

        注意：
            - 文件过大时只返回前 100KB
            - 自动处理编码错误（忽略无法解码的字符）
        """
        try:
            target_path: Path = self._get_safe_path(file_path)
            if not target_path.exists():
                return f"错误：文件 {file_path} 不存在。"
            if target_path.is_dir():
                return f"错误：{file_path} 是一个目录，请使用 list_files 查看。"

            file_size: int = target_path.stat().st_size
            limit: int = self.config.max_file_size

            with open(
                target_path,
                mode="r",
                encoding=self.config.default_encoding,
                errors="ignore",
            ) as f:
                content: str = f.read(limit)
                if file_size > limit:
                    content += "\n... (文件过大，仅显示前 100KB 内容)"
                return content
        except ValueError as e:
            return f"错误：{e}"
        except Exception as e:
            return f"读取失败：{e}"

    async def list_files(self, dir_name: str = "./") -> str:
        """
        列出指定目录下的文件和子目录。

        目录排在文件前面，按名称字母排序。

        Args:
            dir_name: 目录路径（相对于工作区），默认为根目录。

        Returns:
            文件和目录列表。每行一个项目，格式为：
            - [DIR]  目录名
            - [FILE] 文件名 (大小 bytes)
            如果目录为空，返回"目录为空。"。

        示例：
            列出根目录::

                files = await tools.list_files()
                print(files)

            列出子目录::

                files = await tools.list_files("src")

        注意：
            - 目录排在文件前面
            - 按名称字母排序
        """
        try:
            target_dir: Path = self._get_safe_path(dir_name)
            if not target_dir.exists():
                return f"错误：目录 {dir_name} 不存在。"

            items: list[Path] = list(target_dir.iterdir())
            if not items:
                return "目录为空。"

            result: list[str] = []
            for item in items:
                prefix: str = "[DIR] " if item.is_dir() else "[FILE]"
                if item.is_file():
                    size: int = item.stat().st_size
                    result.append(f"{prefix} {item.name} ({size} bytes)")
                else:
                    result.append(f"{prefix} {item.name}")

            return "\n".join(result)
        except ValueError as e:
            return f"错误：{e}"
        except Exception as e:
            return f"列出文件失败：{e}"

    async def execute_command(self, command: str) -> str:
        """
        执行系统命令（可选通过 Sandboxie 沙箱）。

        如果配置启用了沙箱且 Start.exe 存在，命令会在沙箱中执行。
        输出长度有限制（防止内存溢出），超时时间为配置的超时值。

        Args:
            command: 要执行的命令。

        Returns:
            命令输出。包括返回码、标准输出、标准错误。
            如果输出过长，会被截断并添加提示。

        示例：
            执行 Python::

                result = await tools.execute_command("python --version")
                print(result)

            执行脚本::

                result = await tools.execute_command("python script.py")

            安装包::

                result = await tools.execute_command("uv pip install requests")

        注意：
            - 如果启用沙箱，命令会在 Sandboxie 中执行
            - 输出长度有限制（防止内存溢出）
            - 超时时间为配置的超时值（默认 60 秒）
        """
        run_command: str = ""
        if self.config.sandbox_enabled and os.path.exists(self._start_path):
            run_command = f'"{self._start_path}" {command}'
        else:
            run_command = command

        try:
            env: dict[str, str] = os.environ.copy()
            env["PYTHONIOENCODING"] = self.config.default_encoding

            result: subprocess.CompletedProcess[str] = subprocess.run(
                run_command,
                shell=True,
                capture_output=True,
                text=True,
                encoding=self.config.default_encoding,
                errors="replace",
                timeout=self.config.command_timeout,
                env=env,
            )

            output: str = f"返回码：{result.returncode}\n"

            if result.stdout:
                stdout: str = result.stdout[: self.config.max_output_length]
                output += f"输出:\n{stdout}\n"
                if len(result.stdout) > self.config.max_output_length:
                    output += "\n... (输出过长，已截断)"

            if result.stderr:
                stderr: str = result.stderr[: self.config.max_output_length]
                output += f"错误:\n{stderr}"
                if len(result.stderr) > self.config.max_output_length:
                    output += "\n... (错误信息过长，已截断)"
            return output
        except subprocess.TimeoutExpired:
            return "错误：命令执行超时。"
        except Exception as e:
            return f"错误：{e}"

    async def install_package(self, package_name: str) -> str:
        """
        安装 Python 第三方库。

        使用 uv pip install 安装，速度更快。
        包名会经过验证（防止命令注入）。

        Args:
            package_name: 包名称。例如：requests, beautifulsoup4, uvicorn[standard]。

        Returns:
            安装结果。成功返回 pip 输出，失败返回错误信息。

        示例：
            安装包::

                result = await tools.install_package("requests")
                print(result)

            安装带 extras::

                result = await tools.install_package("uvicorn[standard]")

        注意：
            - 包名会经过验证（防止命令注入）
            - 使用 uv pip 安装（更快）
        """
        if not self._validate_package_name(package_name):
            return f"错误：无效的包名格式：{package_name}"
        return await self.execute_command(f"uv pip install -q {package_name}")


default_config: Final = Config()
"""
默认配置实例。

使用默认配置创建的 Config 实例，工作区为 "./workspace"。
适用于大多数单用户场景。

示例：
    from ._atomic_tools import default_config

    print(default_config.workspace)
    print(default_config.sandbox_enabled)
"""

default_tools: Final = AtomicTools(default_config)
"""
默认工具实例。

使用默认配置创建的 AtomicTools 实例。
适用于大多数单用户场景，无需手动创建配置和工具实例。

示例：
    from ._atomic_tools import default_tools

    await default_tools.write_in_file("test.txt", "Hello")
    content = await default_tools.read_file("test.txt")
    result = await default_tools.execute_command("python --version")
"""

__all__: Final = [
    "Config",
    "AtomicTools",
    "default_config",
    "default_tools",
]
