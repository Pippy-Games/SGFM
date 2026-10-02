# SGMF 文件关联模块

把 `.sgmic` / `.sgpim` / `.sgwb` / `.sgtp` 四种扩展名绑定到 SGMF 播放器。

## 特点

- **不需要管理员权限**：全部操作写在 `HKCU\Software\Classes` 下
- **兼容 Windows 7 / 10 / 11**
- **支持每种类型独立图标**
- **不会破坏系统已有默认程序**：只添加"打开方式"选项，最终决定权交给用户

## 使用方法

### 源码运行

```bat
cd 项目根
python -m installer.cli register "C:\Windows\System32\notepad.exe"