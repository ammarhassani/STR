"""
Cross-platform native file dialog utilities.

Flet's FilePicker has known issues on macOS (GitHub issues #5334, #5700, #5753, #5886).
This module provides native file dialogs using:
- macOS: AppleScript via osascript
- Windows: tkinter.filedialog
- Linux: zenity with tkinter fallback
"""
import subprocess
import platform
from pathlib import Path
from typing import Optional, List


def choose_directory(
    prompt: str = "Select a folder",
    default_path: Optional[str] = None
) -> Optional[str]:
    """
    Show a native directory selection dialog.

    Args:
        prompt: Dialog title/prompt
        default_path: Initial directory to show

    Returns:
        Selected directory path or None if cancelled
    """
    system = platform.system()

    if system == "Darwin":
        return _macos_choose_directory(prompt, default_path)
    elif system == "Windows":
        return _windows_choose_directory(prompt, default_path)
    else:
        return _linux_choose_directory(prompt, default_path)


def choose_file(
    prompt: str = "Select a file",
    default_path: Optional[str] = None,
    file_types: Optional[List[str]] = None
) -> Optional[str]:
    """
    Show a native file selection dialog.

    Args:
        prompt: Dialog title/prompt
        default_path: Initial directory to show
        file_types: List of allowed extensions (e.g., ['db', 'sqlite'])

    Returns:
        Selected file path or None if cancelled
    """
    system = platform.system()

    if system == "Darwin":
        return _macos_choose_file(prompt, default_path, file_types)
    elif system == "Windows":
        return _windows_choose_file(prompt, default_path, file_types)
    else:
        return _linux_choose_file(prompt, default_path, file_types)


def choose_save_file(
    prompt: str = "Save file",
    default_path: Optional[str] = None,
    default_name: Optional[str] = None,
    file_types: Optional[List[str]] = None
) -> Optional[str]:
    """
    Show a native save file dialog.

    Args:
        prompt: Dialog title/prompt
        default_path: Initial directory to show
        default_name: Default filename
        file_types: List of allowed extensions (e.g., ['db', 'sqlite'])

    Returns:
        Selected file path or None if cancelled
    """
    system = platform.system()

    if system == "Darwin":
        return _macos_choose_save_file(prompt, default_path, default_name, file_types)
    elif system == "Windows":
        return _windows_choose_save_file(prompt, default_path, default_name, file_types)
    else:
        return _linux_choose_save_file(prompt, default_path, default_name, file_types)


# ============================================================================
# macOS Implementation (AppleScript)
# ============================================================================

def _macos_choose_directory(prompt: str, default_path: Optional[str]) -> Optional[str]:
    """Use AppleScript to show native macOS folder picker."""
    script_parts = ['choose folder']
    script_parts.append(f'with prompt "{prompt}"')

    if default_path and Path(default_path).exists():
        script_parts.append(f'default location POSIX file "{default_path}"')

    script = ' '.join(script_parts)

    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and result.stdout.strip():
            hfs_path = result.stdout.strip()
            return _hfs_to_posix(hfs_path)
        return None

    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"Error showing directory dialog: {e}")
        return None


def _macos_choose_file(
    prompt: str,
    default_path: Optional[str],
    file_types: Optional[List[str]]
) -> Optional[str]:
    """Use AppleScript to show native macOS file picker."""
    script_parts = ['choose file']
    script_parts.append(f'with prompt "{prompt}"')

    if default_path:
        parent = Path(default_path).parent if Path(default_path).is_file() else Path(default_path)
        if parent.exists():
            script_parts.append(f'default location POSIX file "{parent}"')

    if file_types:
        types_str = ', '.join(f'"{t}"' for t in file_types)
        script_parts.append(f'of type {{{types_str}}}')

    script = ' '.join(script_parts)

    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and result.stdout.strip():
            hfs_path = result.stdout.strip()
            return _hfs_to_posix(hfs_path)
        return None

    except Exception as e:
        print(f"Error showing file dialog: {e}")
        return None


def _macos_choose_save_file(
    prompt: str,
    default_path: Optional[str],
    default_name: Optional[str],
    file_types: Optional[List[str]]
) -> Optional[str]:
    """Use AppleScript to show native macOS save dialog."""
    # AppleScript doesn't have a direct "save file" dialog, use choose file name
    script_parts = ['choose file name']
    script_parts.append(f'with prompt "{prompt}"')

    if default_path and Path(default_path).exists():
        script_parts.append(f'default location POSIX file "{default_path}"')

    if default_name:
        script_parts.append(f'default name "{default_name}"')

    script = ' '.join(script_parts)

    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and result.stdout.strip():
            hfs_path = result.stdout.strip()
            return _hfs_to_posix(hfs_path)
        return None

    except Exception as e:
        print(f"Error showing save dialog: {e}")
        return None


