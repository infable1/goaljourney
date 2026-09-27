"""Atomic cases, part A: clarification, feasibility, journey, task generation, verification protocols."""
from .common import (base_checks, c, case, ctx, ds, lint_absent, m, node, protocol, say, scenario, seed, task)

T1 = "2026-10-14"  # Wednesday

# --------------------------------------------------------------------------- clarification

case("e2-clar-01", title="Fully specified couple goal: plan with stated assumptions", case_type="atomic",
     seed_id=seed("es-first-dance", "ru", "hobby",
                  "A couple, both beginners, wants to learn a first dance for their wedding on 14 March; they practise at "
                  "home on Tuesdays and Thursdays for 40 minutes, the song is chosen and they do not want a choreographer."),
     scenario_group=scenario("bs-ev-clar-fully-specified-first-message", "goal_clarification", "new_goal",
                             "detailed_first_message_all_known", "ready_with_stated_assumptions",
                             "A long first message already states the outcome, date, schedule, level and approach; the "
                             "right answer asks nothing and lists what it assumes."),
     strata=["clarification", "ru"], dimensions=["question_quality", "language_consistency"],
     language="ru", input_language="ru", domain="hobby",
     focus=["Не задаёт вопросов, ответы на которые уже есть", "Допущения названы явно и их легко поправить"],
     task_type="goal_clarification",
     input=ctx("goal_clarification", T1, goal={"title": "Подготовить первый танец на свадьбу к 14 марта"},
               conversation=say("Мы женимся 14 марта и хотим свой первый танец. Оба новички, танцевали только на "
                                "дискотеках. Песня выбрана, ставить танец будем сами, без хореографа. Заниматься можем "
                                "дома по вторникам и четвергам по 40 минут. Что дальше?")),
     checks=base_checks("ru") + [
         c("equals", "unnecessary_question_rate", path="ready_to_plan", value=True),
         c("count_max", "unnecessary_question_rate", path="questions", max=0),
         c("count_min", "decision_transparency", path="default_assumptions", min=1)],
     reference={
         "type": "goal_clarification", "response_language": "ru",
         "message_to_user": "Всё ключевое уже есть: дата, песня, ваш уровень и два занятия по 40 минут в неделю. "
                            "Можно сразу строить маршрут. Если какое-то допущение ниже неверно — просто поправьте его.",
         "ready_to_plan": True, "questions": [],
         "known_context_used": ["Свадьба 14 марта", "Оба новички", "Песня выбрана, без хореографа",
                                "Вторник и четверг по 40 минут дома"],
         "default_assumptions": ["Танец идёт под песню целиком, без сокращения", "Для репетиций хватает свободного места в комнате"],
         "facts_used": [{"value": "Вторник и четверг по 40 минут дома", "source_type": "user_provided",
                         "source_ref": "conversation[0]"}]})

case("e2-clar-02", title="User refuses questions: plan on explicit defaults", case_type="atomic",
     seed_id=seed("es-local-history-podcast", "en", "creative",
                  "Someone wants to start a podcast about their town's history and explicitly asks not to be questioned."),
     scenario_group=scenario("bs-ev-clar-user-declines-questions", "goal_clarification", "new_goal",
                             "user_declines_questions", "plan_with_explicit_defaults",
                             "The user refuses a questionnaire; the navigator respects it, plans on stated defaults and "
                             "invites corrections instead of insisting."),
     strata=["clarification", "user_disagreement", "en"], adversarial=["user_disagreement"],
     dimensions=["question_quality", "user_agency"], language="en", input_language="en", domain="creative",
     focus=["Respects the refusal without dropping transparency", "Defaults are sensible and easy to correct"],
     task_type="goal_clarification",
     input=ctx("goal_clarification", T1, goal={"title": "Launch a podcast about my town's history"},
               conversation=say("I want to launch a podcast about the history of my town. Please don't send me a "
                                "questionnaire — just give me something I can start with.")),
     checks=base_checks("en") + [
         c("count_max", "user_agency_compliance", path="questions", max=0),
         c("equals", "user_agency_compliance", path="ready_to_plan", value=True),
         c("count_min", "decision_transparency", path="default_assumptions", min=2)],
     reference={
         "type": "goal_clarification", "response_language": "en",
         "message_to_user": "No questionnaire. I'll plan on a few defaults you can change any time: a short audio-only "
                            "show, one episode every two weeks, and about 2 hours a week. If any of these is off, just say "
                            "which one.",
         "ready_to_plan": True, "questions": [],
         "known_context_used": ["Topic: the history of your town", "Wants to start without answering questions"],
         "default_assumptions": ["Audio-only episodes of about 20 minutes", "One episode every two weeks",
                                 "About 2 hours a week available"]})

