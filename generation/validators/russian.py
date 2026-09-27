"""Russian voice (POL-D): detectors for grammatically gendered forms.

The assistant has no grammatical gender and never infers the user's gender, so in its own text it
avoids past-tense singular verbs and short adjectives about itself («разбил», «готов») and gendered
agreement when addressing the user («вы один»). Stored memory about the user is written the same way
(«выходные свободны», not «свободен»).

Used by the semantic lint (errors for records with schema_version >= 0.1.1) and by `gj audit`.
The detectors are heuristics tuned on the v0.1.x pool; the tests in tests/test_validators_v011.py
pin their behaviour on known positives and negatives.
"""
import re

_AI_VERB_STEMS = [
    "разбил", "составил", "подготовил", "добавил", "убрал", "изменил", "проверил", "сделал", "понял", "предложил",
    "сохранил", "сократил", "заменил", "посмотрел", "обновил", "сдвинул", "собрал", "перестроил", "пересчитал",
    "отметил", "записал", "засчитал", "создал", "удалил", "разделил", "оставил", "включил", "спланировал",
    "построил", "выбрал", "увидел", "прочитал", "решил", "подобрал", "распределил", "учитывал", "рассчитал",
    "посчитал", "перенастроил", "проанализировал", "подумал", "запланировал", "поставил", "исправил", "уточнил",
]
_AI_VERB_IRREGULAR = ["перенёс", "перенес", "перенесла", "учёл", "учел", "учла", "нашёл", "нашел", "нашла", "смог", "смогла",
                      "пришёл", "пришла", "зачёл", "зачла"]
AI_VERBS = set(_AI_VERB_STEMS) | {s + "а" for s in _AI_VERB_STEMS} | set(_AI_VERB_IRREGULAR)
_SELF_ADJ = r"(рад|рада|готов|готова|уверен|уверена|должен|должна|благодарен|благодарна|согласен|согласна|обязан|обязана)"
_SELF_ADJ_RE = re.compile(r"\bя\s+(?:\w+\s+){0,2}?" + _SELF_ADJ + r"\b", re.IGNORECASE)
_THIRD_PARTY_SUBJ = {"вы", "ты", "он", "она", "пользователь", "ментор", "руководитель", "друг", "тренер", "коллега",
                     "кто", "который", "которая", "начальник", "врач", "клиент", "каждый"}
WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+")
_USER_ADJ = (r"(один|одна|сам|сама|готов|готова|уверен|уверена|должен|должна|рад|рада|свободен|свободна|занят|занята|"
             r"способен|способна|согласен|согласна|знаком|знакома|доволен|довольна|устал|устала)")
USER_ADDRESS_RE = re.compile(r"\b(?:вы|ли)\s+(?:\w+\s+){0,1}?" + _USER_ADJ + r"\b", re.IGNORECASE)
INFORMAL_RE = re.compile(r"\b(ты|тебе|тебя|тобой|твой|твоя|твоё|твои|твоих)\b", re.IGNORECASE)
_MEMORY_ADJ_RE = re.compile(r"\b(свободен|свободна|сам|сама|занят|занята|один|одна|готов|готова|должен|должна)\b",
                            re.IGNORECASE)
_PAST_SG_RE = re.compile(r"\b\w{3,}(?:ал|ил|ял|ел|ул|ыл)(?:а|ся|ась)?\b", re.IGNORECASE)
_THIRD_PARTY_NOUNS = {"врач", "врача", "тренер", "друг", "подруга", "коллега", "руководитель", "начальник",
                      "начальница", "мама", "папа", "жена", "муж", "партнёр", "партнер", "брат", "сестра", "сын",
                      "дочь", "ментор", "преподаватель", "учитель", "он", "она", "кто", "который", "которая"}
AGENT_NOUN_RE = re.compile(
    r"\b(\w+(?:ый|ий|ой))\s+(\w+(?:чик|щик|тель|ник|ист|ер|ор|ец|ин|ок|ар))\b|"
    r"\b(хозяин|повар|нарезчик|моделлер|новичок|любитель|знаток|путешественник|кулинар|бегун|пловец|ученик|студент|"
    r"водитель|писатель|читатель|исследователь|сладкоежка)\b", re.IGNORECASE)


def self_reference(s):
    """Yield gendered forms by which the assistant refers to itself («разбил», «я уверен»)."""
    words = WORD_RE.findall(s or "")
    low = [w.lower() for w in words]
    for i, w in enumerate(low):
        if w in AI_VERBS:
            prev = set(low[max(0, i - 3):i])
            if prev & _THIRD_PARTY_SUBJ:
                continue
            # a capitalised proper noun right before the verb is a third-party subject ("Ментор предложил")
            if i > 0 and words[i - 1][:1].isupper() and i - 1 > 0:
                continue
            yield w
    for m in _SELF_ADJ_RE.finditer(s or ""):
        yield m.group(0)


def user_address(s):
    """Yield regex matches that address the user with gendered agreement («вы один», «готов ли»)."""
    yield from USER_ADDRESS_RE.finditer(s or "")


# Nouns that end like past-tense verbs («канала», «материала», «отдела»).
_PAST_LOOKALIKE_NOUNS = re.compile(
    r"^(канал|материал|сериал|журнал|финал|капитал|персонал|идеал|интервал|сигнал|оригинал|терминал|генерал|"
    r"арсенал|подвал|вокзал|зал|бал|скандал|пьедестал|овал|штурвал|минимал|отдел|предел|раздел|пробел|стул|"
    r"караул|тыл|пыл|крокодил|фестивал)", re.IGNORECASE)
# Words after which a clause-internal past-tense form is still about the user («раньше работал»).
_PAST_ADVERBS = {"не", "уже", "раньше", "давно", "недавно", "ещё", "еще", "только", "почти", "никогда", "всегда",
                 "часто", "редко", "тоже", "также", "сам", "сама", "когда-то", "однажды", "впервые"}
_CLAUSE_BREAK = re.compile(r"[.,;:!?()—–\-]\s*$|^\s*$|\b(и|но|а|или|если|когда|что|потому)\s+$", re.IGNORECASE)


def memory_gendered(s):
    """A gendered form describing the user in stored memory (memory is written without a subject,
    so a clause-initial singular past-tense verb or a short adjective refers to the user)."""
    m = _MEMORY_ADJ_RE.search(s or "")
    if m:
        return m
    for m in _PAST_SG_RE.finditer(s or ""):
        if _PAST_LOOKALIKE_NOUNS.match(m.group(0)):
            continue
        before_words = [w.lower() for w in WORD_RE.findall(s[:m.start()])]
        if set(before_words[-3:]) & _THIRD_PARTY_NOUNS:
            continue
        clause_start = bool(_CLAUSE_BREAK.search(s[:m.start()]))
        after_adverb = bool(before_words) and before_words[-1] in _PAST_ADVERBS
        if clause_start or after_adverb:
            return m
    return None
