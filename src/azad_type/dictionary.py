"""Local vocabulary for Azad Type. No vendor dictionaries are included.

The small seed lists below were written for this project. They are deliberately
conservative; importing a larger, appropriately licensed vocabulary is optional.
"""
from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata


def normalize(word: str) -> str:
    return unicodedata.normalize("NFC", word).translate(str.maketrans({"ي": "ی", "ك": "ک", "ى": "ی"})).strip()


# Original, intentionally limited vocabulary; not a full Persian dictionary.
SEED_PERSIAN = frozenset("""
سلام درود خداحافظ صبح شب روز امروز فردا دیروز خوب خوبی خوبم خوبیها خوش
خانه زندگی شهر کشور ایران جهان فارسی زبان انگلیسی نوشتن نوشتار خواندن
کتاب نامه متن واژه کلمه جمله نوشته نویسنده خواننده رایانه کامپیوتر
کیبورد صفحه کلید برنامه نرم افزار اینترنت شبکه فایل پوشه سند تصویر عکس
من تو او ما شما ایشان این آن اینجا آنجا کجا چرا چطور چگونه چه کی
هست هستم هستی هستیم هستید هستند بود بودم بودی بودیم بودید بودند باشد
است نیست نبود باش باشم باشی باشید باشیم باشند بودن شدن شود شد شده
دارم داری دارد داریم دارید دارند داشتن داشت داشتم داشتند ندارم ندارد
کرد کردم کردی کردیم کردید کردند کردن کند کنم کنی کنیم کنید کنند
کار درست اشتباه باز بسته آغاز پایان شروع توقف ادامه افزودن حذف ذخیره
بازگشت تنظیم تنظیمات ابزار کمک راهنما درباره نسخه آزاد آزادی محلی
امنیت خصوصی شخصی داده اطلاعات ارتباط خبر گزارش پیام پاسخ سوال پرسش
بله آری نه خیر لطفا ممنون سپاس تشکر خواهش دوست دوستان عزیز گرامی
خانواده مادر پدر خواهر برادر فرزند کودک مرد زن انسان مردم نام نامها
زمان ساعت دقیقه ثانیه هفته ماه سال شنبه یکشنبه دوشنبه سهشنبه چهارشنبه
پنجشنبه جمعه بهار تابستان پاییز زمستان باران برف باد هوا آسمان زمین
آب آتش خاک نور تاریکی روشن خورشید ماه ستاره دریا رود کوه دشت باغ
گل درخت سبز آبی قرمز زرد سیاه سفید رنگ کوچک بزرگ بلند کوتاه نزدیک
دور بالا پایین چپ راست جلو پشت اول آخر بعد قبل همیشه هرگز اکنون
هنوز خیلی کمی بیشتر کمتر همه هیچ بعضی دیگر دوباره فقط نیز هم اما
اگر چون برای بر با بدون به از در تا یا و را که یخ یک دو سه چهار پنج شش
هفت هشت نه ده صد هزار میلیون عدد شماره قیمت پول تومان ریال خرید
فروش پرداخت حساب بانک بازار فروشگاه دانشگاه مدرسه دانش آموز دانشجو
استاد معلم درس آموزش یاد یادگیری دانش علم تجربه تلاش نتیجه هدف
فکر اندیشه نظر انتخاب گزینه امکان ویژگی کیفیت سرعت ساده آسان سخت
تازه قدیمی جدید زیبا آرام سریع مهم لازم ممکن بهتر بهترین طبیعی
فرهنگ هنر موسیقی فیلم داستان شعر بازی سفر مسیر راه خیابان کوچه
ماشین خودرو قطار هواپیما دوچرخه غذا نان برنج چای قهوه میوه سیب
دست پا سر چشم گوش دهان قلب بدن سالم سلامت خوشحال ناراحت خسته
امید عشق شادی لبخند مهربان دیدن گفتن شنیدن رفتن آمدن رسیدن گرفتن
دادن آوردن ساختن شناختن خواستن توانستن دانستن فهمیدن گفت رفت آمد
ببین بگو بیا برو بنویس بخوان بخواه بدان بدانم خوبید خوبند خوشبخت
می‌روم می‌رود می‌روند می‌کنم می‌کنی می‌کند می‌کنیم می‌کنید می‌کنند
می‌شود می‌شوم می‌شوی می‌شویم می‌شوید می‌شوند می‌خواهم می‌خواهی
می‌خواهد می‌خواهیم می‌خواهید می‌خواهند نمی‌شود نمی‌کنم نمی‌کند
توانایی پشتیبانی ترجمه تغییر تبدیل متنها کلیدها واژگان واژه‌نامه
""".split())