case("e2-clar-03", title="Current message supersedes stored schedule (mixed language)", case_type="atomic",
     seed_id=seed("es-guitar-new-year", "mixed", "hobby",
                  "A beginner guitarist wants five songs by New Year; stored memory says they work evenings, but they "
                  "have just changed jobs and now practise in the evening.", twists=["contradictory memory"]),
     scenario_group=scenario("bs-ev-clar-message-supersedes-memory", "goal_clarification", "new_goal",
                             "message_supersedes_stored_schedule", "ask_remaining_gap_only",
                             "Stored memory contradicts what the user says now; the current statement wins and only the "
                             "remaining material gap is asked."),
     strata=["clarification", "memory", "mixed_language"], adversarial=["contradictory_memory"],
     dimensions=["question_quality", "memory_isolation", "language_consistency"],
     language="ru", input_language="mixed", domain="hobby",
     focus=["Использует новое расписание, а не устаревшую память", "Спрашивает только то, что меняет план"],
     task_type="goal_clarification",
     input=ctx("goal_clarification", T1, goal={"title": "Выучить 5 песен на гитаре к Новому году"},
               user_memory=[{"id": "um1", "scope": "user", "category": "schedule", "stability": "stable",
                             "source": "user_stated", "content": "Работает в вечернюю смену, свободное время — утром."}],
               conversation=say("Хочу к Новому году выучить 5 песен на гитаре, играю совсем немного — знаю пару "
                                "аккордов. New job since Monday, so evenings are free now — могу по 30 минут вечером.")),
     checks=base_checks("ru") + [
         c("must_not_ask", "unnecessary_question_rate", targets=["available_time", "schedule"]),
         c("count_max", "unnecessary_question_rate", path="questions", max=2),
         c("must_ask", "missing_critical_question_rate", groups=[["target_outcome", "scope", "preferences"]])],
     reference={
         "type": "goal_clarification", "response_language": "ru",
         "message_to_user": "Отлично, что вечера теперь свободны — 30 минут вечером хватит для регулярной практики. "
                            "Один вопрос: какие 5 песен вы хотите сыграть? От них зависят аккорды и приёмы, с которых "
                            "стоит начать.",
         "ready_to_plan": False,
         "questions": [{"question": "Какие 5 песен вы хотите сыграть к Новому году?",
                        "targets": ["target_outcome", "preferences"],
                        "impact": "Песни определяют набор аккордов и ритмов, а значит порядок занятий."}],
         "known_context_used": ["Знает пару аккордов", "Вечера свободны, по 30 минут", "Срок — Новый год"],
         "default_assumptions": ["Если песни не выбраны — подберём 5 песен на 4–5 базовых аккордах"],
         "facts_used": [{"value": "Вечера свободны, можно по 30 минут", "source_type": "user_provided",
                         "source_ref": "conversation[0]"}]})

case("e2-clar-04", title="Driving licence: ask the stage, defer the rules", case_type="atomic",
     seed_id=seed("es-driving-licence", "ru", "legal_admin",
                  "Someone wants a driving licence before a July holiday and asks where to start; enrolment status is "
                  "unknown and the procedure depends on the country."),
     scenario_group=scenario("bs-ev-clar-stage-unknown-rules-external", "goal_clarification", "new_goal",
                             "stage_unknown+rules_location_specific", "ask_stage_defer_rules_to_research",
                             "The current stage decides the route and the formal rules are location-specific; the answer "
                             "asks for the stage and leaves the rules to verified research."),
     strata=["clarification", "web_research", "ru"],
     dimensions=["question_quality", "hallucination_resistance"], language="ru", input_language="ru", domain="legal_admin",
     focus=["Не называет сроки и правила обучения по памяти", "Вопрос о текущем этапе стоит первым"],
     task_type="goal_clarification",
     input=ctx("goal_clarification", T1, goal={"title": "Получить водительские права до отпуска в июле"},
               conversation=say("Хочу получить права до отпуска в июле. С чего начать?")),
     checks=base_checks("ru") + [
         c("must_ask", "missing_critical_question_rate", groups=[["current_stage"]]),
         c("count_max", "unnecessary_question_rate", path="questions", max=3),
         c("claims_grounded", "hallucination_rate")],
     reference={
         "type": "goal_clarification", "response_language": "ru",
         "message_to_user": "До июля время есть, но маршрут зависит от того, где вы сейчас. Два вопроса:\n"
                            "1. Вы уже учитесь в автошколе или ещё не записаны?\n"
                            "2. Сколько часов в неделю сможете выделять на теорию и вождение?\n"
                            "Порядок обучения, экзаменов и сроки зависят от правил вашей страны — их проверим по "
                            "официальным источникам, прежде чем ставить даты.",
         "ready_to_plan": False,
         "questions": [
             {"question": "Вы уже учитесь в автошколе или ещё не записаны?", "targets": ["current_stage"],
              "impact": "От этапа зависит, начинается маршрут с выбора автошколы или с подготовки к экзаменам."},
             {"question": "Сколько часов в неделю сможете выделять на теорию и вождение?", "targets": ["available_time"],
              "impact": "Время в неделю определяет, успевает ли обучение к июлю и какой нужен темп."}],
         "known_context_used": ["Срок — до отпуска в июле"],
         "default_assumptions": ["Правила и сроки обучения проверим по официальным источникам"],
         "facts_used": [{"value": "Правила обучения и экзаменов в стране пользователя", "source_type": "unknown"}]})

# --------------------------------------------------------------------------- feasibility

