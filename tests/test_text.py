from generation.validators import text as T


def test_language_detection():
    assert T.detect_input_language(["Хочу выучить испанский"]) == "ru"
    assert T.detect_input_language(["I want to learn Spanish"]) == "en"
    assert T.detect_input_language(["Хочу сделать pet-project на React и задеплоить на Vercel"]) == "mixed"
    assert T.matches_language("Сдать IELTS на 7.0 к декабрю", "ru")
    assert not T.matches_language("Pass the exam", "ru")


def test_vague_titles():
    assert T.title_is_vague("Research the market")
    assert T.title_is_vague("Изучи рынок")
    assert not T.title_is_vague("Interview 5 potential customers about budgeting")
    assert not T.result_is_measurable("Better understanding of the market.")
    assert T.result_is_measurable("A list of 10 pre-orders.")
