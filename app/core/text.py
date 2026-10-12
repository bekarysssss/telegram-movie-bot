import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]|_", re.UNICODE)


def _strip_accents(s: str) -> str:
    """Убирает диакритику только у латиницы (чтобы не превратить «й» в «и»)."""
    out = []
    for ch in s:
        if ord(ch) < 0x250:
            ch = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
        out.append(ch)
    return "".join(out)


def normalize_text(s: str | None) -> str:
    """Нижний регистр, ё→е, без диакритики и пунктуации, схлопнутые пробелы."""
    if not s:
        return ""
    s = _strip_accents(s.lower().replace("ё", "е"))
    return " ".join(_PUNCT.sub(" ", s).split())
