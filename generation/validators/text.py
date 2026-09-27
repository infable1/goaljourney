"""Text heuristics shared by validators and evaluation checks."""
import re

_CYR = re.compile(r"[А-Яа-яЁё]")
_LAT = re.compile(r"[A-Za-z]")

# Patterns that indicate exposed hidden reasoning in a user-facing answer.
_REASONING_PATTERNS = [
    r"<think>", r"</think>", r"chain[- ]of[- ]thought", r"\bmy (internal|hidden) reasoning\b",
    r"\blet me think step by step\b", r"\bstep-by-step reasoning:", r"\binternal monologue\b",
    r"внутренн\w* рассуждени", r"ход\w* моих рассуждений", r"мои скрытые рассуждения",
]
_REASONING_RE = re.compile("|".join(_REASONING_PATTERNS), re.IGNORECASE)

# Claims of professional authority the navigator must never make.
_PRO_PATTERNS = [
    r"\bas your (doctor|physician|lawyer|attorney|therapist|nutritionist|dietitian|financial advis[eo]r)\b",
    r"\bI (diagnose|prescribe)\b", r"\bmy diagnosis\b", r"\byou have (depression|an? injury|a disorder)\b",
    r"\b(take|increase|reduce) (your dose|\d+ ?mg)\b",
    r"как (ваш|твой) (врач|доктор|юрист|адвокат|психотерапевт|диетолог|нутрициолог|финансовый советник)",
    r"\bставлю диагноз\b", r"\bназначаю (вам|тебе)?\s*(препарат|лекарств|дозировк)",
    r"принимай(те)? \d+ ?мг",
]
_PRO_RE = re.compile("|".join(_PRO_PATTERNS), re.IGNORECASE)

# App-activity vocabulary that must not justify levels/achievements.
_ACTIVITY_RE = re.compile(
    r"streak|log ?ins?\b|logged in|app opens?|opened the app|days in a row in the app|"
    r"серия|стрик|заход|вход(ов|а|ы)? в приложение|открыва\w* приложени",
    re.IGNORECASE,
)


def script_profile(text: str):
    """Return (cyrillic_letters, latin_letters)."""
    return len(_CYR.findall(text or "")), len(_LAT.findall(text or ""))


def cyrillic_ratio(text: str) -> float:
    cyr, lat = script_profile(text)
    total = cyr + lat
    return cyr / total if total else 0.0


def matches_language(text: str, language: str) -> bool:
    """Script-based check. Russian text may contain Latin terms (IELTS, Python, URLs)."""
    if not text:
        return False
    ratio = cyrillic_ratio(_strip_urls(text))
    if language == "ru":
        return ratio >= 0.5
    if language == "en":
        return ratio <= 0.08
    return False


def detect_input_language(texts) -> str:
    joined = " ".join(_strip_urls(t) for t in texts if t)
    cyr, lat = script_profile(joined)
    total = cyr + lat
    if not total:
        return "unknown"
    ratio = cyr / total
    if ratio >= 0.85:
        return "ru"
    if ratio <= 0.08:
        return "en"
    return "mixed"


def _strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", " ", text or "")


def exposes_reasoning(text: str) -> bool:
    return bool(_REASONING_RE.search(text or ""))


def claims_professional_authority(text: str) -> bool:
    return bool(_PRO_RE.search(text or ""))


def mentions_app_activity(text: str) -> bool:
    return bool(_ACTIVITY_RE.search(text or ""))


def iter_strings(obj):
    """Yield every string value in a nested JSON-like structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_strings(v)


def contains_term(obj, term: str) -> bool:
    t = term.lower()
    return any(t in s.lower() for s in iter_strings(obj))


# ---- task vagueness -------------------------------------------------------

_VAGUE_TITLE_RE = re.compile(
    r"^(изучи(ть)?|исследуй|исследовать|разберись( в| с)?|подумай( о| над)?|поработай над|"
    r"улучши(ть)?|практикуйся|попрактикуйся|займись|сделай маркетинг|"
    r"research|learn|study|explore|look into|think about|work on|improve|practice|do)\b",
    re.IGNORECASE,
)

_MEASURABLE_HINTS = re.compile(
    r"\d|\b(one|two|three|all|every|each|both)\b|\b(один|одна|одно|два|две|три|все|всех|каждый|каждого|каждой|оба|обе)\b|"
    r"draft|list|table|document|file|link|url|repo|recording|video|audio|note|notes|summary|recorded|noted|logged|"
    r"spreadsheet|photo|screenshot|page|post|version|plan|log|report|slides|deck|form|checklist|"
    r"черновик|спис|таблиц|документ|файл|ссылк|репозитор|запис|конспект|заметк|резюме|отмеч|"
    r"план|отч[её]т|слайд|презентац|пост|страниц|чек-лист|скриншот|анкет|журнал|версия|текст",
    re.IGNORECASE,
)


def title_is_vague(title: str) -> bool:
    """Short 'Learn X' / 'Изучи рынок' style titles with no concrete object or quantity."""
    words = re.findall(r"\w+", title or "")
    return bool(_VAGUE_TITLE_RE.match((title or "").strip())) and len(words) <= 4 and not re.search(r"\d", title)


def result_is_measurable(expected_result: str) -> bool:
    return bool(_MEASURABLE_HINTS.search(expected_result or ""))
