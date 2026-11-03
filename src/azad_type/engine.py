"""Conservative, deterministic Persian physical-key conversion.

This is a vocabulary-backed heuristic, not a language model. It neither hooks
keyboards nor performs I/O, and returns its reason for every automatic decision.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .dictionary import Dictionary, normalize


# Physical keys on a US QWERTY keyboard, following the common Windows Persian
# letter positions. Whitespace and unlisted characters are preserved.
QWERTY_TO_PERSIAN = dict(zip(
    "qwertyuiop[]asdfghjkl;'zxcvbnm,",
    "ضصثقفغعهخحجچشسیبلاتنمکگظطزرذدپو",
))
PERSIAN_TO_QWERTY = {value: key for key, value in QWERTY_TO_PERSIAN.items()}
_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_PUNCTUATION = str.maketrans({",": "،", "?": "؟", ";": "؛"})
_PERSIAN = re.compile(r"[\u0621-\u063a\u0641-\u064a\u067e\u0686\u0698\u06a9\u06af\u06cc]")
_TECHNICAL = re.compile(r"(?:https?://|www\.|@|[/\\_:=+#]|\w\.\w|\d)", re.IGNORECASE)
_LATIN = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class Settings:
    auto_convert: bool = True
    min_word_length: int = 3
    persian_digits: bool = False
    persian_punctuation: bool = False

    def __post_init__(self) -> None:
        if not 2 <= self.min_word_length <= 20:
            raise ValueError("min_word_length must be between 2 and 20.")


@dataclass(frozen=True)
class Decision:
    original: str
    output: str
    converted: bool
    reason: str
    confidence: float


def to_persian(text: str) -> str:
    """Map letter keys, preserving case-independent physical positions."""
    return "".join(QWERTY_TO_PERSIAN.get(character.lower(), character) for character in text)


def to_english(text: str) -> str:
    normalized = text.translate(str.maketrans({"ي": "ی", "ك": "ک", "ى": "ی"}))
    return "".join(PERSIAN_TO_QWERTY.get(character, character) for character in normalized)


class Engine:
    def __init__(self, dictionary: Dictionary | None = None, settings: Settings | None = None):
        self.dictionary = dictionary if dictionary is not None else Dictionary()
        self.settings = settings if settings is not None else Settings()

    def _format(self, text: str) -> str:
        if self.settings.persian_digits:
            text = text.translate(_DIGITS)
        if self.settings.persian_punctuation:
            text = text.translate(_PUNCTUATION)
        return text

    def decide(self, token: str, previous_persian: bool = False) -> Decision:
        """Decide a completed whitespace-delimited token.

        Known English wins even when both spellings could be words. A two-key
        Persian word requires previous Persian context. Unknown words remain
        unchanged, so specialist vocabulary should be added by the user.
        """
        if not token:
            return Decision(token, token, False, "empty", 1.0)
        if not self.settings.auto_convert:
            return Decision(token, token, False, "paused", 1.0)
        if _PERSIAN.search(token):
            if _LATIN.search(token):
                return Decision(token, token, False, "mixed-script", 1.0)
            output = self._format(normalize(token))
            return Decision(token, output, output != token, "already-persian", 1.0)
        if token.isdecimal() and previous_persian and self.settings.persian_digits:
            output = token.translate(_DIGITS)
            return Decision(token, output, output != token, "persian-context-digits", 0.9)
        if _TECHNICAL.search(token):
            return Decision(token, token, False, "technical-token", 1.0)
        # English punctuation wrappers should not defeat English protection.
        english_core = token.strip('"“”(){}[]<>.,!?;:\'')
        if self.dictionary.contains(english_core, "en"):
            return Decision(token, token, False, "protected-english", 1.0)
        if len(english_core) > 1 and (english_core.isupper() or any(character.isupper() for character in english_core[1:])):
            return Decision(token, token, False, "identifier-case", 0.95)

        # Prefer a complete mapped word. Comma, brackets, semicolon, and quote
        # are also Persian letter keys, so stripping them unconditionally loses
        # legitimate words. Only try punctuation stripping after a full miss.
        candidates: list[tuple[str, str, str]] = [("", token, "")]
        left, right = 0, len(token)
        while left < right and token[left] in '"“”({<':
            left += 1
        while right > left and token[right - 1] in '"”)}>.!?,;:\'':
            right -= 1
        if left or right != len(token):
            candidates.append((token[:left], token[left:right], token[right:]))
        for prefix, core, suffix in candidates:
            if not core or not _LATIN.search(core) or any(character.lower() not in QWERTY_TO_PERSIAN for character in core):
                continue
            mapped = to_persian(core)
            if not self.dictionary.contains(mapped, "fa"):
                continue
            letter_count = len(core)
            if letter_count < self.settings.min_word_length:
                if letter_count < 2 or not previous_persian:
                    return Decision(token, token, False, "short-word-needs-context", 0.5)
                confidence, reason = 0.8, "dictionary-with-context"
            else:
                confidence, reason = 0.95, "persian-dictionary"
            output = prefix + mapped + self._format(suffix)
            return Decision(token, output, output != token, reason, confidence)
        return Decision(token, token, False, "no-dictionary-evidence", 0.0)

    def convert_text(self, text: str, automatic: bool = True) -> str:
        """Convert a text while preserving its exact whitespace.

        Context ends at line boundaries or an English token. This is a batch
        helper; the desktop backend calls ``decide`` for each completed token.
        """
        if not automatic:
            return self.manual_convert(text)
        output: list[str] = []
        previous_persian = False
        for piece in re.split(r"(\s+)", text):
            if piece.isspace():
                output.append(piece)
                if "\n" in piece or "\r" in piece:
                    previous_persian = False
                continue
            decision = self.decide(piece, previous_persian=previous_persian)
            output.append(decision.output)
            if piece:
                previous_persian = bool(_PERSIAN.search(decision.output))
        return "".join(output)

    def manual_convert(self, text: str, direction: str = "toggle") -> str:
        """Force layout mapping. No English/URL protection is applied.

        ``toggle`` chooses Persian-to-English when Persian letters are present;
        pass ``fa`` or ``en`` to choose the output alphabet explicitly.
        """
        if direction not in {"toggle", "fa", "en"}:
            raise ValueError("direction must be 'toggle', 'fa', or 'en'.")
        if direction == "en" or (direction == "toggle" and _PERSIAN.search(text)):
            return to_english(text)
        return self._format(to_persian(text))
