from datetime import datetime
from enum import StrEnum
from typing import Any, Self, cast

import questionary
from rich.align import Align
from rich.box import DOUBLE
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


menu_style = questionary.Style(
    [
        ("qmark", "#787DFF bold"),
        ("question", "#787DFF bold"),
        ("answer", "#9787FF"),
        ("pointer", "#9787FF"),
        ("highlighted", "#9787FF bold")
    ]
)
"""Generic questionary menu style."""


LOGO = r"""[#787DFF]                          __      [/]
[#877DFF]   _________ ____  ____  / /______[/]
[#967DFF]  / ___/ __ `/ _ \/ __ \/ __/ ___/[/]
[#A57DFF] (__  ) /_/ /  __/ / / / /_(__  ) [/]
[#B47DFF]/____/\__, /\___/_/ /_/\__/____/  [/]
[#C37DFF]     /____/                       
"""


# ============================== Multiple Language Supports ==============================
def lang(key: str, mapping: dict[str, Any] = {
        "agent_state_STANDBY": "就绪",
        "sandbox_status_True": "启用",
        "sandbox_status_False": "禁用",

        "show_launching_banner_title": "Sgents 控制台",
        "show_launching_banner_subtitle": "使用上下键选择，Enter 确认",

        "show_status_bar_time_format": "%Y/%m/%d %H:%M:%S",
        "show_status_bar_statues_text": "[#9898FF]Agent：[/][#787DFF]{}[/] [#9898FF]| 沙箱：[/][#787DFF]{}[/] [#9898FF]| 任务：[/][#787DFF]{}[/] [#9898FF]| 启动时间：[/][#787DFF]{}[/]",
        "show_status_bar_title": "Agent 状态",

        "show_agent_status_headers": ("角色", "状态", "工具"),
        "show_agent_status_title": "Agent 团队状态",
        "show_agent_status_table": (
            ("代码编写", "就绪"),
            ("代码审查", "就绪"),
            ("任务执行", "就绪"),
            ("协调整合", "就绪")
        ),

        "ask_by_main_menu_message": "请选择操作：",
        "ask_by_main_menu_choices": (
            "执行新任务",
            "查看历史任务",
            "浏览工作区",
            "Agent 团队状态",
            "配置设置",
            "退出"
        ),

        "ask_by_task_type_menu_message": "选择任务类型：",
        "ask_by_task_type_menu_choices": (
            "网页爬取",
            "数据处理",
            "文件操作",
            "系统命令",
            "多 Agent 协作",
            "返回"
        ),

        "ask_for_task_description_prompt": "请输入任务描述：",

        "ask_confirm_return_message": "按 Enter 返回",

        "main_choice1": "\n[#9898FF]任务 '{}' 执行成功！[/]\n",
    }
) -> str:
    return mapping[key]


# ============================== Interface Impletementation ==============================
class AgentState(StrEnum):
    """Possible agent states."""
    STANDBY = lang("agent_state_STANDBY")

    def __repr__(self) -> str:
        return self._name_


class Interface:
    """
    Represents an user interface.
    Only one instance of `Interface` can exist at the same time.
    """

    __instance: Interface | None = None

    def __new__(cls) -> Self:
        # Impletement single instance mode.
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cast(Self, cls.__instance)

    def __init__(self) -> None:
        self.task_count: int = 0
        self.agent_status: AgentState = AgentState.STANDBY
        self.sandbox_status: bool = True

    def show_launching_banner(self):
        """Show the launching banner."""
        console.clear()
        print()

        panel = Panel(
            Align.center(LOGO),
            title=lang("show_launching_banner_title"),
            subtitle=lang("show_launching_banner_subtitle"),
            border_style="#9787FF"
        )
        console.print(panel)
        print()
    
    def show_status_bar(self) -> None:
        """Show the status bar."""
        current_time = datetime.now().strftime(lang("show_status_bar_time_format"))
        statues_text = lang("show_status_bar_statues_text").format(
            self.agent_status,
            lang("sandbox_status_True") if self.sandbox_status else lang("sandbox_status_False"),
            self.task_count, current_time
        )
        console.print(
            Panel(
                statues_text,
                box=DOUBLE,
                title=lang("show_status_bar_title"),
                border_style="#9787FF"
            )
        )
        print()
    
    def show_agent_status(self):
        """Show the status of the agent group."""
        table = Table(
            "Agent", *lang("show_agent_status_headers"),
            title=lang("show_agent_status_title"),
            border_style="#9787FF", title_style="#9787FF bold", header_style="#9898FF"
        )
        row1, row2, row3, row4 = lang("show_agent_status_table")
        table.add_row("Coder", *row1, "3", style="#B9B3FF")
        table.add_row("Reviewer", *row2, "2", style="#B9B3FF")
        table.add_row("Executor", *row3, "4", style="#B9B3FF")
        table.add_row("Manager", *row4, "1", style="#B9B3FF")
        console.print(table)
        print()
    
    def ask_by_main_menu(self) -> Any:
        """Display the main menu."""
        return questionary.select(
            lang("ask_by_main_menu_message"),
            lang("ask_by_main_menu_choices"),
            style=menu_style,
            use_arrow_keys=True
        ).ask()
    
    def ask_by_task_type_menu(self) -> Any:
        """Display the submenu which asks for the type of mission going to start."""
        return questionary.select(
            lang("ask_by_task_type_menu_message"),
            lang("ask_by_main_menu_choices"),
            style=menu_style,
            use_arrow_keys=True
        ).ask()

    def ask_for_task_description(self) -> Any:
        """Ask for the description of the mission."""
        return questionary.text(lang("ask_for_task_description_prompt"), style=menu_style).ask()

    def ask_confirm_return(self) -> Any:
        """Ask whether actually returning."""
        return questionary.confirm(lang("ask_confirm_return_message")).ask()

    def main(self):
        while True:
            try:
                self.show_launching_banner()
                self.show_status_bar()

                choose = self.ask_by_main_menu()

                match lang("ask_by_main_menu_choices").index(choose):
                    case 0:
                        task_type = self.ask_by_task_type_menu()
                        if task_type and task_type != lang("ask_by_task_type_menu_choices")[-1]:
                            task_desc = self.ask_for_task_description()
                            if task_desc:
                                self.task_count += 1
                                console.print(lang("main_choice1").format(task_desc))
                            self.ask_confirm_return()
                    case 1:
                        console.print(f"[yellow]历史任务功能开发中...[/]\n")
                    case 2:
                        console.print(f"[yellow]工作区浏览功能开发中...[/]\n")
                    case 3:
                        console.print(f"[yellow]配置设置功能开发中...[/]\n")
                    case 4:
                        self.show_agent_status()
                        self.ask_confirm_return()
                    case _:
                        console.print(f"\n[#9898FF]再见！[/]\n")
                        break
            except KeyboardInterrupt:
                console.print(f"\n\n[yellow]用户中断 (Ctrl+C)[/]\n")
                continue
            except Exception:
                console.print_exception()
                self.ask_confirm_return()


Interface().ask_by_main_menu()