SEED_ENGLISH = frozenset("""
a about above after again against all also am an and any api app apple are
as ask at away back bad be because been before being below between big both
but by call can cannot case change check child clear close code come could
data day debug default delete did different do does doing done down each
edit else end enter error even ever every example exit false far few file
find first for form found four free from full function get give go good got
great had has have having he hello help her here hers herself him himself his
home how i id if import in info input inside install instead int into is it
its itself just keep key kind know last later left less let like line list
little local long look made make many may me more most much must my myself
name need never new next no none nor not nothing now number of off old on once
one only open or other our ours ourselves out over own part path pause people
please point print program put python read ready real red remove restart return
right run said same save say second see select set settings she should show
side since small so some something source start state still stop string such
system take test than that the their theirs them themselves then there these
they thing think this those through time to too true try two type under undo
unit until up update us use used user using value very want was way we web well
were what when where which while white who why will with without word work
world would write wrong yes yet you your yours yourself yourselves
ajax android angular array ascii azure bash binary bit bool boolean branch
break build byte cache callback caps char chat chrome class cli client cloud
cmd commit config console const cookie cpu css csv cursor database desktop
dev dict diff django dll dns docker dotnet download editor email enum env
eslint exception exe export firefox float font format framework frontend
git github gitlab gmail gnu google gpu graphql gui hash html http https icon
ide image init interface ios ip java javascript json jwt kernel lambda linux
localhost log login mac macos markdown memory merge microsoft module ms npm
node null object package pandas parameter password pdf php pip plugin port
postgres process promise protocol pull push query react readonly redis repo
request response rest route ruby rust schema script sdk search server service
session shell shift shortcut smtp socket sql sqlite ssh ssl stack static
status store struct sudo swift sync table task tcp terminal thread timeout
token toolbar tuple txt typescript ubuntu ui unicode unix upload url utf var
vector version view virtual vm vscode vue webpack wifi win windows xml yaml
zsh zoom api http tcp udp lan vpn ssh tls sdk usb html css sql gui uuid sha
""".split())

_LANGUAGES = {"fa", "en"}
_MAX_FILE_BYTES = 10 * 1024 * 1024
_MAX_WORDS = 100_000