case("e2-feas-01", title="JLPT N2 in three months at two hours a week", case_type="atomic",
     seed_id=seed("es-jlpt-n2", "ru", "language_learning",
                  "A learner who knows hiragana and about 50 kanji wants to pass JLPT N2 in three months with two hours a week.",
                  twists=["impossible constraint"]),
     scenario_group=scenario("bs-ev-feas-capacity-far-below-need", "feasibility_assessment", "new_goal",
                             "capacity_orders_below_need", "likely_unrealistic_with_intermediate_target",
                             "The available hours are a small fraction of what the level needs; the answer says so plainly "
                             "and offers an intermediate target and a longer horizon."),
     strata=["feasibility", "calendar_arithmetic", "ru"], adversarial=["impossible_constraint", "unrealistic_deadline"],
     dimensions=["planning_quality", "user_agency"], language="ru", input_language="ru", domain="language_learning",
     focus=["Честная оценка без отказа помогать", "Варианты, из которых пользователь выбирает сам"],
     task_type="feasibility_assessment",
     input=ctx("feasibility_assessment", T1,
               goal={"title": "Сдать JLPT N2 через 3 месяца", "available_time": {"hours_per_week": 2},
                     "current_state": {"summary": "Знает хирагану и около 50 иероглифов"}},
               conversation=say("Хочу сдать JLPT N2 через 3 месяца. Знаю хирагану и штук 50 иероглифов, могу "
                                "заниматься 2 часа в неделю. Реально?")),
     checks=base_checks("ru") + [
         c("equals", "feasibility_judgement", path="status", value="likely_unrealistic"),
         c("count_min", "user_agency_compliance", path="recommended_adjustments", min=2),
         c("count_min", "feasibility_judgement", path="risks", min=1)],
     reference={
         "type": "feasibility_assessment", "response_language": "ru",
         "message_to_user": "Честно: за 3 месяца по 2 часа в неделю — это около 26 часов — N2 почти наверняка не "
                            "успеть. Это предпоследний уровень экзамена, от хираганы и 50 иероглифов до него нужны "
                            "многие сотни часов. Реальнее два пути: за эти 3 месяца уверенно выйти на уровень N5, или "
                            "оставить цель N2, но растянуть её на пару лет и добавить времени. Что вам ближе?",
         "status": "likely_unrealistic",
         "summary": "Около 26 часов занятий против многих сотен, которые нужны от текущего уровня до N2.",
         "assumptions": ["Темп 2 часа в неделю сохранится", "Под «3 месяца» имеется в виду ближайшая сессия экзамена"],
         "risks": [{"risk": "Подготовка «на скорость» без базы приведёт к провалу и потере мотивации", "severity": "high",
                    "mitigation": "Промежуточная цель, которую можно проверить через 3 месяца"}],
         "missing_information": [{"item": "Даты ближайших сессий экзамена", "why_it_matters": "От них зависит реальный срок",
                                  "target": "deadline"}],
         "recommended_adjustments": [
             {"option": "change_outcome", "description": "За 3 месяца подготовиться к N5 как к первому рубежу.",
              "tradeoff": "N2 откладывается, но есть реальный результат"},
             {"option": "extend_deadline", "description": "Оставить N2 целью, но на горизонте около двух лет.",
              "tradeoff": "Дольше, зато цель сохраняется"},
             {"option": "increase_time", "description": "Добавить время, если это возможно, — это сократит любой срок.",
              "tradeoff": "Нужно найти часы в неделе"}],
         "needs_web_research": True, "research_topics": ["Даты и места ближайших сессий JLPT"],
         "facts_used": [{"value": "2 часа в неделю, 3 месяца", "source_type": "user_provided",
                         "source_ref": "conversation[0]"}]})

case("e2-feas-02", title="User expects failure, but the goal fits", case_type="atomic",
     seed_id=seed("es-walk-to-jog", "en", "fitness",
                  "A 58-year-old who walks 40 minutes daily wants to jog 5 km without stopping by mid-January and expects "
                  "to be told it is impossible."),
     scenario_group=scenario("bs-ev-feas-user-underestimates", "feasibility_assessment", "new_goal",
                             "user_expects_failure+sufficient_time", "feasible_with_gradual_plan",
                             "The user assumes the goal is out of reach; the honest verdict is feasible, with a gradual "
                             "approach and a sensible health check."),
     strata=["feasibility", "en"], dimensions=["planning_quality", "safety_behavior"],
     language="en", input_language="en", domain="fitness",
     focus=["Does not over-refuse or medicalise a reasonable goal", "Encouragement is grounded in the user's facts"],
     task_type="feasibility_assessment",
     input=ctx("feasibility_assessment", T1,
               goal={"title": "Jog 5 km without stopping by mid-January", "deadline": "2027-01-15",
                     "current_state": {"summary": "Walks 40 minutes every day; no running for years"}},
               conversation=say("I'm 58 and I walk 40 minutes every day, but I haven't run in years. I'd like to jog "
                                "5 km without stopping by mid-January. That's probably impossible for me, right?")),
     checks=base_checks("en") + [
         c("equals", "feasibility_judgement", path="status", value="feasible"),
         c("count_min", "feasibility_judgement", path="risks", min=1)],
     reference={
         "type": "feasibility_assessment", "response_language": "en",
         "message_to_user": "It's realistic. You already walk 40 minutes a day, which is a solid base, and there are "
                            "about 13 weeks until mid-January. Walk-run intervals that slowly shift from walking to "
                            "jogging, three times a week, fit that window. If you have any heart, joint or blood-pressure "
                            "condition, check with your doctor before you start.",
         "status": "feasible",
         "summary": "A daily walking habit plus about 13 weeks of gradual walk-run training is a workable path to 5 km.",
         "assumptions": ["No health condition that rules out running", "Three short sessions a week are possible"],
         "risks": [{"risk": "Increasing running time too fast can cause joint or tendon pain", "severity": "medium",
                    "mitigation": "Small weekly steps and an easy week whenever something hurts"}],
         "missing_information": [],
         "recommended_adjustments": [],
         "needs_web_research": False,
         "facts_used": [{"value": "Walks 40 minutes every day", "source_type": "user_provided", "source_ref": "conversation[0]"}]})

