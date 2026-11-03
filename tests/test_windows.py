"""Nonintrusive Win32 adapter tests. No hook or input injection is performed."""
import ctypes
import unittest
from unittest.mock import Mock, patch

from azad_type import windows as win


class HelpersTests(unittest.TestCase):
    def test_allowlist_is_explicit_and_rejects_paths(self):
        self.assertEqual(win.normalize_apps([]), frozenset())
        self.assertEqual(win.normalize_apps([" Notepad.EXE ", "notepad.exe"]), {"notepad.exe"})
        for bad in ("C:\\Windows\\notepad.exe", "../notepad.exe", "notepad"):
            with self.assertRaises(ValueError):
                win.normalize_apps([bad])

    def test_qwerty_letters_symbols_and_caps(self):
        self.assertEqual(win.ascii_key(0x53, False), "s")
        self.assertEqual(win.ascii_key(0x53, True), "S")
        self.assertEqual(win.ascii_key(0x53, True, True), "s")
        self.assertEqual(win.ascii_key(0xBA, False), ";")
        self.assertEqual(win.ascii_key(0xBF, True), "?")
        self.assertIsNone(win.ascii_key(0x70, False))

    def test_editor_offsets_use_utf16_and_require_collapsed_caret(self):
        snapshot = win.EditorSnapshot("a\U0001f642hello", 3, 8)
        self.assertEqual(snapshot.selected, "hello")
        self.assertFalse(snapshot.has_suffix("hello"))
        self.assertTrue(win.EditorSnapshot("a\U0001f642hello", 8, 8).has_suffix("hello"))

    def test_utf16_supplementary_character_is_two_units(self):
        self.assertEqual(win.utf16_units("a\U0001f642"), [97, 0xD83D, 0xDE42])

    def test_default_service_has_no_allowlist_and_does_not_start(self):
        service = win.WindowsTypingService(lambda word: "x")
        self.assertFalse(service.allowed_apps)
        self.assertIsNone(service._thread)
        self.assertEqual(service.status, "Stopped")

    def test_known_password_readonly_and_unknown_fields_are_denied(self):
        service = win.WindowsTypingService(lambda word: None, allowed_apps=["notepad.exe"])
        supported = win.WindowIdentity(1, 2, "notepad.exe", False, True, True, "edit")
        self.assertTrue(service._allowed(supported))
        self.assertFalse(service._allowed(win.WindowIdentity(1, 2, "notepad.exe", True, True, True, "edit")))
        self.assertFalse(service._allowed(win.WindowIdentity(1, 2, "notepad.exe", False, True, False, "edit")))
        self.assertFalse(service._allowed(win.WindowIdentity(1, 2, "notepad.exe", False, True, False, "custom")))
        self.assertFalse(service._allowed(win.WindowIdentity(1, 2, "other.exe", False, True, True, "edit")))
        self.assertFalse(service._allowed(win.WindowIdentity(1, 2, "notepad.exe", False, False, True, "edit")))


