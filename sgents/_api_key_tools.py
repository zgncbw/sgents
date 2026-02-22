"""
_api_key_tools 工具模块

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

API Key 安全管理模块。

本模块提供安全的 API Key 存储和检索功能，使用操作系统级别的凭据存储服务：

    - Windows: Windows 凭据管理器 (Windows Credential Manager)
    - macOS: 钥匙串访问 (Keychain Access)
    - Linux: 密钥环服务 (GNOME Keyring / KWallet)

主要特性：
    - 系统级加密存储，API Key 不落地到文件系统
    - 支持多用户场景（通过 username 参数区分）
    - 完整的异常处理和类型注解
    - 单例模式，全局实例可直接使用

示例：
    基本用法::

        from api_key_manager import api_key_manager

        # 存储 API Key
        api_key_manager.set_api_key("ms-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")

        # 获取 API Key
        key = api_key_manager.get_api_key()
        if key:
            print(f"API Key: {key[:10]}...")

        # 检查是否存在
        if api_key_manager.has_api_key():
            print("API Key 已配置")

        # 删除 API Key
        api_key_manager.delete_api_key()

    多用户场景::

        # 为不同用户存储不同的 API Key
        api_key_manager.set_api_key("key1", username="user1")
        api_key_manager.set_api_key("key2", username="user2")

        # 分别获取
        key1 = api_key_manager.get_api_key("user1")
        key2 = api_key_manager.get_api_key("user2")

注意事项：
    - API Key 通过环境变量或 .env 文件以外的方式存储，更加安全
    - 首次使用时请确保系统凭据服务已启用
    - Linux 用户可能需要安装 gnome-keyring 或 kwallet

作者：
    xiatianxuan

版本：
    1.0.0

最后更新：
    2026-02-22
"""

import keyring
import keyring.errors
from typing import Final, Any

# =============================================================================
# 常量定义
# =============================================================================

SERVICE_NAME: Final = "sgents"
"""
服务名称常量。

用于在系统凭据管理器中注册服务的唯一标识符。所有存储的 API Key 都将
关联到此服务名下。

类型：
    Final[str]

默认值：
    "sgents"

示例：
    >>> SERVICE_NAME
    'sgents'
"""


# =============================================================================
# 异常类
# =============================================================================


class APIKeyError(Exception):
    """
    API Key 相关异常的基类。

    当 API Key 的存储、检索或删除操作失败时，将抛出此异常或其子类。

    常见触发场景：
        - 系统凭据服务不可用
        - API Key 为空或格式无效
        - 权限不足导致无法访问凭据存储
        - 密钥后端初始化失败

    示例：
        >>> try:
        ...     api_key_manager.set_api_key("")
        ... except APIKeyError as e:
        ...     print(f"错误：{e}")
        错误：API Key 不能为空

    继承自：
        Exception
    """

    pass


# =============================================================================
# 核心类
# =============================================================================


