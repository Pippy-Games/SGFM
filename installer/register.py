"""文件关联注册与注销。

Windows 的文件关联有两套机制：
  1. HKCU\\Software\\Classes\\<.ext>          —— 基础关联（本模块使用）
  2. HKCU\\Software\\...\\FileExts\\<.ext>\\UserChoice  —— 用户手动选择的默认程序

第 2 套由系统在用户"始终使用此应用打开"时写入，并带有校验哈希，
第三方无法伪造。因此本模块：
  - 注册第一套（保证右键"打开方式"里有我们的程序）
  - 若检测到 UserChoice 已被其他程序锁定，会给出提示
  - 首次双击 .sgmic 时，Windows 会弹"选择默认程序"对话框，用户选一次即可

所有操作在 HKCU 下，无需管理员权限。
"""

import os
import sys
import winreg
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量
# ============================================================

# 扩展名 → ProgID
EXTENSIONS: Dict[str, str] = {
    '.sgmic': 'SGMF.Audio',
    '.sgpim': 'SGMF.Video',
    '.sgwb':  'SGMF.Text',
    '.sgtp':  'SGMF.Image',
}

# ProgID → 显示名（在"打开方式"里显示的名字）
PROG_IDS: Dict[str, str] = {
    'SGMF.Audio': 'SGMF 音频',
    'SGMF.Video': 'SGMF 视频',
    'SGMF.Text':  'SGMF 文本',
    'SGMF.Image': 'SGMF 图片',
}

# 主 ProgID（用于默认情况）
MAIN_PROG_ID = 'SGMF.Media'


class FileAssociationError(Exception):
    """文件关联操作失败。"""
    pass


# ============================================================
# 内部工具
# ============================================================

def _hkey_classes() -> int:
    return winreg.HKEY_CURRENT_USER


def _set_value(root, subkey: str, name: Optional[str], value: str):
    """创建子键并写入字符串值。"""
    with winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _delete_tree(root, subkey: str) -> bool:
    """递归删除子键及其所有子键。返回是否实际删除。"""
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            # 先递归删除所有子键
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(root, f"{subkey}\\{child}")
    except FileNotFoundError:
        return False

    try:
        winreg.DeleteKey(root, subkey)
        return True
    except OSError:
        # 键可能非空（枚举时被打断），再删一次
        try:
            winreg.DeleteKey(root, subkey)
            return True
        except OSError:
            return False


def _key_exists(root, subkey: str) -> bool:
    try:
        with winreg.OpenKey(root, subkey):
            return True
    except FileNotFoundError:
        return False


def _read_value(root, subkey: str, name: Optional[str]) -> Optional[str]:
    try:
        with winreg.OpenKey(root, subkey) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except (FileNotFoundError, OSError):
        return None


# ============================================================
# 图标路径（优先使用 exe 内嵌图标，其次 assets/*.ico）
# ============================================================

def _resolve_icon_path(icon_name: str = 'icon.ico') -> Optional[str]:
    """解析图标文件的绝对路径。

    查找顺序：
      1. 打包后：sys._MEIPASS/installer/assets/
      2. 源码运行：<项目根>/installer/assets/
    """
    candidates = []

    # PyInstaller 打包后
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(os.path.join(meipass, 'installer', 'assets', icon_name))
        candidates.append(os.path.join(meipass, 'assets', icon_name))

    # 源码运行
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, 'assets', icon_name))

    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None


# ============================================================
# 注册
# ============================================================

def register_one(extension: str,
                 prog_id: str,
                 player_path: str,
                 icon_path: Optional[str] = None,
                 description: Optional[str] = None) -> None:
    """注册单个扩展名。

    Args:
        extension:    含点的扩展名，如 '.sgmic'
        prog_id:      ProgID，如 'SGMF.Audio'
        player_path:  播放器 exe 或 python 脚本的绝对路径
        icon_path:    图标文件路径；None 表示不设图标
        description:  在资源管理器中显示的类型描述
    """
    if not extension.startswith('.'):
        extension = '.' + extension
    extension = extension.lower()

    if not os.path.isabs(player_path):
        raise FileAssociationError(f"player_path 必须是绝对路径: {player_path}")
    if not os.path.isfile(player_path):
        raise FileAssociationError(f"播放器文件不存在: {player_path}")

    root = _hkey_classes()

    # ---------- 1. 扩展名 → ProgID ----------
    _set_value(root, extension, None, prog_id)

    # 告知系统这是一个"打开"关联（OpenWithProgids）
    _set_value(
        root,
        f"{extension}\\OpenWithProgids",
        prog_id,
        "",
    )

    # ---------- 2. ProgID 描述 ----------
    desc = description or PROG_IDS.get(prog_id, prog_id)
    _set_value(root, prog_id, None, desc)

    # ---------- 3. 默认图标 ----------
    if icon_path and os.path.isfile(icon_path):
        _set_value(
            root,
            f"{prog_id}\\DefaultIcon",
            None,
            f"{icon_path},0",
        )

    # ---------- 4. 打开命令 ----------
    # Windows 会把 "%1" 替换成被打开文件的路径
    command = f'"{player_path}" "%1"'
    _set_value(
        root,
        f"{prog_id}\\shell\\open\\command",
        None,
        command,
    )

    # ---------- 5. "用 SGMF 播放器打开" 右键菜单项 ----------
    _set_value(root, f"{prog_id}\\shell\\open", "MUIVerb", "用 SGMF 播放器打开")
    _set_value(root, f"{prog_id}\\shell\\open", "Icon", f"{icon_path},0" if icon_path else player_path)


