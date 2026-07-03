"""Phase 2 grammar content: fills in the A2–C1 catalog topics and adds C2.

Merged into the TOPICS catalog by grammar_topics.py. Same schema as the
Phase 1 core topics: markdown sections + machine-checkable drills.
"""
from app.seed.grammar_topics import drill, md, topic

CONTENT = {
    "dative-case": {
        "content": [
            md("The endings",
               "**Masculine/neuter → -у/-ю**: брат → бра́ту, окно́ → окну́, учи́тель → учи́телю\n\n"
               "**Feminine → -е** (-и for -ия/-ь): сестра́ → сестре́, Мари́я → Мари́и, дверь → две́ри\n\n"
               "Pronouns: мне, тебе́, ему́, ей, нам, вам, им."),
            md("When to use it",
               "**Recipient**: Я даю́ кни́гу бра́ту (I give the book TO my brother).\n\n"
               "**Age**: Мне два́дцать лет — age belongs to the dative person.\n\n"
               "**Feelings & states**: Мне хо́лодно / ску́чно / на́до идти́ — 'to me (it is) cold'.\n\n"
               "**After verbs**: помога́ть, звони́ть, ве́рить, отвеча́ть + dative: Позвони́ ма́ме!"),
        ],
        "drills": [
            drill("dat1", "Я звоню́ ... (мама)", "маме"),
            drill("dat2", "Помоги́ ... (брат)!", "брату"),
            drill("dat3", "'I am 20 years old': ... двадцать лет (я → dative)", "мне"),
            drill("dat4", "Да́йте ... (сестра) чай", "сестре"),
            drill("dat5", "Which case follows «помогать»?", "dative", ["дательный"]),
        ],
    },
    "instrumental-case": {
        "content": [
            md("The endings",
               "**Masculine/neuter → -ом/-ем**: брат → бра́том, мо́ре → мо́рем\n\n"
               "**Feminine → -ой/-ей**: сестра́ → сестро́й, неде́ля → неде́лей; -ь → -ью: дверь → две́рью\n\n"
               "Pronouns: мной, тобо́й, им, ей, на́ми, ва́ми, и́ми."),
            md("With and by means of",
               "**Accompaniment** with с: ко́фе с молоко́м, я иду́ с дру́гом.\n\n"
               "**Instrument** (no preposition!): писа́ть ру́чкой (write WITH a pen), е́хать по́ездом.\n\n"
               "**Professions with быть/стать**: Он был инжене́ром. Она́ ста́ла врачо́м.\n\n"
               "**Time of day/season as adverbs**: у́тром, ве́чером, зимо́й, ле́том."),
        ],
        "drills": [
            drill("ins1", "ко́фе с ... (молоко)", "молоком"),
            drill("ins2", "Я пишу́ ... (ручка)", "ручкой"),
            drill("ins3", "Он стал ... (врач)", "врачом"),
            drill("ins4", "'in winter' (one word)", "зимой"),
            drill("ins5", "Я иду́ в кино́ с ... (друг)", "другом"),
        ],
    },
    "adjective-declension": {
        "content": [
            md("Adjectives follow their noun everywhere",
               "An adjective copies gender, number, AND case:\n\n"
               "но́вый дом → в но́вом до́ме → о́коло но́вого до́ма\n\n"
               "| case | m/n | f | pl |\n|---|---|---|---|\n"
               "| gen | -ого/-его | -ой/-ей | -ых/-их |\n"
               "| dat | -ому/-ему | -ой/-ей | -ым/-им |\n"
               "| ins | -ым/-им | -ой/-ей | -ыми/-ими |\n"
               "| pre | -ом/-ем | -ой/-ей | -ых/-их |"),
            md("The -ого secret",
               "The г in -ого/-его is pronounced **[в]**: но́вого = [но́вава], "
               "сего́дня = [siво́дня] (it's an old genitive!).\n\n"
               "Accusative follows the noun's animacy: ви́жу но́вый дом (inanim.) "
               "but ви́жу но́вого дру́га (anim. = genitive form)."),
        ],
        "drills": [
            drill("adjd1", "в ... до́ме (новый)", "новом"),
            drill("adjd2", "У меня́ нет ... маши́ны (новая)", "новой"),
            drill("adjd3", "Я ви́жу ... дру́га (старый)", "старого"),
            drill("adjd4", "How is the г in «нового» pronounced?", "v", ["в", "[v]"]),
        ],
    },
    "future-tense": {
        "content": [
            md("Two futures, one choice: aspect",
               "**Imperfective future** = бу́ду + infinitive (process/repetition):\n\n"
               "За́втра я бу́ду чита́ть весь день. (I'll be reading all day.)\n\n"
               "**Perfective future** = perfective verb in present-tense form (one completed act):\n\n"
               "За́втра я прочита́ю э́ту кни́гу. (I'll finish this book tomorrow.)"),
            md("буду conjugates, the infinitive doesn't",
               "я бу́ду, ты бу́дешь, он бу́дет, мы бу́дем, вы бу́дете, они бу́дут + чита́ть.\n\n"
               "Never combine бу́ду with a perfective infinitive: ~~бу́ду прочита́ть~~ is "
               "impossible — a completed action can't be an ongoing process."),
        ],
        "drills": [
            drill("fut1", "За́втра я ... рабо́тать (будущее от «быть», я)", "буду"),
            drill("fut2", "Они ... смотре́ть фильм (будущее, они)", "будут"),
            drill("fut3", "'I will finish reading' — я ... (прочитать, future)", "прочитаю"),
            drill("fut4", "Can «буду» combine with a perfective infinitive? (да/нет)", "нет", ["no"]),
        ],
    },
    "motion-verbs-1": {
        "content": [
            md("One way vs many ways",
               "Russian splits every motion verb in two:\n\n"
               "**идти́ / е́хать** — one direction, right now: Я иду́ в шко́лу. (I'm on my way.)\n\n"
               "**ходи́ть / е́здить** — repeated trips, round trips, or 'in general': "
               "Я хожу́ в шко́лу ка́ждый день. Вчера́ мы ходи́ли в кино́ (went & came back).\n\n"
               "идти́/ходи́ть = on foot; е́хать/е́здить = by vehicle."),
            md("The four verbs in action",
               "| | on foot | by vehicle |\n|---|---|---|\n"
               "| one direction | иду́, идёшь | е́ду, е́дешь |\n"
               "| multidirectional | хожу́, хо́дишь | е́зжу, е́здишь |\n\n"
               "Куда́ ты идёшь? (right now) vs Куда́ ты хо́дишь по вечера́м? (habitually)"),
        ],
        "drills": [
            drill("mot1", "Right now: Я ... в парк (идти/ходить, я)", "иду"),
            drill("mot2", "Every day: Я ... на рабо́ту пешко́м (идти/ходить, я)", "хожу"),
            drill("mot3", "By car, now: Мы ... в Москву́ (ехать, мы)", "едем"),
            drill("mot4", "Which verb for a completed round trip yesterday: ходил или шёл?", "ходил"),
        ],
    },
    "reflexive-verbs": {
        "content": [
            md("-ся: the verb turns inward",
               "Attach **-ся** (after consonant) / **-сь** (after vowel): "
               "учи́ться → учу́сь, у́чишься, у́чится.\n\n"
               "Meanings: true reflexive (мы́ться — wash oneself), reciprocal "
               "(встреча́ться — meet each other), passive (магази́н открыва́ется в 9), "
               "and verbs that simply require it (смея́ться, боя́ться, наде́яться)."),
            md("Case warning",
               "Reflexive verbs never take a direct accusative object. Compare: "
               "Я учу́ слова́ (memorize words) vs Я учу́сь в университе́те (study at). "
               "занима́ться takes instrumental: занима́юсь спо́ртом."),
        ],
        "drills": [
            drill("ref1", "я (учиться) → я ...", "учусь"),
            drill("ref2", "он (учиться) → он ...", "учится"),
            drill("ref3", "Я занима́юсь ... (спорт)", "спортом"),
            drill("ref4", "After a vowel, -ся becomes ...", "сь", ["-сь"]),
        ],
    },
    "imperative": {
        "content": [
            md("Making commands",
               "From the они-form stem: чита́ют → **чита́й(те)**; говоря́т → **говори́(те)**; "
               "ждут → **жди(те)**.\n\n"
               "Rule: stem ends in a vowel → -й; ends in a consonant + end-stress → -и́; "
               "consonant + stem stress → -ь (гото́вят → гото́вь).\n\n"
               "-те makes it polite/plural: Скажи́те, пожа́луйста!"),
            md("Aspect in commands",
               "**Perfective** for a single request: Откро́й окно́! (Open the window!)\n\n"
               "**Imperfective** for invitations and general advice: Заходи́те! Сади́тесь! "
               "(Come in! Sit down!) — and for NEGATIVE commands: Не открыва́й окно́!\n\n"
               "Дава́й(те) + future/infinitive = let's: Дава́й пойдём! Дава́йте чита́ть!"),
        ],
        "drills": [
            drill("imp1", "Imperative of «говорить» (formal): ...!", "говорите"),
            drill("imp2", "Imperative of «читать» (informal): ...!", "читай"),
            drill("imp3", "'Let's go!': ... пойдём!", "давай"),
            drill("imp4", "Negative commands use which aspect?", "imperfective", ["несовершенный"]),
        ],
    },
    "plural-declension": {
        "content": [
            md("Plural endings across cases",
               "| case | ending | example |\n|---|---|---|\n"
               "| nom | -ы/-и/-а | столы́, кни́ги, окна́ |\n"
               "| gen | -ов/-ей/-∅ | столо́в, двере́й, книг |\n"
               "| dat | -ам/-ям | стола́м, книга́м |\n"
               "| acc | =nom (inan.) / =gen (anim.) | ви́жу столы́ / студе́нтов |\n"
               "| ins | -ами/-ями | стола́ми |\n"
               "| pre | -ах/-ях | о стола́х |"),
            md("The genitive plural minefield",
               "Three patterns: **-ов** for hard masculines (столо́в), **-ей** for "
               "soft/-ь/husher stems (друзе́й, ноче́й, враче́й), **zero ending** for "
               "feminines in -а and neuters in -о (книг, окон, мест).\n\n"
               "Zero endings often insert о/е inside clusters: де́вушка → де́вушек, "
               "окно́ → о́кон. After мно́го, ма́ло, ско́лько, нет — always genitive plural."),
        ],
        "drills": [
            drill("plu1", "мно́го ... (книга)", "книг"),
            drill("plu2", "пять ... (стол)", "столов"),
            drill("plu3", "мно́го ... (друг)", "друзей"),
            drill("plu4", "Я говорю́ о ... (книги, prep. pl.)", "книгах"),
        ],
    },
    "short-adjectives": {
        "content": [
            md("The predicative short form",
               "Many adjectives have a short form used only as a predicate: "
               "рад/ра́да/ра́ды (glad), гото́в/гото́ва/гото́вы (ready), за́нят/занята́ "
               "(busy), ну́жен/нужна́/ну́жно (needed), бо́лен (ill).\n\n"
               "Я гото́в. Она́ занята́. Мы ра́ды вас ви́деть."),
            md("нужен — the possession pattern",
               "'I need X' = X is-needed to-me: **Мне ну́жен слова́рь** (m), "
               "**Мне нужна́ по́мощь** (f), **Мне ну́жно вре́мя** (n), **Мне нужны́ де́ньги** (pl).\n\n"
               "The needed thing is the subject; the needer goes to the dative."),
        ],
        "drills": [
            drill("sha1", "Мне ... слова́рь (нужен/нужна/нужно)", "нужен"),
            drill("sha2", "Мне ... по́мощь (нужен/нужна/нужно)", "нужна"),
            drill("sha3", "Мне ... де́ньги (нужны/нужно)", "нужны"),
            drill("sha4", "Она́ ... (занят, f)", "занята"),
        ],
    },
    "motion-verbs-2": {
        "content": [
            md("Prefixes turn motion into GPS",
               "| prefix | meaning | example |\n|---|---|---|\n"
               "| при- | arrival | прийти́, прие́хать — arrive |\n"
               "| у- | departure | уйти́, уе́хать — leave |\n"
               "| в- | into | войти́ — enter |\n"
               "| вы- | out of | вы́йти — exit |\n"
               "| пере- | across | перейти́ у́лицу |\n"
               "| до- | as far as | дойти́ до це́нтра |\n"
               "| за- | drop in | зайти́ к дру́гу |"),
            md("Prefixed = ordinary aspect pairs",
               "Prefixed motion verbs stop being 'motion verbs': прийти́ (pf.) / "
               "приходи́ть (impf.) behave like any aspect pair.\n\n"
               "Он пришёл в семь. (He arrived at seven — once.)\n\n"
               "Он прихо́дит в семь. (He arrives at seven — every day.)"),
        ],
        "drills": [
            drill("mv21", "Prefix meaning 'arrival'?", "при", ["при-"]),
            drill("mv22", "'to exit' = ...йти", "вы", ["вы-"]),
            drill("mv23", "Он ... у́лицу (перейти, past m)", "перешёл", ["перешел"]),
            drill("mv24", "'He arrives every day': Он ... ка́ждый день (приходить)", "приходит"),
        ],
    },
    "aspect-mastery": {
        "content": [
            md("Aspect beyond the basics",
               "**Negation**: не + perfective = failure (Он не реши́л зада́чу — tried, "
               "couldn't); не + imperfective = didn't even start (Он не реша́л — didn't do it).\n\n"
               "**Annulled result**: imperfective for actions later reversed: "
               "Ко мне приходи́л друг (he came AND left) vs пришёл (he's still here).\n\n"
               "**Infinitive after verbs**: начина́ть/продолжа́ть/конча́ть take ONLY "
               "imperfective: на́чал чита́ть."),
            md("The general-factual imperfective",
               "To state that an event simply took place — without focusing on its "
               "completion — Russian uses the imperfective: **Ты чита́л «Войну́ и мир»?** "
               "(Have you [ever] read War and Peace?)\n\n"
               "Use perfective when the specific result matters: **Ты прочита́л статью́, "
               "кото́рую я присла́л?** (Did you finish THE article?)"),
        ],
        "drills": [
            drill("am1", "После «начать» — какой вид? (perfective/imperfective)", "imperfective"),
            drill("am2", "'Have you ever read Tolstoy?' — Ты ... Толсто́го? (читал/прочитал)", "читал"),
            drill("am3", "Guest came and left: Ко мне ... друг (приходил/пришёл)", "приходил"),
        ],
    },
    "comparatives": {
        "content": [
            md("Making comparisons",
               "**Simple comparative** = stem + -ее: интере́сный → интере́снее; "
               "irregulars: хоро́ший → лу́чше, плохо́й → ху́же, большо́й → бо́льше, "
               "ма́ленький → ме́ньше, ста́рый → ста́рше, молодо́й → мла́дше.\n\n"
               "Than = чем (…, чем я) or genitive without чем: Он ста́рше меня́."),
            md("Superlatives",
               "**са́мый + adjective**: са́мый большо́й го́род (the biggest city).\n\n"
               "Bookish forms in -е́йший/-а́йший exist (важне́йший, велича́йший) — "
               "recognize them in reading; use са́мый in speech."),
        ],
        "drills": [
            drill("cmp1", "Comparative of «хороший»?", "лучше"),
            drill("cmp2", "Comparative of «плохой»?", "хуже"),
            drill("cmp3", "Он ста́рше ... (я → genitive)", "меня"),
            drill("cmp4", "'the most beautiful city': ... краси́вый го́род", "самый"),
        ],
    },
    "numerals-declension": {
        "content": [
            md("The counting rules",
               "**1** agrees: оди́н дом, одна́ кни́га.\n\n"
               "**2–4** (and 22, 33, …): genitive **singular**: два до́ма, три кни́ги.\n\n"
               "**5–20** (and 25, 30, …): genitive **plural**: пять домо́в, шесть книг.\n\n"
               "Compound numbers follow their LAST word: два́дцать оди́н дом (nom. sg.!)."),
            md("People, money, time",
               "два часа́ / пять часо́в · три рубля́ / де́сять рубле́й · "
               "два челове́ка / пять челове́к (special form!) · два го́да / пять лет.\n\n"
               "Numerals themselves decline (двух, двум, двумя́) — needed at B2+; "
               "at B1 master the nominative counting patterns cold."),
        ],
        "drills": [
            drill("num1", "три ... (книга)", "книги"),
            drill("num2", "пять ... (книга)", "книг"),
            drill("num3", "два ... (час)", "часа"),
            drill("num4", "два́дцать оди́н ... (дом)", "дом"),
            drill("num5", "пять ... (человек)", "человек"),
        ],
    },
    "time-expressions": {
        "content": [
            md("When? — the case depends on the unit",
               "**Days**: в + accusative: в понеде́льник, в сре́ду.\n\n"
               "**Months, years**: в + prepositional: в января́х? нет — в январе́, в 2020 году́.\n\n"
               "**Weeks**: на + prepositional: на э́той неде́ле.\n\n"
               "**Clock time**: в два часа́, в пять часо́в; полови́на второ́го = 1:30."),
            md("Duration and deadlines",
               "**How long**: bare accusative — Я рабо́тал весь день / два часа́.\n\n"
               "**Within/for a deadline**: за + acc.: Я сде́лал э́то за час (in one hour).\n\n"
               "**Planned span**: на + acc.: Я е́ду в Москву́ на неде́лю (for a week).\n\n"
               "**ago / in**: два го́да наза́д · че́рез два го́да."),
        ],
        "drills": [
            drill("tim1", "'on Wednesday': в ... (среда)", "среду"),
            drill("tim2", "'in January': в ... (январь)", "январе"),
            drill("tim3", "'a year ago': год ...", "назад"),
            drill("tim4", "'in (after) a week': ... неде́лю", "через"),
            drill("tim5", "'this week': на э́той ... (неделя)", "неделе"),
        ],
    },
    "conditional": {
        "content": [
            md("бы + past = would",
               "The conditional/subjunctive is just **бы + past tense**:\n\n"
               "Я бы купи́л э́ту маши́ну. (I would buy this car.)\n\n"
               "**Е́сли бы** for unreal conditions — both halves take бы + past: "
               "Е́сли бы я знал, я бы позвони́л. (If I had known, I would have called.)"),
            md("Real vs unreal",
               "Real (likely) conditions use plain е́сли + future: "
               "Е́сли бу́дет дождь, мы оста́немся до́ма.\n\n"
               "бы also softens requests: Я бы хоте́л ко́фе (I'd like a coffee) — "
               "politer than я хочу́."),
        ],
        "drills": [
            drill("con1", "Conditional particle?", "бы"),
            drill("con2", "Е́сли бы я знал, я ... позвони́л", "бы"),
            drill("con3", "Polite: 'I would like...' — Я ... хоте́л...", "бы"),
            drill("con4", "бы combines with which tense?", "past", ["прошедшее"]),
        ],
    },
    "relative-clauses": {
        "content": [
            md("кото́рый — 'which/who/that'",
               "кото́рый declines like an adjective. Its **gender/number** come from "
               "the noun it describes; its **case** comes from its role in the "
               "relative clause:\n\n"
               "Вот кни́га, **кото́рую** я чита́ю. (f. sg. + accusative of чита́ть)\n\n"
               "Вот друг, **кото́рому** я звони́л. (m. sg. + dative of звони́ть)"),
            md("Always a comma",
               "Russian ALWAYS separates the relative clause with a comma — no "
               "exceptions, unlike English: Челове́к, кото́рый живёт ря́дом, — врач.\n\n"
               "With prepositions the preposition moves in front: Дом, **в кото́ром** "
               "я живу́ (the house I live in)."),
        ],
        "drills": [
            drill("rel1", "Вот кни́га, ... я чита́ю (который, f acc)", "которую"),
            drill("rel2", "Вот друг, ... я звони́л (который, m dat)", "которому"),
            drill("rel3", "Дом, в ... я живу́ (который, m pre)", "котором"),
        ],
    },
    "impersonal": {
        "content": [
            md("Sentences without a subject",
               "Russian loves subjectless sentences with a dative experiencer:\n\n"
               "**Мне хо́лодно.** (I'm cold — 'to-me [it is] cold')\n\n"
               "**на́до / ну́жно** + infinitive: Мне на́до рабо́тать. (I have to work.)\n\n"
               "**мо́жно** (one may) / **нельзя́** (one may not): Здесь мо́жно кури́ть? — Нельзя́!"),
            md("хочется and the weather",
               "**Мне хо́чется спать** — a softer, more impersonal 'I feel like sleeping' "
               "than я хочу́.\n\n"
               "Weather and environment are impersonal neuter: Темне́ет (it's getting "
               "dark). Бы́ло хо́лодно. Ста́ло тепло́."),
        ],
        "drills": [
            drill("imp_1", "'I have to go': Мне ... идти́ (надо/можно)", "надо"),
            drill("imp_2", "'one may not': ...", "нельзя"),
            drill("imp_3", "'I'm cold': ... хо́лодно (я → dative)", "мне"),
            drill("imp_4", "'May I?' — ...? ", "можно"),
        ],
    },
    "participles": {
        "content": [
            md("Verbal adjectives of written Russian",
               "**Active present** -ущ/-ющ/-ащ/-ящ: чита́ющий студе́нт = студе́нт, "
               "кото́рый чита́ет.\n\n"
               "**Passive past** -нн/-т: прочи́танная кни́га = кни́га, кото́рую "
               "прочита́ли; закры́тое окно́.\n\n"
               "Participles decline like adjectives and agree with their noun."),
            md("Where you meet them",
               "Participles belong to written/formal Russian — news, contracts, "
               "science. In speech, use кото́рый instead.\n\n"
               "Short passive participles form the passive voice: Кни́га напи́сана "
               "в 1869 году́. Рабо́та сде́лана. Магази́н закры́т."),
        ],
        "drills": [
            drill("par1", "«Студе́нт, кото́рый чита́ет» одним словом: ... студе́нт", "читающий"),
            drill("par2", "Passive past participle of «сделать» (short, f): рабо́та ...", "сделана"),
            drill("par3", "Participles are typical of which register? (spoken/written)", "written",
                  ["письменный"]),
        ],
    },
    "gerunds": {
        "content": [
            md("Doing two things at once",
               "**Imperfective gerund** -я/-а: Чита́я кни́гу, он пил чай. "
               "(While reading, he drank tea.)\n\n"
               "**Perfective gerund** -в: Прочита́в кни́гу, он лёг спать. "
               "(Having finished the book, he went to bed.)\n\n"
               "The gerund's hidden subject MUST be the sentence's subject."),
            md("The dangling gerund trap",
               "Chekhov mocked: «Подъезжа́я к ста́нции, у меня́ слете́ла шля́па» — "
               "'approaching the station, my hat flew off' (the hat was approaching?!). "
               "If the subjects differ, use a clause with когда́ instead."),
        ],
        "drills": [
            drill("ger1", "'While reading' (gerund of читать): ...", "читая"),
            drill("ger2", "'Having read' (gerund of прочитать): ...", "прочитав"),
            drill("ger3", "The gerund's subject must equal the sentence's ... ", "subject",
                  ["подлежащее"]),
        ],
    },
    "reported-speech": {
        "content": [
            md("No tense backshift — ever",
               "Russian keeps the ORIGINAL tense in reported speech:\n\n"
               "Он сказа́л: «Я рабо́таю» → Он сказа́л, что он **рабо́тает**. "
               "(English shifts to 'was working'; Russian doesn't.)\n\n"
               "Он сказа́л, что придёт. (He said he would come — future stays future.)"),
            md("Requests and yes/no questions",
               "**Requests** use что́бы + past: Он попроси́л, что́бы я позвони́л.\n\n"
               "**Yes/no questions** use ...ли: Она́ спроси́ла, до́ма ли я. "
               "(She asked whether I was home.) The questioned word goes first, "
               "ли second."),
        ],
        "drills": [
            drill("rep1", "Он сказал: «Я работаю» → Он сказал, что он ...", "работает"),
            drill("rep2", "Particle for reported yes/no questions?", "ли"),
            drill("rep3", "Он попроси́л, ... я позвони́л (чтобы/что)", "чтобы"),
        ],
    },
    "word-order": {
        "content": [
            md("Free but meaningful",
               "Russian word order is free grammatically but fixed informationally: "
               "known information (theme) first, NEW information (rheme) last.\n\n"
               "Кни́га на столе́. (Where's the book? — ON THE TABLE.)\n\n"
               "На столе́ кни́га. (What's on the table? — A BOOK.)\n\n"
               "The last position carries the stress of novelty — English does this "
               "with 'a' vs 'the'."),
            md("Emphasis and intonation",
               "Fronting creates emphasis: Тебя́ я люблю́ (it's YOU I love). "
               "In questions without a question word, intonation alone rises on "
               "the questioned word: Ты за́втра е́дешь в Москву́? vs Ты за́втра "
               "е́дешь в Москву́? — different questions, same words."),
        ],
        "drills": [
            drill("wo1", "New information goes at the ... of a Russian sentence (start/end)",
                  "end", ["конец"]),
            drill("wo2", "'На столе книга' answers which question: (где книга / что на столе)?",
                  "что на столе"),
        ],
    },
    "complex-syntax": {
        "content": [
            md("Advanced connectors",
               "**несмотря́ на то, что** — despite the fact that\n\n"
               "**поско́льку** — since/inasmuch as (formal причина)\n\n"
               "**ли́бо… ли́бо** — either… or; **ни… ни** — neither… nor (+ не!)\n\n"
               "**как то́лько** — as soon as; **пока́ не** — until: Жди, пока́ я не приду́."),
            md("Punctuation is grammar",
               "Every subordinate clause is comma-separated — что, кото́рый, е́сли, "
               "потому́ что all force commas. Learn the comma with the conjunction "
               "as one unit; Russian editors are merciless about this."),
        ],
        "drills": [
            drill("cx1", "'neither...nor': ни... ...", "ни"),
            drill("cx2", "'as soon as': как ...", "только"),
            drill("cx3", "Does «что» require a comma before it? (да/нет)", "да", ["yes"]),
        ],
    },
    "style-registers": {
        "content": [
            md("Four Russians",
               "**Official** (документы): в соотве́тствии с, назва́нный, осуществля́ть.\n\n"
               "**Academic**: явля́ется, представля́ет собо́й, да́нный.\n\n"
               "**Neutral/journalistic**: the textbook language.\n\n"
               "**Colloquial**: щас (сейчас), чё (что), classic fillers ну, вот, "
               "коро́че, ти́па."),
            md("Switching deliberately",
               "Mixing registers is the #1 marker of a foreigner: writing «осуществи́ть "
               "поку́пку карто́шки» (officialese + colloquial word) sounds absurd. "
               "Match the words to the situation: заявле́ние gets official language, "
               "friends get colloquial, and everything else stays neutral."),
        ],
        "drills": [
            drill("sty1", "«щас» is which register? (colloquial/official)", "colloquial",
                  ["разговорный"]),
            drill("sty2", "«осуществлять» is which register? (colloquial/official)", "official",
                  ["официальный"]),
        ],
    },
    "punctuation": {
        "content": [
            md("Commas are rule-bound, not stylistic",
               "Mandatory commas: before **что, кото́рый, е́сли, потому́ что, когда́, "
               "хотя́** and all subordinators; around participial phrases after their "
               "noun; around вво́дные слова́ (коне́чно, наве́рное, к сча́стью).\n\n"
               "Я ду́маю, что э́то пра́вда. Кни́га, лежа́щая на столе́, моя́."),
            md("Dash and colon",
               "**Dash** replaces the missing 'to be': Москва́ — столи́ца Росси́и. "
               "It also marks direct speech lines (— Приве́т!).\n\n"
               "**Colon** introduces explanations: Я по́нял одно́: на́до учи́ться. "
               "No comma before и in simple lists of two: чай и ко́фе."),
        ],
        "drills": [
            drill("pun1", "Москва́ ... столи́ца Росси́и (which mark?)", "—", ["-", "тире", "dash"]),
            drill("pun2", "Comma before «что»? (да/нет)", "да", ["yes"]),
            drill("pun3", "Comma before «и» in «чай и кофе»? (да/нет)", "нет", ["no"]),
        ],
    },
}

