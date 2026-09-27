"""Calendar consistency (POL-C): weekday names written next to dates are recomputed, never trusted.

`weekday_mismatches(text, today)` finds a weekday named together with a date ("в воскресенье 5-го",
"Sunday, October 5", "2026-10-05 (Sunday)") or with a relative day ("завтра, в понедельник") and
returns the pairs that disagree with the real calendar. Dates without a year resolve to the year
that puts them closest to `today`; a bare ordinal day ("5-го", "the 5th") is accepted if any
nearby month makes the weekday right.

`mentions_date(text, d)` tells whether a text names a given date in any supported form; it is used
to check that a decision summary names a changed milestone date.
"""
import re
from dataclasses import dataclass
from datetime import date, timedelta

EN_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_RU_WEEKDAYS = [
    r"понедельник(?:а|у|ом|е)?", r"вторник(?:а|у|ом|е)?", r"сред(?:а|ы|у|е|ой)", r"четверг(?:а|у|ом|е)?",
    r"пятниц(?:а|ы|у|е|ей)", r"суббот(?:а|ы|у|е|ой)", r"воскресень(?:е|я|ю|ем)",
]
_WEEKDAY_RE = re.compile(
    r"\b(?:" + "|".join(f"(?P<w{i}>{EN_WEEKDAYS[i]}|{_RU_WEEKDAYS[i]})" for i in range(7)) + r")\b", re.IGNORECASE)

_EN_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
              "october", "november", "december"]
_EN_MONTH_ABBR = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sept?", "oct", "nov", "dec"]
_RU_MONTHS = [r"январ[яьею]", r"феврал[яьею]", r"март[аеу]?", r"апрел[яьею]", r"ма[яйею]", r"июн[яьею]",
              r"июл[яьею]", r"август[аеу]?", r"сентябр[яьею]", r"октябр[яьею]", r"ноябр[яьею]", r"декабр[яьею]"]
_MONTH_ALT = "|".join(f"(?P<m{i + 1}>{_EN_MONTHS[i]}|{_EN_MONTH_ABBR[i]}\\.?|{_RU_MONTHS[i]})" for i in range(12))
_MONTH_ALT2 = _MONTH_ALT.replace("(?P<m", "(?P<n")

_ORD = r"(?:-?(?:го|е|th|st|nd|rd))"
_DATE_RES = [
    ("iso", re.compile(r"\b(?P<year>20\d\d)-(?P<month>\d\d)-(?P<day>\d\d)\b")),
    ("dm_name", re.compile(r"\b(?P<day>\d{1,2})" + _ORD + r"?\s+(?:of\s+)?(?:" + _MONTH_ALT + r")(?:\s+(?P<year>20\d\d))?\b", re.IGNORECASE)),
    ("md_name", re.compile(r"\b(?:" + _MONTH_ALT2 + r")\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(?P<year>20\d\d))?(?!\s*(?:h\b|hours?|:|\d))", re.IGNORECASE)),
    ("numeric", re.compile(r"\b(?P<day>\d{1,2})\.(?P<month>\d{2})(?:\.(?P<year>20\d\d))?\b")),
    ("ordinal", re.compile(r"\b(?P<day>\d{1,2})" + _ORD + r"\b", re.IGNORECASE)),
]
_RELATIVE_RE = re.compile(r"\b(?P<rel>сегодня|завтра|послезавтра|today|tomorrow)\b", re.IGNORECASE)
_NEXT_RE = re.compile(r"\b(next|следующ\w*)\b", re.IGNORECASE)
_RELATIVE_OFFSET = {"сегодня": 0, "today": 0, "завтра": 1, "tomorrow": 1, "послезавтра": 2}
# What may stand between a weekday and the date it labels: punctuation and a preposition/article.
_GAP_RE = re.compile(r"^[\s,;:()\[\]\-–—]*(?:(?:the|on|a|an|в|во|это|is)\s+)?[\s,;:()\[\]\-–—]*$", re.IGNORECASE)


@dataclass(frozen=True)
class DateMention:
    start: int
    end: int
    kind: str
    day: int
    month: int = None
    year: int = None


@dataclass(frozen=True)
class WeekdayMismatch:
    snippet: str
    stated: str
    candidates: tuple  # dates the expression can mean; none of them has the stated weekday

    def message(self):
        real = ", ".join(f"{d.isoformat()} is a {EN_WEEKDAYS[d.weekday()].capitalize()}" for d in self.candidates)
        return f"«{self.snippet}» names {self.stated.capitalize()}, but {real}"


def _weekday_mentions(text):
    for m in _WEEKDAY_RE.finditer(text):
        wd = next(i for i in range(7) if m.group(f"w{i}"))
        yield m.start(), m.end(), wd