@unittest.skipUnless(win.IS_WINDOWS, "Win32 adapter state tests")
class StateTests(unittest.TestCase):
    def setUp(self):
        self.identity = win.WindowIdentity(1, 2, "notepad.exe", False, True, True, "edit")
        self.service = win.WindowsTypingService(lambda raw: "\u0633\u0644\u0627\u0645" if raw == "sghl" else None, allowed_apps=["notepad.exe"])
        self.service._identity = self.identity
        self.service._thread_id = 1
        self.focus = patch.object(win, "foreground_identity", return_value=self.identity)
        self.down = patch.object(win, "_down", return_value=False)
        self.fake_user = patch.object(win, "user32", GetKeyState=Mock(return_value=0))
        self.focus.start()
        self.down.start()
        self.fake_user.start()
        self.addCleanup(patch.stopall)

    def test_space_replacement_is_suppressed_only_after_suffix_verification(self):
        self.service._word = "sghl"
        with patch.object(win, "_verified_suffix", return_value=True), patch.object(win, "_replace") as replace:
            self.assertTrue(self.service._handle_key(0x20, win.WM_KEYDOWN))
            replace.assert_called_once_with("sghl", "\u0633\u0644\u0627\u0645 ")
            self.assertEqual(self.service._auto.before, "sghl ")
            self.assertTrue(self.service._handle_key(0x20, win.WM_KEYUP))

    def test_mismatching_suffix_passes_physical_space_without_injection(self):
        self.service._word = "sghl"
        with patch.object(win, "_verified_suffix", return_value=False), patch.object(win, "_replace") as replace:
            self.assertFalse(self.service._handle_key(0x20, win.WM_KEYDOWN))
            replace.assert_not_called()

    def test_tabs_and_enter_never_get_synthesized_or_suppressed(self):
        for vk in (0x09, 0x0D):
            self.service._word = "sghl"
            with patch.object(win, "_replace") as replace:
                self.assertFalse(self.service._handle_key(vk, win.WM_KEYDOWN))
                replace.assert_not_called()

    def test_backspace_undo_is_immediate_and_verified(self):
        self.service._auto = win.Replacement("sghl ", "\u0633\u0644\u0627\u0645 ", self.identity)
        with patch.object(win, "_verified_suffix", return_value=True), patch.object(win, "_replace") as replace:
            self.assertTrue(self.service._handle_key(8, win.WM_KEYDOWN))
            replace.assert_called_once_with("\u0633\u0644\u0627\u0645 ", "sghl ")
            self.assertIsNone(self.service._auto)

    def test_mouse_and_navigation_invalidate_undo_and_word(self):
        self.service._word = "sghl"
        self.service._auto = win.Replacement("a", "b", self.identity)
        self.assertFalse(self.service._handle_key(0x25, win.WM_KEYDOWN))
        self.assertEqual(self.service._word, "")
        self.assertIsNone(self.service._auto)

    def test_selection_reads_native_control_and_does_not_use_clipboard(self):
        self.service.transform_selection = lambda text: text.upper()
        snap = win.EditorSnapshot("hello", 0, 5)
        with patch.object(win, "_read_editor", return_value=snap), patch.object(win, "_replace") as replace:
            self.service._selection("selection", self.identity, self.service._generation)
            replace.assert_called_once_with("", "HELLO")
            self.assertEqual(self.service._manual.before, "hello")

    def test_changed_selection_cancels_replacement(self):
        self.service.transform_selection = lambda text: text.upper()
        with patch.object(win, "_read_editor", side_effect=[win.EditorSnapshot("hello", 0, 5), win.EditorSnapshot("hello", 5, 5)]), patch.object(win, "_replace") as replace:
            self.service._selection("selection", self.identity, self.service._generation)
            replace.assert_not_called()

    def test_native_input_layout_matches_windows_abi(self):
        self.assertEqual(ctypes.sizeof(win.INPUT), 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
        self.assertEqual(win.INPUT.value.offset, 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 4)
        self.assertEqual(win._event(65).ki.dwExtraInfo, win.SELF_INPUT_MARKER)

    def test_unknown_and_password_controls_are_never_read(self):
        with patch.object(win, "_message") as message:
            for identity in (win.WindowIdentity(1, 2, "notepad.exe", False, True, False, "custom"), win.WindowIdentity(1, 2, "notepad.exe", True, True, True, "edit")):
                with self.assertRaises(OSError):
                    win._read_editor(identity)
            message.assert_not_called()

    def test_held_pause_shortcut_only_toggles_once_until_keyup(self):
        with patch.object(win, "_down", side_effect=lambda key: key in (win.VK_CONTROL, win.VK_MENU)):
            self.assertTrue(self.service._handle_key(0x50, win.WM_KEYDOWN))
            self.assertTrue(self.service.paused)
            self.assertTrue(self.service._handle_key(0x50, win.WM_KEYDOWN))
            self.assertTrue(self.service.paused)
            self.assertTrue(self.service._handle_key(0x50, win.WM_KEYUP))
            self.assertTrue(self.service._handle_key(0x50, win.WM_KEYDOWN))
            self.assertFalse(self.service.paused)

    def test_external_injected_input_invalidates_state(self):
        self.service._word = "sghl"
        event = win.KBDLLHOOKSTRUCT(65, 0, win.LLKHF_INJECTED, 0, 1234)
        self.service._keyboard(0, win.WM_KEYDOWN, ctypes.addressof(event))
        self.assertEqual(self.service._word, "")
        self.service._word = "sghl"
        event.dwExtraInfo = win.SELF_INPUT_MARKER
        self.service._keyboard(0, win.WM_KEYDOWN, ctypes.addressof(event))
        self.assertEqual(self.service._word, "sghl")


if __name__ == "__main__":
    unittest.main()
