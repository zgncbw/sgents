#!/usr/bin/env python3
"""
AutoGen Agent CLI - 主界面
单文件测试版本
"""

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from datetime import datetime
from rich.box import DOUBLE

# 初始化控制台
console = Console()

# 颜色配置
PRIMARY = "cyan"
SUCCESS = "green"
WARNING = "yellow"
ERROR = "red"

# Questionary 菜单样式
menu_style = questionary.Style(
    [
        ("qmark", "fg:#00ffff bold"),
        ("question", "bold"),
        ("answer", "fg:#00ffff bold"),
        ("pointer", "fg:#00ffff bold"),
        ("highlighted", "fg:#00ffff bold"),
        ("selected", "fg:#00ff00"),
    ]
)

LOGO_ART = r"""[#787DFF]                          __      [/]
[#877DFF]   _________ ____  ____  / /______[/]
[#967DFF]  / ___/ __ `/ _ \/ __ \/ __/ ___/[/]
[#A57DFF] (__  ) /_/ /  __/ / / / /_(__  ) [/]
[#B47DFF]/____/\__, /\___/_/ /_/\__/____/  [/]
[#C37DFF]     /____/                       
"""


def show_banner():
    """显示启动横幅"""
    console.clear()
    console.print()

    panel = Panel(
        Align.center(LOGO_ART),
        title=f"[bold {PRIMARY}]sgents 控制台[/bold {PRIMARY}]",
        subtitle="[dim]使用上下键选择，Enter 确认[/dim]",
        border_style=PRIMARY,
        padding=(1, 4),
        width=80,
    )

    console.print(panel)
    console.print()


def show_status_bar(agent_status="就绪", sandbox_status="启用", task_count=0):
    """显示状态栏"""
    current_time = datetime.now().strftime("%H:%M")

    status_text = f"Agent: {agent_status} | 沙箱：{sandbox_status} | 任务：[{SUCCESS}]{task_count}[/{SUCCESS}] | 时间：[{SUCCESS}]{current_time}[/{SUCCESS}]"

    console.print(
        Panel(status_text, box=DOUBLE, title="Agent 状态", border_style="#5887FF")
    )
    console.print()


def show_agent_status():
    """显示 Agent 团队状态"""
    table = Table(
        title="Agent 团队状态", border_style=PRIMARY, header_style=f"bold {PRIMARY}"
    )
    table.add_column("Agent", style=PRIMARY, no_wrap=True)
    table.add_column("角色", style="magenta")
    table.add_column("状态", style=SUCCESS)
    table.add_column("工具", justify="right")

    table.add_row("Coder", "代码编写", "就绪", "3")
    table.add_row("Reviewer", "代码审查", "就绪", "2")
    table.add_row("Executor", "任务执行", "就绪", "4")
    table.add_row("Manager", "协调整合", "就绪", "1")

    console.print(table)
    console.print()


def main_menu():
    """主菜单"""
    return questionary.select(
        "请选择操作:",
        choices=[
            "执行新任务",
            "查看历史任务",
            "浏览工作区",
            "Agent 团队状态",
            "配置设置",
            "退出",
        ],
        style=menu_style,
        use_arrow_keys=True,
    ).ask()


def task_type_menu():
    """任务类型子菜单"""
    return questionary.select(
        "选择任务类型:",
        choices=[
            "网页爬取",
            "数据处理",
            "文件操作",
            "系统命令",
            "多 Agent 协作",
            "返回",
        ],
        style=menu_style,
    ).ask()


def input_task_description():
    """输入任务描述"""
    return questionary.text("请输入任务描述:", style=menu_style).ask()


def confirm_return(message="按 Enter 返回"):
    """确认返回"""
    return questionary.confirm(message).ask()


def main():
    """主程序循环"""
    task_count = 0

    while True:
        try:
            # 显示主界面
            show_banner()
            show_status_bar(task_count=task_count)

            # 获取用户选择
            action = main_menu()

            if action is None or action == "退出":
                console.print(f"\n[{PRIMARY}]再见！[/{PRIMARY}]\n")
                break

            elif action == "执行新任务":
                task_type = task_type_menu()
                if task_type and task_type != "返回":
                    task_desc = input_task_description()
                    if task_desc:
                        task_count += 1
                        console.print(
                            f"\n[{SUCCESS}] 任务 '{task_desc}' 执行成功！[/{SUCCESS}]\n"
                        )
                        confirm_return()

            elif action == "查看历史任务":
                console.print(f"\n[{WARNING}]历史任务功能开发中...[/{WARNING}]\n")
                confirm_return()

            elif action == "浏览工作区":
                console.print(f"\n[{WARNING}]工作区浏览功能开发中...[/{WARNING}]\n")
                confirm_return()

            elif action == "Agent 团队状态":
                show_agent_status()
                confirm_return()

            elif action == "配置设置":
                console.print(f"\n[{WARNING}]配置设置功能开发中...[/{WARNING}]\n")
                confirm_return()

        except KeyboardInterrupt:
            console.print(f"\n\n[{WARNING}]用户中断 (Ctrl+C)[/{WARNING}]\n")
            continue
        except Exception as e:
            console.print(f"\n[{ERROR}]错误：{e}[/{ERROR}]\n")
            confirm_return()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n\n[{PRIMARY}]已退出[/{PRIMARY}]\n")