def _month_of(m):
    for i in range(1, 13):
        for prefix in ("m", "n"):
            if m.groupdict().get(f"{prefix}{i}"):
                return i
    month = m.groupdict().get("month")
    return int(month) if month else None


def date_mentions(text):
    """All date expressions in `text`, longest match first where they overlap."""
    found = []
    for kind, rx in _DATE_RES:
        for m in rx.finditer(text or ""):
            day = int(m.group("day"))
            month = _month_of(m)
            year = int(m.group("year")) if m.groupdict().get("year") else None
            if not 1 <= day <= 31 or (month is not None and not 1 <= month <= 12):
                continue
            found.append(DateMention(m.start(), m.end(), kind, day, month, year))
    found.sort(key=lambda d: (d.start, -(d.end - d.start)))
    out = []
    for d in found:
        if out and d.start < out[-1].end:
            continue
        out.append(d)
    return out


def resolve(mention, today):
    """Candidate calendar dates for a mention relative to `today`."""
    if mention.month and mention.year:
        try:
            return [date(mention.year, mention.month, mention.day)]
        except ValueError:
            return []
    if mention.month:
        cands = []
        for y in (today.year - 1, today.year, today.year + 1):
            try:
                cands.append(date(y, mention.month, mention.day))
            except ValueError:
                pass
        return sorted(cands, key=lambda d: abs((d - today).days))[:1]
    cands = []
    for add in (-1, 0, 1, 2):
        y, mth = today.year, today.month + add
        while mth > 12:
            mth, y = mth - 12, y + 1
        while mth < 1:
            mth, y = mth + 12, y - 1
        try:
            d = date(y, mth, mention.day)
        except ValueError:
            continue
        if today - timedelta(days=7) <= d <= today + timedelta(days=62):
            cands.append(d)
    return cands


def _gap_ok(text, a, b):
    return 0 <= b - a <= 12 and bool(_GAP_RE.match(text[a:b]))


def _snippet(text, a, b, pad=12):
    return text[max(0, a - pad):min(len(text), b + pad)].strip()


def weekday_mismatches(text, today):
    """Weekday + date (or relative day) pairs in `text` that contradict the calendar."""
    if not text or not isinstance(today, date):
        return []
    dates = date_mentions(text)
    rels = [(m.start(), m.end(), _RELATIVE_OFFSET[m.group("rel").lower()]) for m in _RELATIVE_RE.finditer(text)]
    out = []
    for ws, we, wd in _weekday_mentions(text):
        paired = None
        for d in dates:
            if _gap_ok(text, we, d.start) or _gap_ok(text, d.end, ws):
                paired = d
                break
        if paired is not None:
            cands = resolve(paired, today)
            if paired.kind == "ordinal" and not cands:
                continue
            if cands and not any(c.weekday() == wd for c in cands):
                out.append(WeekdayMismatch(_snippet(text, min(ws, paired.start), max(we, paired.end)),
                                           EN_WEEKDAYS[wd], tuple(cands)))
            continue
        for rs, re_, off in rels:
            if _gap_ok(text, re_, ws) or _gap_ok(text, we, rs):
                d = today + timedelta(days=off)
                if d.weekday() != wd:
                    out.append(WeekdayMismatch(_snippet(text, min(ws, rs), max(we, re_)), EN_WEEKDAYS[wd], (d,)))
                break
    return out


_RU_MONTH_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября",
                 "октября", "ноября", "декабря"]


def mentions_date(text, d, today=None):
    """True if `text` names date `d` (ISO, '23 ноября', 'November 23', '23.11', ...)."""
    if not text or d is None:
        return False
    if d.isoformat() in text:
        return True
    today = today or d
    for m in date_mentions(text):
        if m.kind == "ordinal":
            continue
        if any(c == d for c in resolve(m, today)):
            return True
    return False


def weekday_names_in(text):
    """Weekday indices named in `text`."""
    return {wd for _, _, wd in _weekday_mentions(text or "")}


def date_grounded(text, d, today):
    """True if `text` supports the calendar date `d`: it names the date, names the weekday of the
    nearest such day ("до пятницы"; a week later only with "next"/"следующ"), or says today/tomorrow."""
    if mentions_date(text, d, today):
        return True
    if today is None:
        return False
    delta = (d - today).days
    horizon = 14 if _NEXT_RE.search(text or "") else 7
    if 0 < delta <= horizon and d.weekday() in weekday_names_in(text):
        return True
    for m in _RELATIVE_RE.finditer(text or ""):
        if _RELATIVE_OFFSET[m.group("rel").lower()] == delta:
            return True
    return False


def weeks_between(a, b):
    return (b - a).days / 7