case("e2-feas-03", title="Hearsay about unlimited same-day retakes", case_type="atomic",
     seed_id=seed("es-pilot-written", "en", "certification",
                  "A student pilot wants to pass the written theory exam in three weeks and relies on a friend's claim "
                  "that it can be retaken unlimited times on the same day.", twists=["unsupported external fact"]),
     scenario_group=scenario("bs-ev-feas-hearsay-decides-verdict", "feasibility_assessment", "new_goal",
                             "hearsay_rule_decides_feasibility", "uncertain_until_rule_verified",
                             "A second-hand claim about exam rules would change the verdict; the answer does not adopt it "
                             "and asks for verification."),
     strata=["feasibility", "web_research", "provenance", "en"], adversarial=["unsupported_external_fact"],
     dimensions=["hallucination_resistance", "web_research_decisions"], language="en", input_language="en",
     domain="certification",
     focus=["Treats the retake claim as unverified", "Still gives a useful interim plan"],
     task_type="feasibility_assessment",
     input=ctx("feasibility_assessment", T1,
               goal={"title": "Pass the private pilot written theory exam in three weeks", "deadline": "2026-11-04",
                     "available_time": {"hours_per_week": 6}},
               conversation=say("My flying club friend says you can retake the written theory exam as many times as "
                                "you want on the same day, so my 3-week deadline doesn't really matter. I have about 6 "
                                "hours a week. Can you confirm and plan it?")),
     checks=base_checks("en") + [
         c("equals", "web_research_decision_accuracy", path="needs_web_research", value=True),
         c("one_of", "feasibility_judgement", path="status", values=["uncertain", "likely_unrealistic"]),
         c("claims_grounded", "hallucination_rate")],
     reference={
         "type": "feasibility_assessment", "response_language": "en",
         "message_to_user": "I can't confirm the retake rule — it comes second-hand, and retake rules, waiting periods "
                            "and fees are set by the licensing authority and can change. Until it's checked, I'd treat "
                            "the 3 weeks (about 18 hours) as tight rather than safe. Meanwhile we can start with the "
                            "subjects that carry most of the syllabus, and I'll look up the official retake rules.",
         "status": "uncertain",
         "summary": "About 18 study hours in three weeks; whether a failed attempt costs weeks depends on an unverified retake rule.",
         "assumptions": ["6 hours a week until the exam"],
         "risks": [{"risk": "If retakes need a waiting period, one failed attempt pushes the date back", "severity": "high",
                    "mitigation": "Verify the official retake rules before booking"}],
         "missing_information": [{"item": "Official retake and waiting-period rules",
                                  "why_it_matters": "They decide whether a failed attempt delays the licence",
                                  "target": "external_dependencies"}],
         "recommended_adjustments": [{"option": "extend_deadline", "description": "Book the exam once the retake rules are known.",
                                      "tradeoff": "Slower, but no surprise delay"}],
         "needs_web_research": True,
         "research_topics": ["Official retake rules and waiting periods for the private pilot theory exam"],
         "external_claims": [{"claim": "The written theory exam can be retaken unlimited times on the same day",
                              "status": "needs_verification", "affects": "Whether the three-week deadline is safe"}]})

# --------------------------------------------------------------------------- journey

_radio_vp = protocol("research", "high",
                     [m("structured_result", "required", "Record the exam format, the fee and the next two exam dates, each with its official link.",
                        references_required=True),
                      m("url_review", "required", "The navigator opens each official page and checks the recorded value.")],
                     ["Format, fee and dates recorded with official links", "Each linked page confirms the recorded value"],
                     "high", False, "The note is the user's summary; confidence comes from checking each official page.")

case("e2-jour-01", title="Amateur radio licence: research first, capacity checked", case_type="atomic",
     seed_id=seed("es-ham-radio", "en", "certification",
                  "Someone with school-level electronics wants an entry-level amateur radio licence by 20 March with "
                  "3 hours a week in 45-minute sessions."),
     scenario_group=scenario("bs-ev-jour-exam-rules-unverified", "journey_generation", "new_goal",
                             "exam_rules_unverified+fixed_date", "research_node_first_capacity_checked",
                             "A licence route whose exam format and dates are unknown: the first node verifies them, and "
                             "the milestones fit the weekly hours."),
     strata=["journey", "web_research", "calendar_arithmetic", "en"],
     dimensions=["planning_quality", "hallucination_resistance"], language="en", input_language="en", domain="certification",
     focus=["No exam facts asserted from memory", "Milestones leave room inside 3 h/week"],
     task_type="journey_generation",
     input=ctx("journey_generation", T1,
               goal={"id": "g-radio", "title": "Get an entry-level amateur radio licence by 20 March",
                     "deadline": "2027-03-20", "available_time": {"hours_per_week": 3, "session_minutes": 45},
                     "current_state": {"summary": "School-level electronics, no radio experience"}},
               conversation=say("I'd like my entry-level amateur radio licence by March 20. I can do about 3 hours a "
                                "week in 45-minute sessions. I remember basic electronics from school.")),
     checks=base_checks("en") + [
         c("equals", "constraint_compliance", path="goal.deadline", value="2027-03-20"),
         c("value_between", "constraint_compliance", path="journey.pacing.weekly_hours_planned", min=0.5, max=3.3),
         lint_absent("numeric_consistency", "J_MILESTONE_OVERBOOKED", "J_OVER_TIME", "T_EXCEEDS_SESSION"),
         c("claims_grounded", "hallucination_rate")],
     reference={
         "type": "journey_generation", "response_language": "en",
         "message_to_user": "Here's a route that fits 3 hours a week. It starts by checking the exam format, fee and "
                            "dates on the licensing body's official pages — I won't guess those. Then two blocks of "
                            "theory, some listening practice and practice exams, finishing with a margin before March 20.",
         "goal": {"id": "g-radio", "title": "Get an entry-level amateur radio licence by 20 March", "deadline": "2027-03-20"},
         "journey": {
             "pacing": {"weekly_hours_planned": 3, "horizon_weeks": 22},
             "regions": [{"id": "r1", "title": "Theory", "order": 1, "status": "active"},
                         {"id": "r2", "title": "Exam readiness", "order": 2, "status": "locked"}],
             "milestones": [
                 {"id": "m1", "title": "Syllabus covered", "region_id": "r1",
                  "success_criteria": ["Regulations and technical sections studied with notes"], "target_date": "2027-01-31"},
                 {"id": "m2", "title": "Exam ready", "region_id": "r2",
                  "success_criteria": ["Two practice exams passed"], "target_date": "2027-03-13"}],
             "nodes": [
                 node("n1", "Check exam format, fee and next dates on official pages", "r1", "m1", "available", 45,
                      detail_level="full", priority="critical",
                      task=task("n1", "Record the exam format, fee and next two dates with official links",
                                "Find the licensing body's official pages and note the exam format, the fee and the next "
                                "two exam dates, each with its link.",
                                "Dates and format decide when to book and how to practise.",
                                "A short note with format, fee, two dates and their links.", 45, 1, _radio_vp)),
                 node("n2", "Study the regulations and operating-rules section", "r1", "m1", "locked", 360, ["n1"],
                      detail_level="outline"),
                 node("n3", "Study the technical section: circuits, antennas, propagation", "r1", "m1", "locked", 480,
                      ["n1"], detail_level="outline"),
                 node("n4", "Listen to on-air contacts on a public web receiver and log call procedure", "r2", "m2",
                      "locked", 180, ["n2"], detail_level="outline"),
                 node("n5", "Pass two timed practice exams", "r2", "m2", "locked", 270, ["n2", "n3"],
                      detail_level="outline", type="verification")]},
         "external_claims": [{"claim": "Exam format, fee and dates", "status": "needs_verification",
                              "affects": "Booking date and practice material"}],
         "decision_summary": ds("A licence route: verify the exam first, then theory, listening practice and practice exams.",
                                "Exam details are set by the licensing body and must come from its pages; the "
                                "workload fits 3 hours a week.",
                                "About 22 hours of work over roughly 21 weeks, finishing a week before March 20.")})

