from __future__ import annotations

from dataclasses import dataclass
import locale


MOJIBAKE_MARKERS = {
    "\ufffd",
    "Ð",
    "Ñ",
    "Ћ",
    "Ў",
    "Є",
    "Ґ",
    "¤",
    "©",
    "«",
    "»",
    "╨",
    "╤",
    "╬",
    "├",
    "┬",
}
UTF8_CYRILLIC_AS_CP866_MARKERS = {"╨", "╤"}

MOJIBAKE_SEQUENCES = (
    "Р°",
    "Р±",
    "РІ",
    "Рі",
    "Рґ",
    "Рµ",
    "Рё",
    "Р№",
    "Рє",
    "Р»",
    "Рј",
    "РЅ",
    "Рѕ",
    "Рї",
    "СЂ",
    "СЃ",
    "С‚",
    "Сѓ",
    "С„",
    "С…",
    "С†",
    "С‡",
    "С€",
    "С‰",
    "С‹",
    "СЊ",
    "СЌ",
    "СЋ",
    "СЏ",
    "С‘",
    "Р”",
    "Рџ",
    "РЎ",
    "Рњ",
    "Рќ",
    "Рћ",
    "Р­",
    "â€¦",
    "â€",
    "â„",
    "â€“",
    "â€”",
    "тА",
    "тВ",
    "тГ",
    "тД",
    "тЕ",
    "тЖ",
    "тЗ",
    "тИ",
    "тК",
    "тЛ",
    "тМ",
    "тН",
    "тО",
    "тП",
    "тР",
    "тС",
    "тТ",
    "тУ",
    "тФ",
    "тХ",
    "тЦ",
    "тЧ",
    "тШ",
    "тЩ",
    "тЪ",
    "тЫ",
    "тЬ",
    "тЭ",
    "тЮ",
    "тЯ",
)

COMMON_RUSSIAN = set("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя")


@dataclass(frozen=True)
class DecodeCandidate:
    text: str
    encoding: str
    score: int


def _candidate_encodings(data: bytes) -> list[str]:
    encodings: list[str] = []

    def add(encoding: str | None) -> None:
        if not encoding:
            return
        normalized = encoding.lower().replace("_", "-")
        if normalized not in encodings:
            encodings.append(normalized)

    add("utf-8")
    if _looks_utf16(data):
        add("utf-16")
        add("utf-16-le")
        add("utf-16-be")
    add("cp866")
    add(locale.getpreferredencoding(False))
    add(locale.getencoding() if hasattr(locale, "getencoding") else None)
    add("mbcs")
    add("cp1251")
    return encodings


def _looks_utf16(data: bytes) -> bool:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return True
    if len(data) < 4:
        return False
    sample = data[: min(len(data), 200)]
    even_nuls = sample[0::2].count(0)
    odd_nuls = sample[1::2].count(0)
    if max(even_nuls, odd_nuls) >= max(2, len(sample) // 5):
        return True
    pairs = max(1, len(sample) // 2)
    utf16_high_bytes = {0, 3, 4}
    even_markers = sum(1 for index in range(0, len(sample), 2) if sample[index] in utf16_high_bytes)
    odd_markers = sum(1 for index in range(1, len(sample), 2) if sample[index] in utf16_high_bytes)
    return max(even_markers, odd_markers) / pairs > 0.35


def _utf16_variant_bytes(data: bytes, encoding: str) -> list[bytes]:
    variants: list[bytes] = []

    def add(candidate: bytes) -> None:
        if candidate and candidate not in variants:
            variants.append(candidate)

    add(data)
    if data.startswith(b"\x00") and len(data) > 1:
        add(data[1:])
    if data.endswith(b"\x00") and len(data) > 1:
        add(data[:-1])

    result: list[bytes] = []
    for candidate in variants:
        result.append(candidate)
        if len(candidate) % 2:
            padded = candidate + b"\x00" if encoding == "utf-16-le" else b"\x00" + candidate
            result.append(padded)
    return result


def _utf16_candidates(data: bytes) -> list[DecodeCandidate]:
    if not _looks_utf16(data):
        return []
    candidates: list[DecodeCandidate] = []
    seen: set[tuple[str, str]] = set()
    for encoding in ("utf-16-le", "utf-16-be"):
        for candidate_data in _utf16_variant_bytes(data, encoding):
            try:
                text = candidate_data.decode(encoding, errors="strict")
            except UnicodeDecodeError:
                continue
            key = (encoding, text)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(DecodeCandidate(text, encoding, _score_text(text, encoding)))
    return candidates


def _score_text(text: str, encoding: str) -> int:
    score = 0
    if encoding == "utf-8":
        score += 20
    for char in text:
        code = ord(char)
        if char in COMMON_RUSSIAN:
            score += 8
        elif char.isascii() and (char.isprintable() or char in "\r\n\t"):
            score += 2
        elif _is_terminal_graphic(char):
            score += 30 if char not in MOJIBAKE_MARKERS else 0
        elif char.isprintable():
            score += 1
        if char in MOJIBAKE_MARKERS:
            score -= 60 if char in UTF8_CYRILLIC_AS_CP866_MARKERS else 20
        if code < 32 and char not in "\r\n\t":
            score -= 30
    score -= text.count("\x00") * 40
    score -= text.count("����") * 80
    for sequence in MOJIBAKE_SEQUENCES:
        score -= text.count(sequence) * 120
    return score


def _is_terminal_graphic(char: str) -> bool:
    code = ord(char)
    return (
        0x2500 <= code <= 0x257F
        or 0x2580 <= code <= 0x259F
        or 0x2800 <= code <= 0x28FF
    )


def decode_process_bytes(data: bytes) -> str:
    if not data:
        return ""

    candidates: list[DecodeCandidate] = _utf16_candidates(data)
    for encoding in _candidate_encodings(data):
        if encoding in {"utf-16-le", "utf-16-be"}:
            continue
        try:
            text = data.decode(encoding, errors="strict")
        except (LookupError, UnicodeDecodeError):
            continue
        candidates.append(DecodeCandidate(text, encoding, _score_text(text, encoding)))

    if candidates:
        return max(candidates, key=lambda candidate: candidate.score).text
    return data.decode("utf-8", errors="replace")


def decode_process_output(data: bytes) -> str:
    return decode_process_bytes(data)