def _hfs_to_posix(hfs_path: str) -> str:
    """Convert HFS path (Macintosh HD:Users:...) to POSIX path (/Users/...)."""
    # Strip "alias " prefix if present (AppleScript returns "alias Macintosh HD:...")
    if hfs_path.startswith('alias '):
        hfs_path = hfs_path[6:]

    hfs_path = hfs_path.rstrip(':')
    parts = hfs_path.split(':')

    if parts[0] == "Macintosh HD":
        posix_parts = ['']
        posix_parts.extend(parts[1:])
    else:
        posix_parts = ['', 'Volumes', parts[0]]
        posix_parts.extend(parts[1:])

    return '/'.join(posix_parts)


# ============================================================================
# Windows Implementation (tkinter)
# ============================================================================

def _windows_choose_directory(prompt: str, default_path: Optional[str]) -> Optional[str]:
    """Use tkinter for Windows directory picker."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    try:
        path = filedialog.askdirectory(
            title=prompt,
            initialdir=default_path if default_path and Path(default_path).exists() else None
        )
        return path if path else None
    finally:
        root.destroy()


def _windows_choose_file(
    prompt: str,
    default_path: Optional[str],
    file_types: Optional[List[str]]
) -> Optional[str]:
    """Use tkinter for Windows file picker."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    filetypes = [('All files', '*.*')]
    if file_types:
        for ext in file_types:
            filetypes.insert(0, (f'{ext.upper()} files', f'*.{ext}'))

    try:
        path = filedialog.askopenfilename(
            title=prompt,
            initialdir=default_path if default_path and Path(default_path).exists() else None,
            filetypes=filetypes
        )
        return path if path else None
    finally:
        root.destroy()


def _windows_choose_save_file(
    prompt: str,
    default_path: Optional[str],
    default_name: Optional[str],
    file_types: Optional[List[str]]
) -> Optional[str]:
    """Use tkinter for Windows save file dialog."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    filetypes = [('All files', '*.*')]
    if file_types:
        for ext in file_types:
            filetypes.insert(0, (f'{ext.upper()} files', f'*.{ext}'))

    try:
        path = filedialog.asksaveasfilename(
            title=prompt,
            initialdir=default_path if default_path and Path(default_path).exists() else None,
            initialfile=default_name,
            filetypes=filetypes
        )
        return path if path else None
    finally:
        root.destroy()


# ============================================================================
# Linux Implementation (zenity with tkinter fallback)
# ============================================================================

def _linux_choose_directory(prompt: str, default_path: Optional[str]) -> Optional[str]:
    """Use zenity or kdialog for Linux directory picker."""
    try:
        cmd = ['zenity', '--file-selection', '--directory', '--title', prompt]
        if default_path and Path(default_path).exists():
            cmd.extend(['--filename', default_path + '/'])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    return _windows_choose_directory(prompt, default_path)


def _linux_choose_file(
    prompt: str,
    default_path: Optional[str],
    file_types: Optional[List[str]]
) -> Optional[str]:
    """Use zenity for Linux file picker."""
    try:
        cmd = ['zenity', '--file-selection', '--title', prompt]
        if default_path and Path(default_path).exists():
            parent = Path(default_path).parent if Path(default_path).is_file() else Path(default_path)
            cmd.extend(['--filename', str(parent) + '/'])

        if file_types:
            for ext in file_types:
                cmd.extend(['--file-filter', f'*.{ext}'])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    return _windows_choose_file(prompt, default_path, file_types)


def _linux_choose_save_file(
    prompt: str,
    default_path: Optional[str],
    default_name: Optional[str],
    file_types: Optional[List[str]]
) -> Optional[str]:
    """Use zenity for Linux save file dialog."""
    try:
        cmd = ['zenity', '--file-selection', '--save', '--title', prompt]
        if default_path and Path(default_path).exists():
            cmd.extend(['--filename', default_path + '/'])
        if default_name:
            cmd.extend(['--filename', default_name])

        if file_types:
            for ext in file_types:
                cmd.extend(['--file-filter', f'*.{ext}'])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    return _windows_choose_save_file(prompt, default_path, default_name, file_types)
