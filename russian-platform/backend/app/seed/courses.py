"""Structured learning paths. Phase 1 ships the full A0 course and the
first half of A1; later courses are added as content, not code."""


def lesson(slug, title, order, objectives, blocks, new_lemmas=None,
           grammar_slugs=None, threshold=0.8):
    return {
        "slug": slug, "title": title, "order_index": order,
        "objectives": objectives, "blocks": blocks,
        "new_lemmas": new_lemmas or [], "grammar_slugs": grammar_slugs or [],
        "mastery_threshold": threshold,
    }


def vocab_block(lemmas, note=""):
    return {"type": "vocabulary", "lemmas": lemmas, "note": note}


def grammar_block(slug):
    return {"type": "grammar_ref", "slug": slug}


def dialogue_block(title, lines):
    return {"type": "dialogue", "title": title,
            "lines": [{"speaker": s, "text": t, "translation": tr}
                      for s, t, tr in lines]}


def reading_block(title, text, translation):
    return {"type": "reading", "title": title, "text": text,
            "translation": translation}


def exercise_block(questions):
    return {"type": "exercise",
            "questions": [{"id": i, "prompt": p, "answer": a, "accept": acc}
                          for i, p, a, acc in questions]}


def mastery_block(questions):
    return {"type": "mastery_test",
            "questions": [{"id": i, "prompt": p, "answer": a, "accept": acc}
                          for i, p, a, acc in questions]}


def culture_block(title, body):
    return {"type": "culture", "title": title, "body": body}