def register_all(player_path: str,
                 icon_dir: Optional[str] = None,
                 per_type_icons: bool = True) -> List[str]:
    """注册全部四种扩展名。

    Args:
        player_path:    播放器 exe / 脚本的绝对路径
        icon_dir:       图标目录；None 表示使用 installer/assets/
        per_type_icons: 是否为每种类型使用不同图标

    Returns:
        已注册的扩展名列表
    """
    if icon_dir is None:
        installer_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(installer_dir)
        icon_dir = os.path.join(project_root, 'assets')
        # 回退：installer/assets 下也有就用它
        if not os.path.isdir(icon_dir):
            icon_dir = os.path.join(installer_dir, 'assets')

    default_icon = _resolve_icon_path('icon.ico')

    # 每种类型对应的图标名
    type_icons = {
        '.sgmic': 'icon_audio.ico',
        '.sgpim': 'icon_video.ico',
        '.sgwb':  'icon_text.ico',
        '.sgtp':  'icon_image.ico',
    }

    registered = []
    for ext, prog_id in EXTENSIONS.items():
        icon = default_icon
        if per_type_icons:
            candidate = os.path.join(icon_dir, type_icons.get(ext, ''))
            if os.path.isfile(candidate):
                icon = candidate

        try:
            register_one(
                extension=ext,
                prog_id=prog_id,
                player_path=player_path,
                icon_path=icon,
                description=PROG_IDS.get(prog_id),
            )
            registered.append(ext)
        except FileAssociationError:
            raise

    return registered


# ============================================================
# 注销
# ============================================================

def unregister_one(extension: str, prog_id: str) -> bool:
    """注销单个扩展名。返回是否有实际删除。"""
    if not extension.startswith('.'):
        extension = '.' + extension
    extension = extension.lower()

    root = _hkey_classes()
    deleted = False

    # 删除 OpenWithProgids 里的项
    _delete_tree(root, f"{extension}\\OpenWithProgids\\{prog_id}")

    # 只有当扩展名默认值指向我们的 ProgID 时才清空
    current = _read_value(root, extension, None)
    if current == prog_id:
        try:
            with winreg.OpenKey(root, extension, 0, winreg.KEY_WRITE) as key:
                winreg.DeleteValue(key, '')
                deleted = True
        except OSError:
            pass

    # 删除 ProgID 整棵子树
    if _delete_tree(root, prog_id):
        deleted = True

    return deleted


def unregister_all() -> List[str]:
    """注销全部四种扩展名。"""
    removed = []
    for ext, prog_id in EXTENSIONS.items():
        if unregister_one(ext, prog_id):
            removed.append(ext)
    return removed


# ============================================================
# 查询
# ============================================================

def check_associations() -> Dict[str, Tuple[bool, Optional[str]]]:
    """检查四种扩展名的当前关联状态。

    Returns:
        {'.sgmic': (是否已关联到 SGMF, 当前 command 字符串), ...}
    """
    root = _hkey_classes()
    result = {}

    for ext, prog_id in EXTENSIONS.items():
        cmd_key = f"{prog_id}\\shell\\open\\command"
        cmd = _read_value(root, cmd_key, None)

        # 扩展名本身是否指向这个 ProgID
        ext_default = _read_value(root, ext, None)
        is_linked = (ext_default == prog_id) and cmd is not None

        result[ext] = (is_linked, cmd)

    return result


def get_registered_player() -> Optional[str]:
    """读取当前注册的播放器路径（从 .sgmic 的 command 里提取）。"""
    root = _hkey_classes()
    cmd_key = f"{EXTENSIONS['.sgmic']}\\shell\\open\\command"
    cmd = _read_value(root, cmd_key, None)
    if not cmd:
        return None

    # 命令形如: "C:\path\to\player.exe" "%1"
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        if end > 0:
            return cmd[1:end]
    # 无引号时取第一个空格之前
    parts = cmd.split(' ', 1)
    return parts[0] if parts else None


def is_admin() -> bool:
    """判断当前进程是否以管理员身份运行。"""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ============================================================
# 通知资源管理器刷新图标缓存
# ============================================================

def notify_shell_change() -> None:
    """通知资源管理器刷新关联缓存，让图标立即生效。"""
    try:
        import ctypes
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(
            SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None
        )
    except Exception:
        pass


# ============================================================
# 高层封装：检查 UserChoice（Win10/11 的默认程序锁定）
# ============================================================

def check_user_choice(extension: str) -> Optional[str]:
    """读取 Win10/11 的 UserChoice ProgID（若用户手动设过默认程序）。

    注意：UserChoice 带哈希校验，第三方无法写入，仅能读取用于提示。
    """
    if not extension.startswith('.'):
        extension = '.' + extension

    subkey = (
        f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer"
        f"\\FileExts\\{extension}\\UserChoice"
    )
    return _read_value(winreg.HKEY_CURRENT_USER, subkey, "ProgId")


def diagnose() -> Dict[str, dict]:
    """诊断四种扩展名在系统中的完整状态。"""
    root = _hkey_classes()
    report = {}

    for ext, prog_id in EXTENSIONS.items():
        ext_linked = _read_value(root, ext, None) == prog_id
        cmd = _read_value(root, f"{prog_id}\\shell\\open\\command", None)
        user_choice = check_user_choice(ext)

        report[ext] = {
            'prog_id': prog_id,
            'ext_linked': ext_linked,
            'command': cmd,
            'user_choice': user_choice,
            'user_choice_is_sgmf': user_choice == prog_id,
            'fully_associated': ext_linked and cmd is not None,
        }

    return report