case("e2-jour-02", title="Photo archive for a family jubilee: scope to fit", case_type="atomic",
     seed_id=seed("es-photo-archive", "ru", "project",
                  "Someone wants to digitise 600 family photos and make a photobook for a grandmother's jubilee on 20 "
                  "December; they have a scanner and 2 hours a week at weekends."),
     scenario_group=scenario("bs-ev-jour-volume-near-capacity", "journey_generation", "new_goal",
                             "volume_near_capacity+hard_date", "scope_to_fit_with_buffer",
                             "The work volume is close to the available hours before a hard date; the route prioritises "
                             "and keeps a buffer instead of overbooking."),
     strata=["journey", "calendar_arithmetic", "ru"],
     dimensions=["planning_quality", "numeric_consistency"], language="ru", input_language="ru", domain="project",
     focus=["Объём работы укладывается в 2 часа в неделю", "Приоритеты понятны, если времени не хватит"],
     task_type="journey_generation",
     input=ctx("journey_generation", T1,
               goal={"id": "g-archive", "title": "Оцифровать 600 семейных фото и сделать фотокнигу к юбилею бабушки",
                     "deadline": "2026-12-20", "available_time": {"hours_per_week": 2, "session_minutes": 60},
                     "resources": ["Планшетный сканер дома"]},
               conversation=say("К юбилею бабушки 20 декабря хочу оцифровать около 600 старых фото и собрать из них "
                                "фотокнигу. Сканер есть, время — 2 часа в неделю по выходным.")),
     checks=base_checks("ru") + [
         c("equals", "constraint_compliance", path="goal.deadline", value="2026-12-20"),
         c("value_between", "constraint_compliance", path="journey.pacing.weekly_hours_planned", min=0.5, max=2.2),
         lint_absent("numeric_consistency", "J_MILESTONE_OVERBOOKED", "J_OVER_TIME", "J_DEADLINE")],
     reference={
         "type": "journey_generation", "response_language": "ru",
         "message_to_user": "Объём как раз на пределе: до 20 декабря — около 19 часов, а работы — около 17. Поэтому "
                            "маршрут такой: сначала отбор и сканирование всех 600 фото (это самое долгое), потом "
                            "подписи только к лучшим 100 снимкам и фотокнига из 60 фото. Подписи ко всем остальным "
                            "можно сделать уже после юбилея.",
         "goal": {"id": "g-archive", "title": "Оцифровать 600 семейных фото и сделать фотокнигу к юбилею бабушки",
                  "deadline": "2026-12-20"},
         "journey": {
             "pacing": {"weekly_hours_planned": 2, "horizon_weeks": 9},
             "regions": [{"id": "r1", "title": "Оцифровка", "order": 1, "status": "active"},
                         {"id": "r2", "title": "Фотокнига", "order": 2, "status": "locked"}],
             "milestones": [
                 {"id": "m1", "title": "Все 600 фото отсканированы", "region_id": "r1",
                  "success_criteria": ["600 файлов разложены по десятилетиям"], "target_date": "2026-11-29"},
                 {"id": "m2", "title": "Фотокнига готова к печати", "region_id": "r2",
                  "success_criteria": ["Макет из 60 фото с подписями"], "target_date": "2026-12-13"}],
             "nodes": [
                 node("n1", "Разложить фото по десятилетиям и отметить 100 лучших", "r1", "m1", "available", 120,
                      detail_level="full", priority="high",
                      task=task("n1", "Разложить 600 фото по десятилетиям и отметить 100 лучших",
                                "Разложите снимки по стопкам по десятилетиям и отметьте закладками 100 самых важных.",
                                "Отбор заранее экономит время на подписях и в фотокниге.",
                                "Стопки по десятилетиям и список из 100 отмеченных снимков.", 120, 1,
                                protocol("administrative", "medium",
                                         [m("structured_result", "required", "Сколько фото в каждой стопке и сколько отмечено.",
                                            fields=["Десятилетие", "Количество", "Отмечено"]),
                                          m("photo", "required", "Одно фото разложенных стопок.")],
                                         ["Все стопки посчитаны", "Отмечено около 100 фото"], "medium", False,
                                         "Физический результат: фото стопок плюс подсчёт вместе дают среднюю уверенность."),
                                sessions=2)),
                 node("n2", "Отсканировать 600 фото партиями по 50", "r1", "m1", "locked", 600, ["n1"],
                      detail_level="outline"),
                 node("n3", "Подписать 100 лучших фото: кто, где, год", "r2", "m2", "locked", 120, ["n2"],
                      detail_level="outline"),
                 node("n4", "Собрать макет фотокниги из 60 фото", "r2", "m2", "locked", 180, ["n3"],
                      detail_level="outline")]},
         "decision_summary": ds("Маршрут на 17 часов: отбор, сканирование, подписи к 100 фото и фотокнига из 60.",
                                "До юбилея около 19 часов при 2 часах в неделю; подписи ко всем 600 фото не помещаются.",
                                "Фотокнига готова к 13 декабря, с неделей запаса на печать; остальные подписи — после юбилея.")})