# ---------------------------------------------------------------- C2 tier
C2_TOPICS = [
    topic(
        "aspect-nuance", "Aspectual Nuance & Aktionsart", "Способы действия", "C2", 37,
        "по-, за-, на- shades: посиде́ть, заговори́ть, нае́сться — aspect beyond pairs.",
        content=[
            md("Aktionsart prefixes",
               "**по-** delimitative: посиде́ть — sit for a while.\n\n"
               "**за-** inchoative: заговори́ть — start speaking suddenly.\n\n"
               "**на-…ся** saturative: нае́сться — eat one's fill.\n\n"
               "**пере-** excess: перерабо́тать — overwork. These aren't aspect "
               "partners: they add a flavor of HOW the action unfolds."),
        ],
        drills=[
            drill("an1", "'to sit for a while': ...сидеть", "по", ["по-"]),
            drill("an2", "'to start speaking': ...говорить", "за", ["за-"]),
        ],
        prerequisites=["aspect-mastery"],
    ),
    topic(
        "stylistic-syntax", "Stylistic Syntax & Rhetoric", "Стилистический синтаксис",
        "C2", 38,
        "Inversion, parcellation, ellipsis — the devices of literary Russian.",
        content=[
            md("Literary devices",
               "**Inversion** for poetic emphasis: Печа́льная э́то была́ исто́рия.\n\n"
               "**Parcellation**: breaking a sentence. For effect. Like this — "
               "common in modern prose and ads.\n\n"
               "**Ellipsis** of the verb: Я — домо́й (I'm off home). Татья́на — в лес "
               "(Pushkin). The dash carries the missing motion verb."),
        ],
        drills=[
            drill("ss1", "«Я — домой» omits what kind of verb? (motion/speech)",
                  "motion", ["движения"]),
        ],
        prerequisites=["style-registers", "word-order"],
    ),
    topic(
        "phraseology", "Phraseology & Idiom Mastery", "Фразеология", "C2", 39,
        "Idioms, proverbs, and winged words every educated speaker knows.",
        content=[
            md("Core idioms",
               "**би́ть баклу́ши** — twiddle thumbs · **ве́шать лапшу́ на у́ши** — "
               "pull one's leg (hang noodles on ears) · **не в свое́й таре́лке** — "
               "out of one's element · **де́лать из му́хи слона́** — make a mountain "
               "out of a molehill (an elephant out of a fly).\n\n"
               "Proverbs: Не име́й сто рубле́й, а име́й сто друзе́й. Тише е́дешь — "
               "да́льше бу́дешь."),
        ],
        drills=[
            drill("ph1", "«Делать из мухи ...» (finish the idiom)", "слона"),
            drill("ph2", "«Не имей сто рублей, а имей сто ...»", "друзей"),
        ],
        prerequisites=["style-registers"],
    ),
    topic(
        "false-friends-advanced", "False Friends & Interference", "Ложные друзья",
        "C2", 40,
        "The interference errors that betray even near-native speakers.",
        content=[
            md("Classic traps",
               "**актуа́льный** = topical/relevant, not 'actual' · **аккура́тный** = "
               "neat/careful, not 'accurate' · **симпати́чный** = cute, not "
               "'sympathetic' · **фами́лия** = surname, not 'family' · "
               "**магази́н** = shop · **декре́т** = maternity leave (colloq.), "
               "not 'decree'.\n\n"
               "Calque errors: 'take a shower' → ~~взять душ~~; correct: приня́ть душ."),
        ],
        drills=[
            drill("ff1", "«фамилия» means ...? (surname/family)", "surname", ["фамилия", "last name"]),
            drill("ff2", "'to take a shower': ... душ (взять/принять)", "принять"),
        ],
        prerequisites=["phraseology"],
    ),
]
