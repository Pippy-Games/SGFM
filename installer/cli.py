"""installer 命令行入口。

用法：
    # 注册到指定播放器
    python -m installer.cli register "C:\\Path\\To\\SGMFPlayer.exe"

    # 注销
    python -m installer.cli unregister

    # 查看状态
    python -m installer.cli status

    # 诊断
    python -m installer.cli diagnose
"""

import argparse
import os
import sys

from .register import (
    EXTENSIONS,
    FileAssociationError,
    check_associations,
    diagnose,
    get_registered_player,
    is_admin,
    notify_shell_change,
    register_all,
    unregister_all,
)


def _cmd_register(args):
    player = os.path.abspath(args.player)
    if not os.path.isfile(player):
        print(f"[错误] 播放器不存在: {player}")
        return 2

    print(f"注册播放器: {player}")
    if is_admin():
        print("  （管理员权限）")
    else:
        print("  （当前用户权限，无需管理员）")

    try:
        registered = register_all(
            player_path=player,
            per_type_icons=not args.no_type_icons,
        )
    except FileAssociationError as e:
        print(f"[错误] {e}")
        return 1

    notify_shell_change()

    print()
    print(f"已注册 {len(registered)} 种扩展名:")
    for ext in registered:
        print(f"  ✓ {ext}  →  {EXTENSIONS[ext]}")
    print()
    print("提示：首次双击文件时，Windows 可能仍会弹「选择默认程序」对话框，")
    print("      选一次 SGMF 播放器即可永久生效。")
    return 0


def _cmd_unregister(args):
    print("注销 SGMF 文件关联…")
    removed = unregister_all()
    notify_shell_change()

    if not removed:
        print("  没有任何关联被移除（可能未注册）。")
    else:
        print(f"已移除 {len(removed)} 种扩展名:")
        for ext in removed:
            print(f"  ✓ {ext}")
    return 0


def _cmd_status(args):
    print("SGMF 文件关联状态")
    print("=" * 56)

    assocs = check_associations()
    for ext, (linked, cmd) in assocs.items():
        mark = "✓" if linked else "✗"
        print(f"  {mark} {ext:<8} → {cmd or '未注册'}")

    print()
    current = get_registered_player()
    if current:
        print(f"当前播放器: {current}")
        if not os.path.isfile(current):
            print("  [警告] 该路径下的文件不存在，请重新注册。")
    else:
        print("当前未注册任何播放器。")
    return 0


def _cmd_diagnose(args):
    print("SGMF 文件关联诊断")
    print("=" * 56)

    report = diagnose()
    for ext, info in report.items():
        print(f"\n[{ext}]")
        print(f"  ProgID:              {info['prog_id']}")
        print(f"  扩展名已链接:        {info['ext_linked']}")
        print(f"  打开命令:            {info['command'] or '—'}")
        print(f"  UserChoice:          {info['user_choice'] or '（未设置）'}")
        print(f"  完整关联:            {info['fully_associated']}")

        if info['user_choice'] and not info['user_choice_is_sgmf']:
            print()
            print("  [提示] 用户已手动指定过其他默认程序。")
            print("         请右键文件 → 打开方式 → 选择其他应用 → SGMF 播放器")
            print("         并勾选「始终使用此应用打开」以覆盖。")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='installer',
        description='SGMF 文件关联注册工具',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_reg = sub.add_parser('register', help='注册文件关联')
    p_reg.add_argument('player', help='SGMF 播放器 exe 或脚本的绝对路径')
    p_reg.add_argument('--no-type-icons', action='store_true',
                       help='不为每种类型使用独立图标')
    p_reg.set_defaults(func=_cmd_register)

    p_unreg = sub.add_parser('unregister', help='注销文件关联')
    p_unreg.set_defaults(func=_cmd_unregister)

    p_status = sub.add_parser('status', help='查看关联状态')
    p_status.set_defaults(func=_cmd_status)

    p_diag = sub.add_parser('diagnose', help='诊断完整关联信息')
    p_diag.set_defaults(func=_cmd_diagnose)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())