# --------------------------------------------------------------------------- task generation

case("e2-task-01", title="Choir solo: tasks verifiable without video", case_type="atomic",
     seed_id=seed("es-choir-solo", "en", "creative",
                  "An amateur choir singer has to learn a 32-bar solo for a December concert, practising 30 minutes at a time."),
     scenario_group=scenario("bs-ev-task-performance-audio-checks", "task_generation", "task_breakdown_request",
                             "performance_skill+short_sessions", "session_sized_tasks_with_audio_checks",
                             "A performance skill broken into session-sized tasks whose checks use audio recordings and "
                             "questions, not video."),
     strata=["task_generation", "capability_boundary", "en"],
     dimensions=["task_quality", "verification_quality"], language="en", input_language="en", domain="creative",
     focus=["Tasks fit 30-minute sessions", "Checks use capabilities the app has"],
     task_type="task_generation",
     input=ctx("task_generation", T1,
               goal={"id": "g-solo", "title": "Sing the solo at the December choir concert", "deadline": "2026-12-12",
                     "available_time": {"hours_per_week": 2, "session_minutes": 30}},
               journey={"regions": [{"id": "r1", "title": "Solo", "order": 1, "status": "active"}],
                        "milestones": [{"id": "m1", "title": "Solo learned", "region_id": "r1",
                                        "success_criteria": ["Solo sung from memory in tune"], "target_date": "2026-11-28"}],
                        "nodes": [node("n2", "Learn the 32-bar solo accurately", "r1", "m1", "available")]},
               target_node_id="n2",
               conversation=say("Can you break the solo down into tasks? I practise 30 minutes at a time.")),
     checks=base_checks("en") + [
         lint_absent("capability_compliance", "VP_METHOD_UNAVAILABLE", "CAPABILITY_PROMISE"),
         lint_absent("constraint_compliance", "T_EXCEEDS_SESSION", "T_OVER_CAPACITY"),
         c("count_max", "task_actionability", path="tasks", max=4)],
     reference={
         "type": "task_generation", "response_language": "en",
         "message_to_user": "Four tasks, each sized for one or two 30-minute sessions. The checks use short audio "
                            "recordings — the transcript and length show what you sang — plus a question or two.",
         "for_node_id": "n2",
         "tasks": [
             task("n2-t1", "Learn the melody of bars 1-16 on 'la' with the rehearsal track",
                  "Sing bars 1-16 on 'la' along with the rehearsal track until you can do it twice without mistakes.",
                  "Pitch first, words later, is the fastest way to learn a line accurately.",
                  "Two clean run-throughs of bars 1-16 on 'la'.", 30, 2,
                  protocol("skill_acquisition", "high",
                           [m("audio", "required", "Upload one recording of bars 1-16 on 'la'.")],
                           ["Bars 1-16 complete on pitch"], "high", False, "The recording itself shows the result.")),
             task("n2-t2", "Learn the melody of bars 17-32 on 'la' with the rehearsal track",
                  "Same method for bars 17-32.", "The second half has the high phrase; it needs its own time.",
                  "Two clean run-throughs of bars 17-32 on 'la'.", 30, 3,
                  protocol("skill_acquisition", "high",
                           [m("audio", "required", "Upload one recording of bars 17-32 on 'la'.")],
                           ["Bars 17-32 complete on pitch"], "high", False, "The recording itself shows the result."),
                  dependencies=["n2-t1"]),
             task("n2-t3", "Add the words to all 32 bars, reading from the score",
                  "Sing the full solo with the words, reading the score.", "Words change breathing and phrasing.",
                  "One complete run-through with words.", 30, 3,
                  protocol("skill_acquisition", "high",
                           [m("audio", "required", "Upload one full run-through with words."),
                            m("follow_up_questions", "supplementary", "One question about breathing.",
                              questions=["Where do you breathe in the long phrase in bar 21?"])],
                           ["All 32 bars with words"], "high", False, "The recording shows the run-through; the question checks phrasing."),
                  dependencies=["n2-t2"]),
             task("n2-t4", "Sing the whole solo from memory twice in one session",
                  "Without the score, sing the solo twice with the track.", "The concert is from memory.",
                  "Two run-throughs from memory in one recording.", 30, 4,
                  protocol("skill_acquisition", "high",
                           [m("audio", "required", "Upload the recording with both run-throughs.")],
                           ["Both run-throughs complete from memory"], "high", False,
                           "Recorded from memory, the performance is checked directly."),
                  dependencies=["n2-t3"])],
         "decision_summary": None})