COURSES = [
    {
        "slug": "a0-foundations",
        "title": "Foundations: Read & Greet",
        "cefr_level": "A0",
        "order_index": 1,
        "description": "From zero to reading Cyrillic, greeting people, and "
                       "introducing yourself. No prior knowledge assumed.",
        "lessons": [
            lesson(
                "a0-01-cyrillic-friends", "Cyrillic I: The Friendly Letters", 1,
                ["Recognize А К М О Т Е and the false friends В Н Р С У Х",
                 "Read your first real Russian words"],
                [grammar_block("cyrillic-alphabet"),
                 reading_block("First words you can already read",
                               "ко́т · то́рт · метро́ · рестора́н · Москва́ · спорт",
                               "cat · cake · metro · restaurant · Moscow · sport"),
                 exercise_block([
                     ("q1", "Transliterate: «кот»", "kot", []),
                     ("q2", "Transliterate: «метро»", "metro", []),
                     ("q3", "Cyrillic «С» sounds like which Latin letter?", "s", []),
                     ("q4", "Cyrillic «Р» sounds like which Latin letter?", "r", []),
                 ]),
                 mastery_block([
                     ("m1", "Transliterate: «Москва»", "moskva", ["maskva"]),
                     ("m2", "Transliterate: «спорт»", "sport", []),
                     ("m3", "Cyrillic «Н» sounds like which Latin letter?", "n", []),
                 ])],
                grammar_slugs=["cyrillic-alphabet"],
            ),
            lesson(
                "a0-02-cyrillic-new", "Cyrillic II: The New Shapes", 2,
                ["Learn Б Г Д Ж З И Л П Ф and read longer words",
                 "Meet Ы, Э, Ю, Я and the signs Ъ/Ь"],
                [grammar_block("cyrillic-alphabet"),
                 reading_block("Sound these out",
                               "банк · парк · такси́ · телефо́н · интерне́т · музе́й · пи́цца",
                               "bank · park · taxi · telephone · internet · museum · pizza"),
                 exercise_block([
                     ("q1", "Transliterate: «банк»", "bank", []),
                     ("q2", "Transliterate: «парк»", "park", []),
                     ("q3", "Which letter is the 'hard sign'? (ъ/ь)", "ъ", []),
                     ("q4", "Transliterate: «такси»", "taksi", ["taxi"]),
                 ]),
                 mastery_block([
                     ("m1", "Transliterate: «телефон»", "telefon", []),
                     ("m2", "Transliterate: «интернет»", "internet", []),
                     ("m3", "Which sign softens a consonant? (ъ/ь)", "ь", []),
                 ])],
                grammar_slugs=["cyrillic-alphabet"],
            ),
            lesson(
                "a0-03-stress", "Stress & the Music of Russian", 3,
                ["Understand stress marks and vowel reduction",
                 "Pronounce молоко́ and хорошо́ like a native"],
                [grammar_block("stress-and-reduction"),
                 exercise_block([
                     ("q1", "Unstressed «о» is pronounced like which vowel?", "a", []),
                     ("q2", "In «молоко́», which syllable is stressed? (1/2/3)", "3", []),
                     ("q3", "за́мок = castle; замо́к = ?", "lock", []),
                 ]),
                 mastery_block([
                     ("m1", "How many stressed syllables per Russian word?", "1", ["one"]),
                     ("m2", "«хорошо́» roughly sounds like: (harasho/horosho)", "harasho", []),
                 ])],
                grammar_slugs=["stress-and-reduction"],
            ),
            lesson(
                "a0-04-greetings", "Hello & Goodbye", 4,
                ["Greet formally and informally", "Say thank you and please"],
                [vocab_block(["здравствуйте", "привет", "до свидания", "пока",
                              "спасибо", "пожалуйста", "да", "нет"]),
                 dialogue_block("At the door", [
                     ("Анна", "Здра́вствуйте!", "Hello! (formal)"),
                     ("Иван", "Здра́вствуйте! Как дела́?", "Hello! How are you?"),
                     ("Анна", "Хорошо́, спаси́бо!", "Good, thank you!"),
                     ("Иван", "До свида́ния!", "Goodbye!"),
                 ]),
                 culture_block("ты vs вы",
                               "Russian has two 'you's. Use вы (and здра́вствуйте) with "
                               "strangers, elders, and at work; ты (and приве́т) with "
                               "friends and children. Switching to ты uninvited can "
                               "feel rude — let the older/senior person offer it."),
                 exercise_block([
                     ("q1", "Formal hello?", "здравствуйте", []),
                     ("q2", "Informal bye?", "пока", []),
                     ("q3", "'Thank you'?", "спасибо", []),
                 ]),
                 mastery_block([
                     ("m1", "Informal hi?", "привет", []),
                     ("m2", "Formal goodbye (2 words)?", "до свидания", []),
                     ("m3", "'Please / you're welcome'?", "пожалуйста", []),
                 ])],
                new_lemmas=["здравствуйте", "привет", "до свидания", "пока",
                            "спасибо", "пожалуйста", "да", "нет"],
            ),
            lesson(
                "a0-05-introductions", "Introducing Yourself", 5,
                ["Say your name and ask someone's name",
                 "Understand «Это...» sentences with no 'to be'"],
                [vocab_block(["меня зовут", "как", "это", "я", "ты", "вы", "кто", "что"]),
                 grammar_block("no-verb-to-be"),
                 dialogue_block("First meeting", [
                     ("Анна", "Здра́вствуйте! Меня́ зову́т А́нна. А вас?",
                      "Hello! My name is Anna. And yours?"),
                     ("Марк", "О́чень прия́тно, А́нна. Меня́ зову́т Марк.",
                      "Very nice to meet you, Anna. My name is Mark."),
                     ("Анна", "Кто э́то?", "Who is this?"),
                     ("Марк", "Э́то мой друг Ива́н.", "This is my friend Ivan."),
                 ]),
                 exercise_block([
                     ("q1", "'My name is' (2 words)", "меня зовут", []),
                     ("q2", "Translate: 'This is a house' (2 words)", "это дом", []),
                     ("q3", "'Who is this?' (2 words)", "кто это", []),
                 ]),
                 mastery_block([
                     ("m1", "Translate: 'I am a student' (2 words)", "я студент", []),
                     ("m2", "'What is this?' (2 words)", "что это", []),
                 ])],
                new_lemmas=["меня зовут", "как", "это", "я", "ты", "вы", "кто", "что"],
                grammar_slugs=["no-verb-to-be"],
            ),
            lesson(
                "a0-06-gender-family", "Family & the Three Genders", 6,
                ["Name family members", "Assign gender by ending",
                 "Use мой/моя/моё correctly"],
                [vocab_block(["мама", "папа", "брат", "сестра", "друг", "человек",
                              "кот", "собака"]),
                 grammar_block("gender"),
                 grammar_block("possessives"),
                 exercise_block([
                     ("q1", "Gender of «мама»? (m/f/n)", "f", ["feminine"]),
                     ("q2", "Gender of «брат»? (m/f/n)", "m", ["masculine"]),
                     ("q3", "... сестра (my)", "моя", []),
                     ("q4", "... друг (my)", "мой", []),
                 ]),
                 mastery_block([
                     ("m1", "Gender of «папа»? (m/f/n)", "m", ["masculine"]),
                     ("m2", "... собака (my)", "моя", []),
                     ("m3", "'This is my brother' (3 words)", "это мой брат", []),
                 ])],
                new_lemmas=["мама", "папа", "брат", "сестра", "друг", "человек",
                            "кот", "собака"],
                grammar_slugs=["gender", "possessives"],
            ),
        ],
    },
    {
        "slug": "a1-survival",
        "title": "Survival Russian",
        "cefr_level": "A1",
        "order_index": 2,
        "description": "Live a day in Russian: say where you live and work, "
                       "order food, count, and handle simple conversations.",
        "lessons": [
            lesson(
                "a1-01-where-you-live", "Where Do You Live?", 1,
                ["Conjugate жить and работать", "Say where things are with в/на + -е"],
                [vocab_block(["жить", "работать", "дом", "город", "улица", "школа",
                              "работа", "здесь", "там", "дома"]),
                 grammar_block("present-tense"),
                 grammar_block("prepositional-case"),
                 dialogue_block("Small talk", [
                     ("Марк", "Где вы живёте?", "Where do you live?"),
                     ("Анна", "Я живу́ в Москве́. А вы?", "I live in Moscow. And you?"),
                     ("Марк", "Я живу́ в Ло́ндоне, но рабо́таю в Москве́.",
                      "I live in London but work in Moscow."),
                 ]),
                 exercise_block([
                     ("q1", "я (жить) → я ...", "живу", []),
                     ("q2", "вы (жить) → вы ...", "живёте", ["живете"]),
                     ("q3", "в ... (Москва)", "москве", []),
                     ("q4", "на ... (работа)", "работе", []),
                 ]),
                 mastery_block([
                     ("m1", "'I live in Moscow' (4 words)", "я живу в москве", []),
                     ("m2", "они (работать) → они ...", "работают", []),
                     ("m3", "в ... (город)", "городе", []),
                 ])],
                new_lemmas=["жить", "работать", "дом", "город", "улица", "школа",
                            "работа", "здесь", "там", "дома"],
                grammar_slugs=["present-tense", "prepositional-case"],
            ),
            lesson(
                "a1-02-speaking", "Speaking & Understanding", 2,
                ["Say what languages you speak", "Survive a misunderstanding"],
                [vocab_block(["говорить", "понимать", "знать", "думать", "язык",
                              "русский", "хорошо", "плохой", "очень", "извините"]),
                 dialogue_block("Language check", [
                     ("Анна", "Вы говори́те по-ру́сски?", "Do you speak Russian?"),
                     ("Марк", "Да, немно́го. Я понима́ю, но говорю́ пло́хо.",
                      "Yes, a little. I understand but speak poorly."),
                     ("Анна", "Вы о́чень хорошо́ говори́те!", "You speak very well!"),
                 ]),
                 exercise_block([
                     ("q1", "я (говорить) → я ...", "говорю", []),
                     ("q2", "они (говорить) → они ...", "говорят", []),
                     ("q3", "'I don't understand' (3 words)", "я не понимаю", []),
                 ]),
                 mastery_block([
                     ("m1", "'Do you (formal) speak Russian?' (3 words + по-русски)",
                      "вы говорите по-русски", []),
                     ("m2", "я не (знать) → я не ...", "знаю", []),
                 ])],
                new_lemmas=["говорить", "понимать", "знать", "думать", "язык",
                            "русский", "хорошо", "плохой", "очень", "извините"],
                grammar_slugs=["present-tense"],
            ),
            lesson(
                "a1-03-cafe", "At the Café", 3,
                ["Order food and drinks with the accusative",
                 "Be polite: дайте, пожалуйста"],
                [vocab_block(["хотеть", "пить", "есть", "чай", "кофе", "вода",
                              "молоко", "хлеб", "магазин"]),
                 grammar_block("accusative-case"),
                 dialogue_block("Ordering", [
                     ("Официант", "Здра́вствуйте! Что вы хоти́те?",
                      "Hello! What would you like?"),
                     ("Марк", "Я хочу́ ко́фе с молоко́м, пожа́луйста.",
                      "I want a coffee with milk, please."),
                     ("Официант", "Хорошо́. Что-нибу́дь ещё?", "OK. Anything else?"),
                     ("Марк", "Да, да́йте во́ду, пожа́луйста. Спаси́бо!",
                      "Yes, give me water please. Thank you!"),
                 ]),
                 culture_block("Café etiquette",
                               "In Russia the waiter won't bring the bill until you "
                               "ask: «Счёт, пожа́луйста». Tipping ~10% is appreciated "
                               "but not obligatory."),
                 exercise_block([
                     ("q1", "я (хотеть) → я ...", "хочу", []),
                     ("q2", "Я пью ... (вода)", "воду", []),
                     ("q3", "Я читаю ... (книга)", "книгу", []),
                 ]),
                 mastery_block([
                     ("m1", "'I want tea' (3 words)", "я хочу чай", []),
                     ("m2", "они (хотеть) → они ...", "хотят", []),
                     ("m3", "Дайте ... , пожалуйста (вода)", "воду", []),
                 ])],
                new_lemmas=["хотеть", "пить", "есть", "чай", "кофе", "вода",
                            "молоко", "хлеб", "магазин"],
                grammar_slugs=["accusative-case"],
            ),
            lesson(
                "a1-04-numbers", "Counting & Shopping", 4,
                ["Count to ten", "Ask prices with сколько"],
                [vocab_block(["один", "два", "три", "четыре", "пять", "шесть",
                              "семь", "восемь", "девять", "десять", "сколько",
                              "деньги"]),
                 dialogue_block("At the market", [
                     ("Марк", "Ско́лько э́то сто́ит?", "How much does this cost?"),
                     ("Продавец", "Три́ста рубле́й.", "Three hundred rubles."),
                     ("Марк", "Хорошо́, да́йте два, пожа́луйста.",
                      "OK, give me two, please."),
                 ]),
                 exercise_block([
                     ("q1", "5 по-русски?", "пять", []),
                     ("q2", "8 по-русски?", "восемь", []),
                     ("q3", "'How much does this cost?' — Сколько это ...?", "стоит", []),
                     ("q4", "Числительное для 'one' с «книга»: ... книга", "одна", []),
                 ]),
                 mastery_block([
                     ("m1", "3 по-русски?", "три", []),
                     ("m2", "10 по-русски?", "десять", []),
                     ("m3", "7 по-русски?", "семь", []),
                 ])],
                new_lemmas=["один", "два", "три", "четыре", "пять", "шесть",
                            "семь", "восемь", "девять", "десять", "сколько",
                            "деньги"],
            ),
            lesson(
                "a1-05-have", "Having & Not Having", 5,
                ["Express possession with у меня есть",
                 "Say something is absent with нет + genitive"],
                [vocab_block(["у", "время", "год", "день", "ночь", "утро", "вечер",
                              "сегодня", "завтра", "вчера"]),
                 grammar_block("genitive-case"),
                 exercise_block([
                     ("q1", "'I have a cat' (4 words)", "у меня есть кот", []),
                     ("q2", "У меня нет ... (время)", "времени", []),
                     ("q3", "Это книга ... (брат)", "брата", []),
                 ]),
                 mastery_block([
                     ("m1", "'I have no money' (4 words)", "у меня нет денег", []),
                     ("m2", "Здесь нет ... (вода)", "воды", []),
                 ])],
                new_lemmas=["у", "время", "год", "день", "ночь", "утро", "вечер",
                            "сегодня", "завтра", "вчера"],
                grammar_slugs=["genitive-case"],
            ),
            lesson(
                "a1-06-review", "Checkpoint: A Day in Moscow", 6,
                ["Combine everything: greet, introduce, order, count, possess"],
                [reading_block(
                    "Один день",
                    "До́брое у́тро! Меня́ зову́т Марк. Я живу́ в Москве́ и рабо́таю "
                    "в ба́нке. У́тром я пью ко́фе с молоко́м и е́м хлеб. Сего́дня "
                    "хоро́шая пого́да. Ве́чером я до́ма: я чита́ю кни́гу и ду́маю "
                    "о рабо́те. У меня́ есть кот. Он то́же лю́бит молоко́!",
                    "Good morning! My name is Mark. I live in Moscow and work at a "
                    "bank. In the morning I drink coffee with milk and eat bread. "
                    "The weather is nice today. In the evening I'm at home: I read "
                    "a book and think about work. I have a cat. He also loves milk!"),
                 mastery_block([
                     ("m1", "'I live in Moscow' (4 words)", "я живу в москве", []),
                     ("m2", "'I want coffee' (3 words)", "я хочу кофе", []),
                     ("m3", "'I have a cat' (4 words)", "у меня есть кот", []),
                     ("m4", "я (пить) → я ...", "пью", []),
                     ("m5", "Formal hello?", "здравствуйте", []),
                     ("m6", "в ... (Москва)", "москве", []),
                     ("m7", "У меня нет ... (деньги)", "денег", []),
                     ("m8", "Gender of «окно»? (m/f/n)", "n", ["neuter"]),
                 ])],
                threshold=0.85,
            ),
        ],
    },
]