def validate_word(word: object, language: str) -> str:
    if language not in _LANGUAGES:
        raise ValueError("Language must be 'fa' or 'en'.")
    if not isinstance(word, str):
        raise ValueError("Every dictionary entry must be a string.")
    word = normalize(word)
    if not word or len(word) > 128 or any(ch.isspace() or unicodedata.category(ch) == "Cc" for ch in word):
        raise ValueError("Entries must be single words of at most 128 characters.")
    if language == "fa" and not re.fullmatch(r"[\u0621-\u063a\u0641-\u064a\u067e\u0686\u0698\u06a9\u06af\u06cc\u200c]+", word):
        raise ValueError("Persian entries may contain Persian/Arabic letters and a zero-width non-joiner.")
    if language == "en":
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_+.#-]*", word):
            raise ValueError("Protected entries must be Latin words or technical identifiers.")
        word = word.casefold()
    return word


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Dictionary:
    """Original seeds plus separately stored personal entries.

    ``path=None`` means in-memory only. Import validates every record before
    changing memory or disk. Exports contain only personal entries.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else None
        self._personal = {"fa": set(), "en": set()}
        if self.path is not None and self.path.exists():
            self._personal = self._parse_file(self.path)

    @property
    def persian_words(self) -> frozenset[str]:
        return SEED_PERSIAN | frozenset(self._personal["fa"])

    @property
    def protected_words(self) -> frozenset[str]:
        return SEED_ENGLISH | frozenset(self._personal["en"])

    @property
    def personal_words(self) -> dict[str, list[str]]:
        return {language: sorted(words) for language, words in self._personal.items()}

    def contains(self, word: str, language: str = "fa") -> bool:
        if language not in _LANGUAGES:
            raise ValueError("Language must be 'fa' or 'en'.")
        word = normalize(word)
        if language == "fa":
            return word in SEED_PERSIAN or word in self._personal["fa"]
        word = word.casefold()
        return word in SEED_ENGLISH or word in self._personal["en"]

    def add(self, word: str, language: str = "fa") -> None:
        word = validate_word(word, language)
        candidate = {key: set(values) for key, values in self._personal.items()}
        candidate[language].add(word)
        self._commit(candidate)

    def remove(self, word: str, language: str = "fa") -> None:
        word = validate_word(word, language)
        candidate = {key: set(values) for key, values in self._personal.items()}
        candidate[language].discard(word)
        self._commit(candidate)

    def _commit(self, candidate: dict[str, set[str]]) -> None:
        if self.path is not None:
            atomic_json(self.path, {"version": 1, **{key: sorted(values) for key, values in candidate.items()}})
        self._personal = candidate

    def save(self) -> None:
        self._commit(self._personal)

    @staticmethod
    def _parse_file(path: Path) -> dict[str, set[str]]:
        if path.stat().st_size > _MAX_FILE_BYTES:
            raise ValueError("Dictionary files may not exceed 10 MiB.")
        text = path.read_text(encoding="utf-8-sig")
        suffix = path.suffix.lower()
        entries: list[tuple[object, str]] = []
        if suffix == ".json":
            data = json.loads(text)
            if not isinstance(data, dict) or any(key not in {"version", "fa", "en"} for key in data):
                raise ValueError("JSON must contain 'fa' and/or 'en' word arrays and optional version 1.")
            if data.get("version", 1) != 1:
                raise ValueError("Unsupported dictionary version.")
            for language in ("fa", "en"):
                words = data.get(language, [])
                if not isinstance(words, list):
                    raise ValueError("Dictionary language fields must be arrays.")
                entries.extend((word, language) for word in words)
        elif suffix == ".csv":
            reader = csv.DictReader(io.StringIO(text))
            if reader.fieldnames != ["word", "language"]:
                raise ValueError("CSV header must be word,language.")
            for row in reader:
                if None in row or row.get("word") is None or row.get("language") is None:
                    raise ValueError("Invalid CSV row.")
                entries.append((row["word"], row["language"]))
        elif suffix == ".txt":
            # Explicit language prefixes make exports round-trip unambiguously;
            # unprefixed lines are inferred from their alphabet.
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(("fa\t", "en\t")):
                    language, word = line.split("\t", 1)
                else:
                    word = line
                    language = "fa" if re.search(r"[\u0600-\u06ff]", word) else "en"
                entries.append((word, language))
        else:
            raise ValueError("Choose a JSON, CSV, or TXT dictionary file.")
        if len(entries) > _MAX_WORDS:
            raise ValueError("Dictionary files may contain at most 100,000 entries.")
        result: dict[str, set[str]] = {"fa": set(), "en": set()}
        for word, language in entries:
            checked = validate_word(word, language)
            result[language].add(checked)
        return result

    def import_file(self, path: str | Path) -> int:
        imported = self._parse_file(Path(path))
        candidate = {key: self._personal[key] | imported[key] for key in _LANGUAGES}
        added = sum(len(candidate[key] - self._personal[key]) for key in _LANGUAGES)
        self._commit(candidate)
        return added

    def export_file(self, path: str | Path) -> None:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            atomic_json(path, {"version": 1, **self.personal_words})
            return
        output = io.StringIO(newline="")
        if suffix == ".csv":
            writer = csv.writer(output)
            writer.writerow(("word", "language"))
            for language in ("fa", "en"):
                writer.writerows((word, language) for word in sorted(self._personal[language]))
        elif suffix == ".txt":
            for language in ("fa", "en"):
                for word in sorted(self._personal[language]):
                    output.write(f"{language}\t{word}\n")
        else:
            raise ValueError("Choose a JSON, CSV, or TXT dictionary file.")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                stream.write(output.getvalue())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