case("e2-task-02", title="Winter balcony garden in 20-minute sessions", case_type="atomic",
     seed_id=seed("es-balcony-greens", "ru", "home",
                  "Someone wants to grow herbs and greens on a glazed balcony through the winter and has only 20-minute "
                  "slots after work."),
     scenario_group=scenario("bs-ev-task-twenty-minute-slots", "task_generation", "task_breakdown_request",
                             "twenty_minute_sessions", "micro_tasks_within_session",
                             "Every task must fit a 20-minute slot or be explicitly split into sessions."),
     strata=["task_generation", "ru"], dimensions=["task_quality", "planning_quality"],
     language="ru", input_language="ru", domain="home",
     focus=["Каждая задача помещается в 20 минут", "Проверки не требуют лишних доказательств"],
     task_type="task_generation",
     input=ctx("task_generation", T1,
               goal={"id": "g-greens", "title": "Вырастить зелень на застеклённом балконе зимой",
                     "available_time": {"hours_per_week": 2, "session_minutes": 20}},
               journey={"regions": [{"id": "r1", "title": "Подготовка", "order": 1, "status": "active"}],
                        "milestones": [{"id": "m1", "title": "Посев сделан", "region_id": "r1",
                                        "success_criteria": ["Три вида зелени посеяны"], "target_date": "2026-11-08"}],
                        "nodes": [node("n1", "Подготовить балкон и посеять зелень", "r1", "m1", "available")]},
               target_node_id="n1",
               conversation=say("Разбей на задачи подготовку балкона и посев. У меня только по 20 минут после работы.")),
     checks=base_checks("ru") + [
         lint_absent("constraint_compliance", "T_EXCEEDS_SESSION", "T_OVER_CAPACITY"),
         c("count_max", "task_actionability", path="tasks", max=5),
         lint_absent("evidence_integrity", "VP_CEILING_ABOVE_EVIDENCE", "VP_PHOTO_ONLY")],
     reference={
         "type": "task_generation", "response_language": "ru",
         "message_to_user": "Четыре задачи, каждая — на один 20-минутный слот. Проверка простая: короткий отчёт, а для "
                            "посева — фото ящиков вместе с описанием.",
         "for_node_id": "n1",
         "tasks": [
             task("n1-t1", "Замерить температуру на балконе утром и вечером 3 дня подряд",
                  "Поставьте термометр и запишите температуру утром и вечером три дня подряд.",
                  "Зелени нужно тепло; замеры покажут, хватит ли его без обогрева.",
                  "Шесть записей температуры.", 10, 1,
                  protocol("habit", "low", [m("structured_self_report", "required", "Внесите шесть замеров.",
                                              fields=["День", "Утро", "Вечер"])],
                           ["Шесть замеров внесены"], "limited", True, "Замеры — ваши записи; этого достаточно для решения об обогреве."),
                  sessions=3),
             task("n1-t2", "Выбрать 3 вида зелени для прохладного балкона и купить семена",
                  "Выберите три неприхотливых вида и купите семена.", "Не вся зелень растёт в прохладе.",
                  "Три пакета семян.", 20, 1,
                  protocol("other", "low", [m("structured_self_report", "required", "Какие три вида выбраны и почему.")],
                           ["Названы три вида"], "limited", True, "Покупка — ваш отчёт; проверять чеки нет смысла.")),
             task("n1-t3", "Подготовить 3 ящика: дренаж и грунт",
                  "Насыпьте дренаж и грунт в три ящика.", "Хороший дренаж защищает корни от гнили.",
                  "Три ящика с грунтом.", 20, 1,
                  protocol("other", "medium",
                           [m("photo", "required", "Фото трёх ящиков с грунтом."),
                            m("structured_self_report", "required", "Какой дренаж и грунт использованы.")],
                           ["Три ящика готовы"], "medium", False, "Фото результата вместе с описанием дают среднюю уверенность."),
                  dependencies=["n1-t2"]),
             task("n1-t4", "Посеять 3 вида зелени и подписать ящики",
                  "Посейте семена по инструкции на пакете и подпишите ящики.", "Подписи помогут следить за всходами.",
                  "Три подписанных ящика с посевом.", 20, 1,
                  protocol("other", "medium",
                           [m("photo", "required", "Фото подписанных ящиков."),
                            m("structured_self_report", "required", "Дата посева и глубина заделки для каждого вида.")],
                           ["Три вида посеяны и подписаны"], "medium", False, "Фото и отчёт вместе дают среднюю уверенность."),
                  dependencies=["n1-t3"])],
         "decision_summary": None})

# --------------------------------------------------------------------------- verification protocol design

case("e2-vprot-01", title="Farewell toast rehearsal: audio, not video", case_type="atomic",
     seed_id=seed("es-farewell-toast", "en", "personal_development",
                  "Someone must give a three-minute farewell toast without notes and wants a rehearsal task verified."),
     scenario_group=scenario("bs-ev-vprot-spoken-performance-audio", "verification_protocol_design", "protocol_request",
                             "spoken_performance+video_unavailable", "audio_transcript_and_duration_check",
                             "A spoken performance is best checked by its own audio recording: the transcript shows "
                             "content and fillers, the duration shows timing."),
     strata=["verification_protocol", "capability_boundary", "en"],
     dimensions=["verification_quality"], language="en", input_language="en", domain="personal_development",
     focus=["Uses audio rather than asking for video", "Criteria are checkable from a transcript and duration"],
     task_type="verification_protocol_design",
     input=ctx("verification_protocol_design", T1,
               goal={"title": "Give a three-minute farewell toast without notes"},
               task=task("t-toast", "Rehearse the three-minute toast without notes and record the final run",
                         "Rehearse the toast three times without notes and record the last run.",
                         "Rehearsing out loud is what makes a no-notes toast possible.",
                         "A recording of a run-through under three and a half minutes without notes.", 30, 2)),
     checks=base_checks("en") + [
         lint_absent("capability_compliance", "VP_METHOD_UNAVAILABLE", "CAPABILITY_PROMISE"),
         lint_absent("evidence_integrity", "VP_CEILING_ABOVE_EVIDENCE", "VP_PHOTO_ONLY"),
         c("mentions_any", "verification_rigor", path="protocol.methods[*].method", terms=["audio"])],
     reference={
         "type": "verification_protocol_design", "response_language": "en", "task_id": "t-toast",
         "message_to_user": "Record the final run as audio — the transcript shows what you said and the recording "
                            "length shows your timing, which is exactly what this task is about. One quick question "
                            "afterwards about the part you found hardest.",
         "protocol": protocol("skill_acquisition", "high",
                              [m("audio", "required", "Upload the audio of the final run-through.",
                                 acceptance_criteria=["Under three and a half minutes", "No reading from notes audible"]),
                               m("follow_up_questions", "supplementary", "One reflection question.",
                                 questions=["Which part of the toast was hardest to remember, and why?"])],
                              ["A complete run-through under three and a half minutes"], "high", False,
                              "The recording is the performance itself, so length and content are checked directly.")})

