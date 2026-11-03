"""Opt-in Win32 integration. Importing this module never installs a hook.

Only process basenames explicitly allowed by the user receive conversions.
Only verified native Edit/RichEdit controls accept input. ES_PASSWORD and
ES_READONLY controls, unknown modern fields, and multiline RichEdit controls
are refused. Selection actions read native selection ranges and do not touch
the clipboard. Browser, terminal, WinUI, and custom-rendered fields are unsupported.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as wt
from dataclasses import dataclass
import os
import threading
import time
from typing import Callable, Iterable

IS_WINDOWS = os.name == "nt"
WH_KEYBOARD_LL, WH_MOUSE_LL = 13, 14
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
WM_QUIT = 0x12
LLKHF_INJECTED = 0x10
KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 2, 4
SELF_INPUT_MARKER = 0x415A4144
VK_SHIFT, VK_CONTROL, VK_MENU = 0x10, 0x11, 0x12
MODIFIERS = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}
NAVIGATION = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x1B}
HOTKEYS = {0x20: "word", 0x0D: "selection", 0x55: "undo", 0x44: "dictionary", 0x50: "pause"}


def normalize_apps(apps: Iterable[str]) -> frozenset[str]:
    """Allow process basenames only; an empty collection intentionally denies all."""
    result = set()
    for app in apps:
        app = str(app).strip().lower()
        if not app:
            continue
        if "/" in app or "\\" in app or not app.endswith(".exe"):
            raise ValueError("Allowed applications must be executable basenames, such as notepad.exe")
        result.add(app)
    return frozenset(result)


def ascii_key(vk: int, shift: bool, caps: bool = False) -> str | None:
    """Translate US QWERTY physical keys without changing keyboard state."""
    if 0x41 <= vk <= 0x5A:
        ch = chr(vk)
        return ch if shift != caps else ch.lower()
    if 0x30 <= vk <= 0x39:
        return ")!@#$%^&*("[vk - 0x30] if shift else chr(vk)
    normal = {0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/", 0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'"}
    shifted = {0xBA: ":", 0xBB: "+", 0xBC: "<", 0xBD: "_", 0xBE: ">", 0xBF: "?", 0xC0: "~", 0xDB: "{", 0xDC: "|", 0xDD: "}", 0xDE: '"'}
    return (shifted if shift else normal).get(vk)


def utf16_units(text: str) -> list[int]:
    raw = text.encode("utf-16-le")
    return [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw), 2)]


@dataclass(frozen=True)
class WindowIdentity:
    hwnd: int = 0
    focus: int = 0
    app: str = ""
    password: bool = False
    english_layout: bool = False
    editable: bool = False
    class_name: str = ""


@dataclass(frozen=True)
class EditorSnapshot:
    text: str
    start: int  # UTF-16 code-unit offsets, as reported by EM_GETSEL.
    end: int

    @property
    def selected(self) -> str:
        return self.text.encode("utf-16-le")[2 * self.start:2 * self.end].decode("utf-16-le")

    def has_suffix(self, value: str) -> bool:
        if self.start != self.end:
            return False
        prefix = self.text.encode("utf-16-le")[:2 * self.start].decode("utf-16-le")
        return prefix.endswith(value)


@dataclass(frozen=True)
class Replacement:
    before: str
    after: str
    identity: WindowIdentity


if IS_WINDOWS:
    ULONG_PTR = ctypes.c_size_t
    LRESULT = ctypes.c_ssize_t
    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]

    class INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("value",)
        _fields_ = [("type", wt.DWORD), ("value", INPUTUNION)]

    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [("cbSize", wt.DWORD), ("flags", wt.DWORD), ("hwndActive", wt.HWND), ("hwndFocus", wt.HWND), ("hwndCapture", wt.HWND), ("hwndMenuOwner", wt.HWND), ("hwndMoveSize", wt.HWND), ("hwndCaret", wt.HWND), ("rcCaret", wt.RECT)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
    user32.SetWindowsHookExW.restype = wt.HHOOK
    user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
    user32.CallNextHookEx.restype = LRESULT
    user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
    user32.GetForegroundWindow.restype = wt.HWND
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    user32.GetWindowThreadProcessId.restype = wt.DWORD
    user32.GetGUIThreadInfo.argtypes = [wt.DWORD, ctypes.POINTER(GUITHREADINFO)]
    user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
    user32.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT, ctypes.POINTER(ULONG_PTR)]
    user32.SendMessageTimeoutW.restype = LRESULT
    user32.GetKeyboardLayout.argtypes = [wt.DWORD]
    user32.GetKeyboardLayout.restype = wt.HANDLE
    user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wt.UINT
    user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
    user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
    kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wt.HMODULE
    kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    kernel32.OpenProcess.restype = wt.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
    kernel32.CloseHandle.argtypes = [wt.HANDLE]


def foreground_identity() -> WindowIdentity:
    if not IS_WINDOWS:
        return WindowIdentity()
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return WindowIdentity()
    pid = wt.DWORD()
    tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
    if not user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
        return WindowIdentity(hwnd=int(hwnd))
    app = ""
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    if handle:
        try:
            path, size = ctypes.create_unicode_buffer(32768), wt.DWORD(32768)
            if kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                app = os.path.basename(path.value).lower()
        finally:
            kernel32.CloseHandle(handle)
    focus = int(info.hwndFocus or 0)
    cls = ctypes.create_unicode_buffer(256)
    if focus:
        user32.GetClassNameW(focus, cls, len(cls))
    class_name = cls.value.lower()
    is_edit = class_name == "edit" or class_name.startswith("richedit")
    style = user32.GetWindowLongW(focus, -16) if focus else 0
    password = bool(is_edit and style & 0x20)
    editable = is_edit and not bool(style & (0x20 | 0x800))
    layout = int(user32.GetKeyboardLayout(tid) or 0)
    return WindowIdentity(int(hwnd), focus, app, password, (layout & 0x3FF) == 9, editable, class_name)


def foreground_app() -> str:
    return foreground_identity().app


def _message(hwnd: int, message: int, wparam: int = 0, lparam: int = 0) -> int:
    result = ULONG_PTR()
    if not user32.SendMessageTimeoutW(hwnd, message, wparam, lparam, 0x0002, 120, ctypes.byref(result)):
        raise OSError("Editor did not answer a bounded inspection request")
    return result.value


def _read_editor(identity: WindowIdentity) -> EditorSnapshot:
    if not identity.editable or identity.password or foreground_identity() != identity:
        raise OSError("The focused field is not a supported editable native control")
    length = _message(identity.focus, 0x000E)  # WM_GETTEXTLENGTH, UTF-16 units.
    if length > 512 * 1024:
        raise ValueError("Editor is too large for bounded verification")
    buffer = ctypes.create_unicode_buffer(length + 1)
    copied = _message(identity.focus, 0x000D, length + 1, ctypes.addressof(buffer))
    if copied > length:
        raise OSError("Editor text changed during verification")
    start, end = wt.DWORD(), wt.DWORD()
    _message(identity.focus, 0x00B0, ctypes.addressof(start), ctypes.addressof(end))  # EM_GETSEL.
    text = buffer.value
    units = len(text.encode("utf-16-le")) // 2
    if start.value > end.value or end.value > units:
        raise OSError("Editor reported an unverifiable selection")
    if identity.class_name.startswith("richedit") and ("\r" in text or "\n" in text):
        raise OSError("Multiline RichEdit range semantics are unsupported")
    if foreground_identity() != identity:
        raise OSError("Focus changed during verification")
    return EditorSnapshot(text, start.value, end.value)


def _verified_suffix(identity: WindowIdentity, value: str) -> bool:
    try:
        return _read_editor(identity).has_suffix(value)
    except (OSError, ValueError, UnicodeError):
        return False


def _down(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def _event(vk: int = 0, scan: int = 0, flags: int = 0) -> INPUT:
    return INPUT(type=1, ki=KEYBDINPUT(vk, scan, flags, 0, SELF_INPUT_MARKER))


def _send(events: list[INPUT]) -> None:
    if not events:
        return
    array = (INPUT * len(events))(*events)
    if user32.SendInput(len(array), array, ctypes.sizeof(INPUT)) != len(array):
        raise OSError("Windows refused injected input; elevated applications are unsupported")


def _replace(before: str, after: str) -> None:
    # Native controls disagree on Backspace semantics for CRLF, surrogate pairs,
    # and grapheme clusters. Automatic words are simple BMP text; decline other
    # destructive operations rather than guessing how many characters to erase.
    if len(before) > 8192 or len(after) > 8192:
        raise ValueError("Global replacement exceeds the bounded text limit")
    if any(ch in before for ch in "\r\n\t") or any(ord(ch) > 0xFFFF for ch in before):
        raise ValueError("This text cannot be safely removed using native Backspace")
    events = []
    for _ in before:
        events.extend((_event(8), _event(8, flags=KEYEVENTF_KEYUP)))
    for unit in utf16_units(after):
        events.extend((_event(scan=unit, flags=KEYEVENTF_UNICODE), _event(scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)))
    _send(events)


class WindowsTypingService:
    """Dedicated hook thread with explicit start/stop and application allowlist.

    Callbacks must be quick and thread-safe; they run outside the Tk thread.
    on_status receives generic operational messages, never captured text.
    """

    def __init__(self, decide: Callable[[str], str | None], transform_selection: Callable[[str], str] | None = None,
                 add_word: Callable[[str], None] | None = None, on_status: Callable[[str], None] | None = None,
                 allowed_apps: Iterable[str] = ()):
        self.decide = decide
        self.transform_selection = transform_selection
        self.add_word = add_word
        self.on_status = on_status or (lambda status: None)
        self.allowed_apps = normalize_apps(allowed_apps)
        self.paused = False
        self._thread = None
        self._thread_id = 0
        self._ready = threading.Event()
        self._error = None
        self._word = ""
        self._last_token = None
        self._auto = None
        self._manual = None
        self._identity = WindowIdentity()
        self._generation = 0
        self._suppressed = set()
        self._busy = False
        self._status = "Stopped"

    @property
    def status(self) -> str:
        return self._status

    def _notify(self, value: str) -> None:
        self._status = value
        try:
            self.on_status(value)
        except Exception:
            pass

    def configure(self, allowed_apps: Iterable[str]) -> None:
        self.allowed_apps = normalize_apps(allowed_apps)
        self._reset()

    def set_paused(self, paused: bool) -> None:
        self.paused = bool(paused)
        self._reset()
        self._notify("Paused" if paused else "Listening in allowed applications")

    def _reset(self) -> None:
        self._word = ""
        self._last_token = self._auto = self._manual = None
        self._generation += 1

    def _allowed(self, identity: WindowIdentity) -> bool:
        return bool(identity.app in self.allowed_apps and identity.focus and identity.editable and not identity.password and identity.english_layout)

    def start(self) -> None:
        if not IS_WINDOWS:
            raise OSError("Global typing is available only on Windows")
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(target=self._run, name="AzadTypeKeyboard", daemon=True)
        self._thread.start()
        if not self._ready.wait(5):
            raise OSError("Keyboard service did not initialize")
        if self._error:
            raise self._error

    def stop(self) -> None:
        self._reset()
        self._suppressed.clear()
        if IS_WINDOWS and self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(3)
        self._notify("Stopped")

    def _run(self) -> None:
        keyboard = mouse = None
        try:
            self._thread_id = kernel32.GetCurrentThreadId()
            # Force creation of the message queue before callers can stop us.
            msg = wt.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
            self._key_callback = HOOKPROC(self._keyboard)
            self._mouse_callback = HOOKPROC(self._mouse)
            module = kernel32.GetModuleHandleW(None)
            keyboard = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._key_callback, module, 0)
            mouse = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_callback, module, 0)
            if not keyboard or not mouse:
                raise ctypes.WinError(ctypes.get_last_error())
            self._notify("Listening in allowed applications")
            self._ready.set()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as error:
            self._error = error
            self._notify("Keyboard service unavailable")
            self._ready.set()
        finally:
            if keyboard:
                user32.UnhookWindowsHookEx(keyboard)
            if mouse:
                user32.UnhookWindowsHookEx(mouse)
            self._thread_id = 0
            self._reset()

    def _mouse(self, code, message, data):
        # Movement alone is harmless; clicks/wheels invalidate caret assumptions.
        if code >= 0 and message != 0x200:
            self._reset()
        return user32.CallNextHookEx(None, code, message, data)

    def _keyboard(self, code, message, data):
        try:
            if code >= 0:
                event = ctypes.cast(data, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if event.flags & LLKHF_INJECTED:
                    if event.dwExtraInfo != SELF_INPUT_MARKER:
                        self._reset()
                    return user32.CallNextHookEx(None, code, message, data)
                if self._handle_key(event.vkCode, message):
                    return 1
        except Exception:
            self._reset()
            self._notify("Conversion skipped after input error")
        return user32.CallNextHookEx(None, code, message, data)

    def _handle_key(self, vk: int, message: int) -> bool:
        down = message in {WM_KEYDOWN, WM_SYSKEYDOWN}
        if down and vk in self._suppressed:
            return True  # A held shortcut/undo key performs exactly one action.
        if not down:
            if vk in self._suppressed:
                self._suppressed.discard(vk)
                return True
            return False
        identity = foreground_identity()
        if identity != self._identity:
            self._reset()
            self._identity = identity
        control, alt = _down(VK_CONTROL), _down(VK_MENU)
        if control and alt and vk in HOTKEYS:
            action = HOTKEYS[vk]
            if action == "pause":
                self.set_paused(not self.paused)
            elif not self.paused and self._allowed(identity) and not self._busy:
                self._queue_action(action, identity)
            else:
                return False
            self._suppressed.add(vk)
            return True
        if vk in MODIFIERS:
            return False
        if self.paused or self._busy or not self._allowed(identity):
            self._reset()
            return False
        if control or alt or _down(0x5B) or _down(0x5C) or vk in NAVIGATION:
            self._reset()
            return False
        if vk == 8:
            if self._auto and self._auto.identity == identity and _verified_suffix(identity, self._auto.after):
                item = self._auto
                _replace(item.after, item.before)
                self._reset()
                self._last_token = item.before
                self._suppressed.add(vk)
                self._notify("Automatic conversion undone")
                return True
            self._generation += 1
            self._word = self._word[:-1]
            self._last_token = self._manual = None
            return False
        if vk in {0x20, 0x09, 0x0D}:
            self._generation += 1
            self._auto = self._manual = None
            original, self._word = self._word, ""
            boundary = {0x20: " ", 0x09: "\t", 0x0D: "\r"}[vk]
            # Tabs and Enter can navigate/submit. Never suppress or synthesize them.
            if vk != 0x20:
                self._reset()
                return False
            self._last_token = original + boundary if original else None
            replacement = self.decide(original) if original else None
            if replacement is not None and replacement != original and _verified_suffix(identity, original):
                _replace(original, replacement + boundary)
                self._auto = Replacement(original + boundary, replacement + boundary, identity)
                self._last_token = replacement + boundary
                self._suppressed.add(vk)
                self._notify("Word converted")
                return True
            return False
        char = ascii_key(vk, _down(VK_SHIFT), bool(user32.GetKeyState(0x14) & 1))
        self._generation += 1
        self._auto = self._manual = self._last_token = None
        if char and len(self._word) < 128:
            self._word += char
        else:
            self._word = ""
        return False

    def _queue_action(self, action: str, identity: WindowIdentity) -> None:
        self._busy = True
        generation = self._generation
        word = self._word or self._last_token
        undo = self._manual
        threading.Thread(target=self._action, args=(action, identity, generation, word, undo), name="AzadTypeAction", daemon=True).start()

    def _still_here(self, identity: WindowIdentity, generation: int) -> bool:
        return self._generation == generation and not self.paused and bool(self._thread_id) and foreground_identity() == identity

    def _action(self, action, identity, generation, word, undo) -> None:
        try:
            deadline = time.monotonic() + 2
            while any(_down(vk) for vk in (VK_CONTROL, VK_MENU, VK_SHIFT)):
                if time.monotonic() >= deadline:
                    return
                time.sleep(0.01)
            if not self._still_here(identity, generation):
                return
            if action == "undo":
                if undo and undo.identity == identity and _verified_suffix(identity, undo.after):
                    _replace(undo.after, undo.before)
                    self._reset()
                    self._notify("Manual conversion undone")
                return
            if action == "word":
                if word and self.transform_selection:
                    transformed = self.transform_selection(word)
                    if transformed != word and self._still_here(identity, generation) and _verified_suffix(identity, word):
                        _replace(word, transformed)
                        self._reset()
                        self._manual = Replacement(word, transformed, identity)
                        self._notify("Word converted manually")
                return
            self._selection(action, identity, generation)
        except Exception:
            self._reset()
            self._notify("Action skipped; check selection and supported native editor")
        finally:
            self._busy = False

    def _selection(self, action: str, identity: WindowIdentity, generation: int) -> None:
        if action == "selection" and not self.transform_selection or action == "dictionary" and not self.add_word:
            return
        snapshot = _read_editor(identity)
        selected = snapshot.selected
        if not selected or not self._still_here(identity, generation):
            return
        if action == "dictionary":
            self.add_word(selected)
            self._notify("Selected word added to personal dictionary")
            return
        transformed = self.transform_selection(selected)
        if transformed == selected or not self._still_here(identity, generation):
            return
        if any(len(text) > 8192 or any(ch in text for ch in "\r\n\t") or any(ord(ch) > 0xFFFF for ch in text) for text in (selected, transformed)):
            raise ValueError("Global selection conversion supports bounded single-line BMP text")
        if _read_editor(identity) != snapshot:
            return
        _replace("", transformed)  # Existing native selection is replaced by Unicode input.
        self._reset()
        self._manual = Replacement(selected, transformed, identity)
        self._notify("Selected text converted")
