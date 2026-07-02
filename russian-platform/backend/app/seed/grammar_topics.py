"""The grammar encyclopedia: a full A0→C2 curriculum catalog.

Core A0/A1 topics ship with complete lesson content and machine-checkable
drills. Later topics carry their curriculum position, summary, and section
outline; their full interactive content is authored in Phase 2 content
sprints (docs/ROADMAP.md) — the schema and renderer are identical.
"""


def topic(slug, title, title_native, level, order, summary,
          content=None, drills=None, prerequisites=None):
    return {
        "slug": slug, "title": title, "title_native": title_native,
        "cefr_level": level, "order_index": order, "summary": summary,
        "content": content or [], "drills": drills or [],
        "prerequisites": prerequisites or [],
    }


def md(title, body):
    return {"type": "markdown", "title": title, "body": body}


def drill(id_, prompt, answer, accept=None, explanation=""):
    return {"id": id_, "prompt": prompt, "answer": answer,
            "accept": accept or [], "explanation": explanation}


TOPICS = [
    topic(
        "cyrillic-alphabet", "The Cyrillic Alphabet", "Алфавит", "A0", 1,
        "All 33 letters, their sounds, and how to read your first words.",
        content=[
            md("Why Cyrillic is easier than it looks",
               "Russian uses 33 letters. Six look and sound like English (А К М О Т Е), "
               "some look familiar but sound different (В=v, Н=n, Р=r, С=s, У=u, Х=kh), "
               "and the rest are new shapes for sounds you mostly already know.\n\n"
               "Strategy: learn letters in these groups, not in dictionary order. "
               "After the first two groups you can already read МОСКВА, РЕСТОРАН, СПОРТ."),
            md("The three letter groups",
               "**Friends** (same look, same sound): А К М О Т\n\n"
               "**False friends** (same look, new sound): В [v] · Е [ye] · Н [n] · Р [r] · С [s] · У [u] · Х [kh]\n\n"
               "**New shapes**: Б Г Д Ж З И Й Л П Ф Ц Ч Ш Щ Ы Э Ю Я Ё Ъ Ь\n\n"
               "Use the Alphabet page for per-letter audio notes, IPA, and example words."),
            md("Reading practice",
               "Sound these out — they are loanwords you already know:\n\n"
               "спорт · парк · такси́ · кафе́ · метро́ · телефо́н · интерне́т · шокола́д · компью́тер"),
        ],
        drills=[
            drill("cyr1", "Which Latin letter does Cyrillic «В» sound like?", "v",
                  explanation="В is a false friend: it looks like B but sounds like V."),
            drill("cyr2", "Which Latin letter does Cyrillic «Н» sound like?", "n"),
            drill("cyr3", "Transliterate: «метро»", "metro"),
            drill("cyr4", "Transliterate: «спорт»", "sport"),
            drill("cyr5", "How many letters are in the Russian alphabet?", "33"),
        ],
    ),
    topic(
        "stress-and-reduction", "Word Stress & Vowel Reduction",
        "Ударение и редукция", "A0", 2,
        "Russian stress is unpredictable and unstressed vowels change sound.",
        prerequisites=["cyrillic-alphabet"],
        content=[
            md("One stressed syllable rules the word",
               "Every Russian word has exactly one stressed syllable, and it is not "
               "predictable from spelling — you learn it with the word (we mark it "
               "everywhere: молоко́). Stress can distinguish words: за́мок (castle) vs "
               "замо́к (lock), and пи́сать vs писа́ть is the difference between a vulgar "
               "word and 'to write'."),
            md("Vowel reduction: the 'malako' rule",
               "Unstressed **о** sounds like **а**: молоко́ → [malakó]. "
               "Unstressed **е** and **я** sound like **и**: язы́к → [yizýk].\n\n"
               "This is why native speech sounds different from spelling. When you "
               "read aloud, reduce every vowel that is not stressed."),
        ],
        drills=[
            drill("str1", "How is unstressed «о» pronounced?", "a",
                  accept=["like a", "[a]"], explanation="молоко́ = 'malako'."),
            drill("str2", "How many stressed syllables does a Russian word have?", "1",
                  accept=["one"]),
            drill("str3", "за́мок means castle. What does замо́к mean?", "lock",
                  explanation="Stress alone changes the meaning."),
        ],
    ),
    topic(
        "gender", "Noun Gender", "Род существительных", "A1", 3,
        "Every noun is masculine, feminine, or neuter — usually visible from the ending.",
        prerequisites=["cyrillic-alphabet"],
        content=[
            md("The ending tells you the gender",
               "**Masculine**: ends in a consonant or -й — дом, музе́й, чай\n\n"
               "**Feminine**: ends in -а/-я — кни́га, неде́ля, Росси́я\n\n"
               "**Neuter**: ends in -о/-е — окно́, мо́ре, письмо́\n\n"
               "Nouns in **-ь** can be either (день is m., ночь is f.) — memorize these."),
            md("Exceptions worth knowing",
               "Natural gender wins over endings: па́па (dad) and де́душка (grandpa) "
               "end in -а but are masculine — они declines like feminine nouns while "
               "adjectives agree masculine: мой па́па.\n\n"
               "Ко́фе is masculine by convention: вку́сный ко́фе."),
        ],
        drills=[
            drill("gen1", "Gender of «книга» (m/f/n)?", "f", accept=["feminine"]),
            drill("gen2", "Gender of «дом» (m/f/n)?", "m", accept=["masculine"]),
            drill("gen3", "Gender of «окно» (m/f/n)?", "n", accept=["neuter"]),
            drill("gen4", "Gender of «папа» (m/f/n)?", "m", accept=["masculine"],
                  explanation="Natural gender beats the -а ending."),
            drill("gen5", "Gender of «ночь» (m/f/n)?", "f", accept=["feminine"]),
        ],
    ),
    topic(
        "no-verb-to-be", "«This is…»: Sentences Without 'To Be'",
        "Предложения без глагола «быть»", "A1", 4,
        "Present-tense 'am/is/are' is simply omitted: Я студент. Это дом.",
        prerequisites=["gender"],
        content=[
            md("Drop the verb, keep the meaning",
               "Russian has no present-tense 'to be'. **Я студе́нт** = 'I [am a] "
               "student'. **Это дом** = 'This [is a] house'. No articles either — "
               "Russian has no 'a' or 'the' at all.\n\n"
               "Questions are made with intonation alone: **Это дом?** ('Is this a house?')"),
            md("Negation and past/future",
               "Negate with не: **Я не студе́нт.**\n\n"
               "In the past and future the verb returns: **Я был студе́нтом** (I was a "
               "student), **Я бу́ду до́ма** (I will be at home)."),
        ],
        drills=[
            drill("be1", "Translate: 'I am a student' (2 words)", "я студент"),
            drill("be2", "Translate: 'This is a house' (2 words)", "это дом"),
            drill("be3", "Translate: 'He is not at home' (3 words)", "он не дома"),
        ],
    ),
    topic(
        "cases-overview", "The Six Cases: A Map", "Шесть падежей", "A1", 5,
        "What cases are, why Russian needs them, and the job of each of the six.",
        prerequisites=["gender", "no-verb-to-be"],
        content=[
            md("Endings do what word order does in English",
               "In English, 'the dog bites the man' vs 'the man bites the dog' is pure "
               "word order. Russian marks the *role* of each noun with an ending, so "
               "word order becomes flexible and expressive.\n\n"
               "| Case | Core job | Question |\n|---|---|---|\n"
               "| Nominative | subject | кто? что? |\n"
               "| Genitive | of / possession / absence | кого́? чего́? |\n"
               "| Dative | to / for (recipient) | кому́? чему́? |\n"
               "| Accusative | direct object; direction | кого́? что? |\n"
               "| Instrumental | with / by means of | кем? чем? |\n"
               "| Prepositional | location; about | о ком? о чём? |"),
            md("Learning order",
               "You will learn them in usefulness order: Nominative (free — it's the "
               "dictionary form), then Prepositional (where things are), Accusative "
               "(objects & direction), Genitive (possession & 'there is no'), Dative, "
               "Instrumental. Each gets its own lesson with drills."),
        ],
        drills=[
            drill("case1", "How many cases does Russian have?", "6", accept=["six"]),
            drill("case2", "Which case marks the subject of a sentence?", "nominative"),
            drill("case3", "Which case answers «где?» for location?", "prepositional"),
            drill("case4", "Which case marks the direct object?", "accusative"),
        ],
    ),
    topic(
        "prepositional-case", "Prepositional Case: Saying Where",
        "Предложный падеж", "A1", 6,
        "в/на + -е endings for location: в Москве́, на рабо́те.",
        prerequisites=["cases-overview"],
        content=[
            md("The formula",
               "Location = **в/на + noun with -е**.\n\n"
               "Москва́ → в Москве́ · го́род → в го́роде · рабо́та → на рабо́те · "
               "стол → на столе́\n\n"
               "Feminine -ия and neuter -ие take -ии: Росси́я → в Росси́и. "
               "Nouns in -ь (f.) take -и: в тетра́ди."),
            md("в or на?",
               "**в** = inside a bounded space: в до́ме, в го́роде, в Росси́и.\n\n"
               "**на** = on a surface or at an event/open place: на столе́, на конце́рте, "
               "на у́лице. Some words idiomatically take на: на рабо́те, на по́чте, "
               "на вокза́ле — learn them as fixed pairs."),
        ],
        drills=[
            drill("prep1", "Put «Москва» in the prepositional: в ...", "москве"),
            drill("prep2", "Put «город» in the prepositional: в ...", "городе"),
            drill("prep3", "'at work': на ...", "работе"),
            drill("prep4", "'in Russia': в ...", "россии"),
            drill("prep5", "Which preposition goes with «концерт» (at a concert)?", "на"),
        ],
    ),
    topic(
        "present-tense", "Present Tense: The Two Conjugations",
        "Настоящее время", "A1", 7,
        "First (-ешь) and second (-ишь) conjugation patterns cover nearly every verb.",
        prerequisites=["no-verb-to-be"],
        content=[
            md("First conjugation (е-pattern): знать → зна́ю",
               "я зна́**ю** · ты зна́**ешь** · он зна́**ет** · мы зна́**ем** · "
               "вы зна́**ете** · они зна́**ют**\n\n"
               "Most verbs in -ать/-ять work like this: рабо́тать, чита́ть, понима́ть, де́лать."),
            md("Second conjugation (и-pattern): говорить → говорю́",
               "я говор**ю́** · ты говор**и́шь** · он говор**и́т** · мы говор**и́м** · "
               "вы говор**и́те** · они говор**я́т**\n\n"
               "Most verbs in -ить work like this: люби́ть, ходи́ть, учи́ть. Watch for "
               "first-person changes: люблю́, хожу́, учу́."),
            md("The big irregular: хотеть",
               "хочу́, хо́чешь, хо́чет — but хоти́м, хоти́те, хотя́т. It switches "
               "conjugation between singular and plural; native children get this "
               "wrong too."),
        ],
        drills=[
            drill("pres1", "Conjugate: я (знать) → я ...", "знаю"),
            drill("pres2", "Conjugate: ты (работать) → ты ...", "работаешь"),
            drill("pres3", "Conjugate: они (говорить) → они ...", "говорят"),
            drill("pres4", "Conjugate: я (любить) → я ...", "люблю",
                  explanation="An -л- appears in the 1st person singular."),
            drill("pres5", "Conjugate: они (хотеть) → они ...", "хотят"),
            drill("pres6", "Conjugate: мы (жить) → мы ...", "живём", accept=["живем"]),
        ],
    ),
    topic(
        "accusative-case", "Accusative Case: Objects & Direction",
        "Винительный падеж", "A1", 8,
        "Marking what you see/read/love, and where you're heading.",
        prerequisites=["prepositional-case", "present-tense"],
        content=[
            md("The endings",
               "**Feminine -а/-я → -у/-ю**: кни́га → Я чита́ю кни́г**у**; Москва́ → в Москв**у́**.\n\n"
               "**Masculine inanimate & neuter: no change**: Я ви́жу дом. Я пью молоко́.\n\n"
               "**Masculine animate = genitive form**: Я ви́жу бра́т**а**. Animacy matters "
               "only in the accusative."),
            md("Location vs direction — the в/на contrast",
               "Same prepositions, different case:\n\n"
               "Я живу́ **в Москве́** (prepositional — where I am)\n\n"
               "Я е́ду **в Москву́** (accusative — where I'm heading)\n\n"
               "This pair is the single highest-value case contrast in Russian."),
        ],
        drills=[
            drill("acc1", "Я читаю ... (книга)", "книгу"),
            drill("acc2", "Я еду в ... (Москва)", "москву"),
            drill("acc3", "Я вижу ... (брат)", "брата",
                  explanation="Animate masculine takes the genitive-looking form."),
            drill("acc4", "Я вижу ... (дом)", "дом",
                  explanation="Inanimate masculine doesn't change."),
            drill("acc5", "Мы идём на ... (работа)", "работу"),
        ],
    ),
    topic(
        "genitive-case", "Genitive Case: Possession & Absence",
        "Родительный падеж", "A1", 9,
        "'of', 'у меня есть', 'нет чего-то', and counting.",
        prerequisites=["accusative-case"],
        content=[
            md("The endings",
               "**Masculine/neuter → -а/-я**: дом → до́ма, окно́ → окна́, чай → ча́я\n\n"
               "**Feminine → -ы/-и**: кни́га → кни́ги, неде́ля → неде́ли\n\n"
               "Core jobs: possession (кни́га бра́та — brother's book), absence "
               "(нет воды́ — there's no water), quantity (мно́го де́нег), and after "
               "numbers 2-4 (два до́ма) and 5+ (пять домо́в, genitive plural)."),
            md("У меня есть — the Russian 'to have'",
               "Russian rarely uses a verb 'to have'. Instead: **У меня́ есть кот** — "
               "lit. 'by me there-is a cat'. Negative drops есть and puts the object "
               "in genitive: **У меня́ нет кота́.**"),
        ],
        drills=[
            drill("gen_c1", "У меня нет ... (время)", "времени",
                  explanation="время is an irregular -мя noun: gen. времени."),
            drill("gen_c2", "У меня нет ... (деньги)", "денег"),
            drill("gen_c3", "Это книга ... (брат)", "брата"),
            drill("gen_c4", "Здесь нет ... (вода)", "воды"),
            drill("gen_c5", "Translate: 'I have a cat' (4 words)", "у меня есть кот"),
        ],
    ),
    topic(
        "verb-aspect-intro", "Verb Aspect: The Big Idea",
        "Вид глагола", "A2", 10,
        "Imperfective (process/repetition) vs perfective (completed result) — the soul of the Russian verb.",
        prerequisites=["present-tense"],
        content=[
            md("Two verbs for every action",
               "Almost every English verb maps to a Russian *pair*: "
               "чита́ть/прочита́ть, писа́ть/написа́ть, говори́ть/сказа́ть.\n\n"
               "**Imperfective** = process, repetition, or the fact an activity happened: "
               "Вчера́ я чита́л кни́гу (I was reading / spent time reading).\n\n"
               "**Perfective** = one completed action with a result: "
               "Вчера́ я прочита́л кни́гу (I finished the book)."),
            md("Consequences you must internalize",
               "1. Perfective verbs have **no present tense** — a completed action "
               "can't be happening now. Present-looking forms of perfectives mean "
               "future: Я прочита́ю = I will read (to completion).\n\n"
               "2. Choose aspect every time you use a past or future verb. When "
               "narrating repeated/habitual actions, use imperfective; for a chain of "
               "one-off completed events, perfective."),
        ],
        drills=[
            drill("asp1", "Which aspect expresses a completed result? (imperfective/perfective)",
                  "perfective"),
            drill("asp2", "Which aspect has NO present tense?", "perfective"),
            drill("asp3", "Perfective partner of «говорить»?", "сказать"),
            drill("asp4", "'I was reading (process)': Я ... книгу (читал/прочитал)", "читал"),
        ],
    ),
    topic(
        "past-tense", "Past Tense", "Прошедшее время", "A2", 11,
        "One of the easiest parts of Russian: -л agrees with gender, not person.",
        prerequisites=["present-tense", "gender"],
        content=[
            md("Four forms, no persons",
               "Drop -ть, add **-л** (m), **-ла** (f), **-ло** (n), **-ли** (pl):\n\n"
               "он чита́л · она чита́ла · оно чита́ло · они чита́ли\n\n"
               "'I' and 'you' agree with the speaker's gender: Я чита́л (male speaker) "
               "vs Я чита́ла (female speaker)."),
            md("Irregulars to memorize",
               "идти́ → шёл, шла, шли · мочь → мог, могла́, могли́ · "
               "есть → ел, е́ла, е́ли. быть is regular: был, была́, бы́ло, бы́ли — "
               "note the shifting stress in была́."),
        ],
        drills=[
            drill("past1", "Она ... (работать) вчера", "работала"),
            drill("past2", "Мы ... (жить) в Москве", "жили"),
            drill("past3", "Past of «идти» for «он»?", "шёл", accept=["шел"]),
            drill("past4", "Я (female) ... (быть) дома", "была"),
        ],
    ),
    topic(
        "possessives", "Possessives & Agreement", "Притяжательные местоимения",
        "A1", 12,
        "мой/моя/моё/мои and friends agree with the thing possessed.",
        prerequisites=["gender"],
        content=[
            md("Agree with the noun, not the owner",
               "| owner | m | f | n | pl |\n|---|---|---|---|---|\n"
               "| my | мой | моя́ | моё | мои́ |\n"
               "| your (ты) | твой | твоя́ | твоё | твои́ |\n"
               "| our | наш | на́ша | на́ше | на́ши |\n"
               "| your (вы) | ваш | ва́ша | ва́ше | ва́ши |\n\n"
               "**его́ (his), её (her), их (their) never change**: его́ дом, его́ кни́га."),
        ],
        drills=[
            drill("pos1", "... книга (my)", "моя"),
            drill("pos2", "... дом (my)", "мой"),
            drill("pos3", "... окно (our)", "наше"),
            drill("pos4", "... книга (his)", "его",
                  explanation="его never agrees — same form for all genders."),
        ],
    ),

    # ------------------- curriculum catalog: authored in content sprints --
    topic("dative-case", "Dative Case: To & For", "Дательный падеж", "A2", 13,
          "Recipients (Я даю́ бра́ту...), age (Мне 20 лет), and feelings (Мне хо́лодно).",
          prerequisites=["genitive-case"]),
    topic("instrumental-case", "Instrumental Case", "Творительный падеж", "A2", 14,
          "'with' and 'by means of': с дру́гом, писа́ть ру́чкой; professions with быть.",
          prerequisites=["dative-case"]),
    topic("adjective-declension", "Adjective Declension", "Склонение прилагательных",
          "A2", 15, "Adjectives agree in gender, number, AND case with their noun.",
          prerequisites=["accusative-case", "possessives"]),
    topic("future-tense", "Future Tense", "Будущее время", "A2", 16,
          "Compound future (бу́ду чита́ть) vs perfective future (прочита́ю).",
          prerequisites=["verb-aspect-intro", "past-tense"]),
    topic("motion-verbs-1", "Verbs of Motion I", "Глаголы движения I", "A2", 17,
          "идти́/ходи́ть, е́хать/е́здить: unidirectional vs multidirectional.",
          prerequisites=["verb-aspect-intro"]),
    topic("reflexive-verbs", "Reflexive Verbs", "Возвратные глаголы", "A2", 18,
          "-ся verbs: учи́ться, называ́ться, встреча́ться.",
          prerequisites=["present-tense"]),
    topic("imperative", "The Imperative", "Повелительное наклонение", "A2", 19,
          "Commands and requests: Скажи́(те)! Дава́й(те)...!",
          prerequisites=["present-tense"]),
    topic("plural-declension", "Plurals Across Cases", "Множественное число", "A2", 20,
          "Plural endings for all six cases, including the genitive plural minefield.",
          prerequisites=["genitive-case"]),
    topic("short-adjectives", "Short-Form Adjectives", "Краткие прилагательные",
          "B1", 21, "рад, гото́в, ну́жен — predicative forms and when to prefer them.",
          prerequisites=["adjective-declension"]),
    topic("motion-verbs-2", "Verbs of Motion II: Prefixes", "Глаголы движения II",
          "B1", 22, "при-, у-, в-, вы-, пере-, до- turn motion verbs into a GPS system.",
          prerequisites=["motion-verbs-1"]),
    topic("aspect-mastery", "Aspect in Depth", "Вид: тонкости", "B1", 23,
          "Aspect in the imperative, infinitive, negation, and annulled results.",
          prerequisites=["verb-aspect-intro", "future-tense"]),
    topic("comparatives", "Comparatives & Superlatives", "Степени сравнения", "B1", 24,
          "бо́льше, лу́чше, интере́снее; са́мый + adjective.",
          prerequisites=["adjective-declension"]),
    topic("numerals-declension", "Numerals & Counting", "Числительные", "B1", 25,
          "The full counting system: 2-4 + gen.sg., 5+ + gen.pl., declining numerals.",
          prerequisites=["plural-declension"]),
    topic("time-expressions", "Time Expressions", "Выражение времени", "B1", 26,
          "в + acc. for days, в + prep. for months, telling the time, dates.",
          prerequisites=["numerals-declension"]),
    topic("conditional", "Conditional & Subjunctive", "Условное наклонение", "B1", 27,
          "бы + past: е́сли бы я знал... — hypotheticals and polite requests.",
          prerequisites=["past-tense"]),
    topic("relative-clauses", "Relative Clauses with кото́рый", "Слово «который»",
          "B1", 28, "кото́рый declines by its role in the relative clause.",
          prerequisites=["adjective-declension"]),
    topic("impersonal", "Impersonal Constructions", "Безличные предложения", "B2", 29,
          "Мне ну́жно, мо́жно, нельзя́, хо́чется — Russian's subjectless sentences.",
          prerequisites=["dative-case"]),
    topic("participles", "Participles", "Причастия", "B2", 30,
          "чита́ющий, прочи́танный: verbal adjectives of written Russian.",
          prerequisites=["aspect-mastery", "relative-clauses"]),
    topic("gerunds", "Gerunds (Verbal Adverbs)", "Деепричастия", "B2", 31,
          "чита́я, прочита́в: doing two things in one sentence.",
          prerequisites=["participles"]),
    topic("reported-speech", "Reported Speech", "Косвенная речь", "B2", 32,
          "Он сказа́л, что... / попроси́л, что́бы... — no backshifting of tense.",
          prerequisites=["conditional"]),
    topic("word-order", "Word Order & Information Structure", "Порядок слов", "B2", 33,
          "Free but not random: theme-rheme, emphasis, and intonation constructions.",
          prerequisites=["relative-clauses"]),
    topic("complex-syntax", "Complex Sentences & Conjunctions", "Сложные предложения",
          "C1", 34, "несмотря́ на то, что...; поско́льку; ли́бо...ли́бо — advanced connectors.",
          prerequisites=["reported-speech", "word-order"]),
    topic("style-registers", "Style & Register", "Стили речи", "C1", 35,
          "Official, academic, journalistic, colloquial: switching registers deliberately.",
          prerequisites=["complex-syntax"]),
    topic("punctuation", "Punctuation", "Пунктуация", "C1", 36,
          "The comma rules of Russian are strict and testable — master them.",
          prerequisites=["complex-syntax"]),
]