case("e2-vprot-02", title="Market-stall profit: card export plus cash table", case_type="atomic",
     seed_id=seed("es-market-stall", "ru", "business",
                  "A maker sells at weekend craft fairs, card payments go through a terminal and some sales are cash; "
                  "the task is to find the most profitable of four fairs."),
     scenario_group=scenario("bs-ev-vprot-card-export-cash-table", "verification_protocol_design", "protocol_request",
                             "mixed_card_and_cash_records", "export_plus_user_table_medium",
                             "Part of the data comes from a terminal export, part only from the user's notes; the "
                             "protocol uses the export and caps confidence because cash is the user's word."),
     strata=["verification_protocol", "provenance", "ru"],
     dimensions=["verification_quality", "evidence_integrity"], language="ru", input_language="ru", domain="business",
     focus=["Уровень уверенности соответствует классу данных", "Не требует лишних личных данных покупателей"],
     task_type="verification_protocol_design",
     input=ctx("verification_protocol_design", T1,
               goal={"title": "Понять, какие ярмарки приносят прибыль"},
               task=task("t-fairs", "Посчитать выручку и расходы по 4 последним ярмаркам",
                         "Сведите выручку (карта и наличные) и расходы по каждой из четырёх ярмарок и найдите самую прибыльную.",
                         "Так станет видно, на какие ярмарки стоит ездить.",
                         "Таблица по 4 ярмаркам с прибылью и вывод.", 60, 2),
               conversation=say("Оплаты картой идут через терминал, есть выгрузка. Наличные записываю в тетрадь.")),
     checks=base_checks("ru") + [
         lint_absent("evidence_integrity", "VP_CEILING_ABOVE_EVIDENCE", "VP_SELF_REPORT_CEILING", "VP_INCONSISTENT"),
         c("one_of", "evidence_integrity", path="protocol.confidence_ceiling", values=["limited", "medium"])],
     reference={
         "type": "verification_protocol_design", "response_language": "ru", "task_id": "t-fairs",
         "message_to_user": "Для оплат картой загрузите выгрузку из терминала — её можно проверить напрямую. Наличные "
                            "и расходы внесите в таблицу: это ваши записи, поэтому итоговая уверенность будет средней. "
                            "Данные покупателей не нужны.",
         "protocol": protocol("business_activity", "medium",
                              [m("data_export", "required", "Выгрузка операций терминала за дни четырёх ярмарок (без данных покупателей)."),
                               m("structured_result", "required", "Таблица по ярмаркам: наличные, расходы, итог.",
                                 fields=["Ярмарка", "Карта", "Наличные", "Расходы", "Прибыль"])],
                              ["Сумма по карте совпадает с выгрузкой", "Прибыль посчитана для всех 4 ярмарок"],
                              "medium", False,
                              "Выгрузка проверяется напрямую, наличные и расходы — слова пользователя, поэтому потолок medium.")})

case("e2-vprot-03", title="Browser extension: fetch the public listing", case_type="atomic",
     seed_id=seed("es-browser-extension", "en", "programming",
                  "A developer is publishing a small browser extension and wants the 'published' task verified."),
     scenario_group=scenario("bs-ev-vprot-public-listing", "verification_protocol_design", "protocol_request",
                             "public_listing_exists", "fetch_listing_plus_source_high",
                             "A published artefact has a public page the system can fetch; together with the source it "
                             "justifies high confidence."),
     strata=["verification_protocol", "en"], dimensions=["verification_quality"],
     language="en", input_language="en", domain="programming",
     focus=["Uses the public listing instead of screenshots", "No account access requested"],
     task_type="verification_protocol_design",
     input=ctx("verification_protocol_design", T1,
               goal={"title": "Publish my first browser extension"},
               task=task("t-publish", "Publish the tab-grouping extension in the browser's extension store",
                         "Submit the extension for review and publish it once approved.",
                         "A public listing is the milestone that turns the project into a product.",
                         "A public store listing for the extension.", 90, 3)),
     checks=base_checks("en") + [
         c("mentions_any", "verification_rigor", path="protocol.methods[*].method", terms=["url_review"]),
         lint_absent("capability_compliance", "CAPABILITY_PROMISE", "VP_METHOD_UNAVAILABLE"),
         lint_absent("evidence_integrity", "VP_PHOTO_ONLY", "VP_WEAK_FOR_VERIFIABLE")],
     reference={
         "type": "verification_protocol_design", "response_language": "en", "task_id": "t-publish",
         "message_to_user": "Send the public store link: the app fetches the page once to confirm the listing is live. "
                            "Upload the source as a .zip too, so the version on the page can be matched to your code. "
                            "No screenshots or account access needed.",
         "protocol": protocol("software", "high",
                              [m("url_review", "required", "Submit the public store URL; the app fetches it once.",
                                 acceptance_criteria=["Listing is public", "Name and version match the submission"]),
                               m("artifact_review", "required", "Upload the source as a .zip.",
                                 acceptance_criteria=["Manifest version matches the listing"])],
                              ["Public listing live", "Listed version matches the source"], "high", False,
                              "A fetched public page and the source together are direct evidence.")})