class APIKeyManager:
    """
    API Key 管理器。

    提供完整的 API Key 生命周期管理功能，包括存储、检索、删除和状态检查。
    底层使用 keyring 库与操作系统凭据服务交互，确保 API Key 的安全存储。

    安全特性：
        - 使用操作系统级加密存储
        - API Key 不以明文形式存储在文件中
        - 支持多用户隔离（通过 username 参数）
        - 完整的异常处理和错误报告

    平台支持：
        - Windows 10/11: Windows Credential Manager
        - macOS 10.15+: Keychain Access
        - Linux: GNOME Keyring, KWallet, 或 SecretService

    属性：
        service_name (str): 服务名称标识符，用于在系统凭据中注册。

    示例：
        创建管理器实例::

            manager = APIKeyManager()
            manager.set_api_key("ms-xxxxxxxx...", username="default")

        使用全局单例::

            from api_key_manager import api_key_manager
            api_key_manager.set_api_key("ms-xxxxxxxx...")

    注意：
        首次使用前请确保系统凭据服务已正确配置。Linux 用户可能需要
        安装额外的依赖包（如 gnome-keyring）。

    参考：
        - keyring 文档：https://pypi.org/project/keyring/
        - PEP 257 文档字符串规范
    """

    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        """
        初始化 API Key 管理器。

        创建管理器实例并验证系统凭据后端是否可用。如果后端不可用，
        将抛出 APIKeyError 异常。

        参数：
            service_name (str, optional): 服务名称标识符。用于在系统凭据
                管理器中注册服务。默认为 SERVICE_NAME 常量值 ("sgents")。

        返回：
            None

        异常：
            APIKeyError: 当系统凭据后端不可用时抛出。

        示例：
            默认服务名::

                manager = APIKeyManager()

            自定义服务名::

                manager = APIKeyManager(service_name="myapp")

        注意：
            构造函数会自动调用 _check_backend() 验证后端可用性。
            如果验证失败，实例将不会创建成功。
        """
        self.service_name: str = service_name
        self._check_backend()

    def _check_backend(self) -> None:
        """
        检查 keyring 后端是否可用。

        验证系统凭据服务是否正确配置并可用。如果后端优先级为 0，
        表示未找到可用的凭据存储服务。

        返回：
            None

        异常：
            APIKeyError: 当未找到可用的密钥后端时抛出，包含平台相关的
                配置指导信息。

        平台特定要求：
            Windows:
                确保 Windows 凭据管理器服务正在运行。
            macOS:
                确保钥匙串访问 (Keychain Access) 可用。
            Linux:
                安装 gnome-keyring 或 kwallet 之一：
                - Ubuntu/Debian: sudo apt install gnome-keyring
                - Fedora: sudo dnf install gnome-keyring
                - Arch: sudo pacman -S gnome-keyring

        示例：
            >>> manager = APIKeyManager()  # 自动调用此方法
            >>> manager._check_backend()   # 手动检查
        """
        backend: Any = keyring.get_keyring()
        if backend.priority == 0:
            raise APIKeyError(
                "未找到可用的密钥后端！\n"
                "Windows: 确保 Windows 凭据管理器可用\n"
                "macOS: 确保钥匙串访问可用\n"
                "Linux: 安装 gnome-keyring 或 kwallet"
            )

    def set_api_key(self, api_key: str, username: str) -> bool:
        """
        存储 API Key 到系统凭据管理器。

        将提供的 API Key 安全存储到操作系统级别的凭据存储中。存储前会
        验证 API Key 不为空，并自动去除首尾空白字符。

        参数：
            api_key (str): API Key 字符串。不能为空或仅包含空白字符。
                建议格式：提供商前缀 + 唯一标识符
                例如："ms-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            username (str): 用户名标识符。用于区分不同用户的 API Key。
                单用户场景建议使用 "default"。

        返回：
            bool: 存储成功返回 True。

        异常：
            APIKeyError: 当 API Key 为空或存储失败时抛出。包含详细的
                错误信息以便调试。

        示例：
            基本用法::

                manager.set_api_key("ms-xxxxxxxx...", username="default")

            多用户场景::

                manager.set_api_key("key1", username="user1")
                manager.set_api_key("key2", username="user2")

            异常处理::

                try:
                    manager.set_api_key("", username="default")
                except APIKeyError as e:
                    print(f"存储失败：{e}")

        注意：
            - API Key 会被自动去除首尾空白字符
            - 同一 username 的新值会覆盖旧值
            - 存储操作是同步的，完成后立即可检索

        安全性：
            API Key 将以加密形式存储在系统凭据中，不会出现在：
            - 配置文件
            - 日志文件
            - 版本控制系统
        """
        if not api_key or not api_key.strip():
            raise APIKeyError("API Key 不能为空")

        try:
            keyring.set_password(
                service_name=self.service_name,
                username=username,
                password=api_key.strip(),
            )
            return True
        except keyring.errors.InitError as e:
            raise APIKeyError(f"密钥后端初始化失败：{e}")
        except Exception as e:
            raise APIKeyError(f"存储失败：{e}")

    def get_api_key(self, username: str) -> str | None:
        """
        从系统凭据管理器获取 API Key。

        检索之前存储的 API Key。如果指定的 username 不存在或检索失败，
        返回 None。

        参数：
            username (str): 用户名标识符。必须与存储时使用的 username
                一致。

        返回：
            str | None: 如果找到 API Key，返回字符串；否则返回 None。
                返回的字符串不包含首尾空白字符。

        异常：
            APIKeyError: 当密钥后端不可用时抛出。

        示例：
            基本用法::

                key = manager.get_api_key("default")
                if key:
                    print(f"API Key: {key[:10]}...")
                else:
                    print("未找到 API Key")

            多用户场景::

                user1_key = manager.get_api_key("user1")
                user2_key = manager.get_api_key("user2")

            异常处理::

                try:
                    key = manager.get_api_key("default")
                except APIKeyError as e:
                    print(f"获取失败：{e}")

        注意：
            - 返回值为 None 表示未找到或检索失败
            - 建议使用 has_api_key() 先检查是否存在
            - 检索操作是同步的

        安全性：
            - 返回的 API Key 不应记录到日志中
            - 使用完成后应及时从内存中清除
            - 建议使用掩码显示（如显示前 10 位）
        """
        try:
            api_key: str | None = keyring.get_password(
                service_name=self.service_name, username=username
            )
            return api_key
        except keyring.errors.NoKeyringError:
            raise APIKeyError("密钥后端不可用")
        except Exception:
            return None

    def delete_api_key(self, username: str) -> bool:
        """
        从系统凭据管理器删除 API Key。

        永久删除指定 username 的 API Key。删除后无法恢复，需要重新存储。

        参数：
            username (str): 用户名标识符。必须与存储时使用的 username
                一致。

        返回：
            bool: 删除成功返回 True；如果 API Key 不存在或删除失败，
                返回 False。

        示例：
            基本用法::

                if manager.delete_api_key("default"):
                    print("删除成功")
                else:
                    print("删除失败或不存在")

            批量删除::

                for user in ["user1", "user2", "user3"]:
                    manager.delete_api_key(user)

        注意：
            - 删除操作不可逆
            - 删除不存在的 API Key 返回 False，不抛出异常
            - 建议删除前先用 has_api_key() 确认存在

        安全性：
            - 删除后 API Key 从系统凭据中永久移除
            - 不会留下任何痕迹或备份
            - 适合在用户注销或重置配置时使用
        """
        try:
            keyring.delete_password(service_name=self.service_name, username=username)
            return True
        except keyring.errors.PasswordDeleteError:
            return False
        except Exception:
            return False

    def has_api_key(self, username: str) -> bool:
        """
        检查指定用户是否存在 API Key。

        快速检查指定的 username 是否已存储 API Key，无需获取完整内容。

        参数：
            username (str): 用户名标识符。

        返回：
            bool: 存在返回 True，否则返回 False。

        示例：
            基本用法::

                if manager.has_api_key("default"):
                    print("API Key 已配置")
                else:
                    print("请先配置 API Key")

            配置检查::

                if not manager.has_api_key("default"):
                    manager.set_api_key(input("输入 API Key: "), "default")

        注意：
            - 此方法内部调用 get_api_key()
            - 返回 True 仅表示存在，不保证 API Key 有效
            - 适合在程序启动时进行配置检查

        性能：
            此方法会访问系统凭据存储，可能有轻微的性能开销。
            建议在程序初始化时调用，避免在循环中频繁调用。
        """
        return self.get_api_key(username) is not None

    def __repr__(self) -> str:
        """
        返回对象的字符串表示。

        生成包含服务名称的格式化字符串，用于调试和日志记录。

        返回：
            str: 格式为 "APIKeyManager(service={service_name})" 的字符串。

        示例：
            >>> manager = APIKeyManager()
            >>> repr(manager)
            'APIKeyManager(service=sgents)'

            >>> manager = APIKeyManager("myapp")
            >>> repr(manager)
            'APIKeyManager(service=myapp)'

        注意：
            此方法不返回任何敏感信息（如 API Key），可以安全地用于日志输出。
        """
        return f"APIKeyManager(service={self.service_name})"


# =============================================================================
# 全局实例
# =============================================================================

api_key_manager: Final = APIKeyManager()
"""
API Key 管理器全局单例实例。

这是预初始化的 APIKeyManager 实例，适用于大多数单用户场景。
直接使用此实例可以避免重复创建管理器的开销。

类型：
    Final[APIKeyManager]

示例：
    导入并使用::

        from api_key_manager import api_key_manager

        # 存储
        api_key_manager.set_api_key("ms-xxxxxxxx...")

        # 获取
        key = api_key_manager.get_api_key()

        # 检查
        if api_key_manager.has_api_key():
            print("已配置")

注意：
    - 此实例在模块导入时自动初始化
    - 如果系统凭据后端不可用，导入时会抛出 APIKeyError
    - 多用户场景建议创建新的 APIKeyManager 实例

参考：
    APIKeyManager 类文档
"""
