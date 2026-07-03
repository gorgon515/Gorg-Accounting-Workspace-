"""Graded reading library: hand-authored texts with sentence-aligned
translations and stress marks. Grows via content packs; the reader UI and
API are content-agnostic."""


def s(ru: str, en: str) -> dict:
    return {"ru": ru, "en": en, "audio_url": None}


TEXTS = [
    {
        "slug": "moya-semya", "title": "Моя́ семья́", "title_translation": "My Family",
        "kind": "story", "cefr_level": "A1", "topic": "family",
        "summary": "A simple first-person introduction to a family.",
        "sentences": [
            s("Меня́ зову́т А́нна.", "My name is Anna."),
            s("Э́то моя́ семья́.", "This is my family."),
            s("Мой па́па — врач.", "My dad is a doctor."),
            s("Он рабо́тает в больни́це.", "He works at a hospital."),
            s("Моя́ ма́ма — учи́тель.", "My mom is a teacher."),
            s("Она́ рабо́тает в шко́ле.", "She works at a school."),
            s("У меня́ есть брат.", "I have a brother."),
            s("Его́ зову́т Ива́н.", "His name is Ivan."),
            s("Он студе́нт.", "He is a student."),
            s("У нас до́ма живёт кот Ба́рсик.", "A cat named Barsik lives in our home."),
            s("Я о́чень люблю́ мою́ семью́.", "I love my family very much."),
        ],
    },
    {
        "slug": "v-kafe", "title": "В кафе́", "title_translation": "At the Café",
        "kind": "dialogue", "cefr_level": "A1", "topic": "food",
        "summary": "Ordering breakfast — the essential survival dialogue.",
        "sentences": [
            s("— До́брое у́тро! Что вы хоти́те?", "— Good morning! What would you like?"),
            s("— Да́йте, пожа́луйста, ко́фе с молоко́м.", "— Please give me a coffee with milk."),
            s("— Хорошо́. Что-нибу́дь ещё?", "— OK. Anything else?"),
            s("— Да, ка́шу и хлеб с сы́ром.", "— Yes, porridge and bread with cheese."),
            s("— У нас о́чень вку́сные блины́. Хоти́те?", "— Our blini are very tasty. Would you like some?"),
            s("— Нет, спаси́бо. Мо́жет быть, за́втра.", "— No, thank you. Maybe tomorrow."),
            s("— Ваш ко́фе, пожа́луйста.", "— Your coffee, please."),
            s("— Спаси́бо! Ско́лько э́то сто́ит?", "— Thank you! How much is it?"),
            s("— Три́ста рубле́й.", "— Three hundred rubles."),
            s("— Вот, пожа́луйста. До свида́ния!", "— Here you are. Goodbye!"),
        ],
    },
    {
        "slug": "repka", "title": "Ре́пка", "title_translation": "The Turnip",
        "kind": "fairy_tale", "cefr_level": "A1", "topic": "nature",
        "summary": "The classic Russian folk tale every child knows — adapted "
                   "and shortened for beginners.",
        "sentences": [
            s("Посади́л дед ре́пку.", "Grandfather planted a turnip."),
            s("Вы́росла ре́пка больша́я-пребольша́я.", "The turnip grew very, very big."),
            s("Тя́нет дед ре́пку — не мо́жет.", "Grandfather pulls the turnip — he can't."),
            s("Позва́л дед ба́бку.", "Grandfather called grandmother."),
            s("Ба́бка за де́дку, де́дка за ре́пку — не мо́гут.", "Grandmother holds grandfather, grandfather holds the turnip — they can't."),
            s("Позва́ли вну́чку, соба́ку Жу́чку и ко́шку.", "They called the granddaughter, the dog Zhuchka, and the cat."),
            s("Тя́нут-потя́нут — не мо́гут!", "They pull and pull — they can't!"),
            s("Позва́ла ко́шка мы́шку.", "The cat called the mouse."),
            s("Тя́нут-потя́нут — и вы́тянули ре́пку!", "They pull and pull — and pulled out the turnip!"),
            s("Вот так ма́ленькая мы́шка помогла́ всем.", "And that is how the little mouse helped everyone."),
        ],
    },
    {
        "slug": "moy-den", "title": "Мой день", "title_translation": "My Day",
        "kind": "story", "cefr_level": "A2", "topic": "daily",
        "summary": "A typical weekday, told with the daily-routine verbs.",
        "sentences": [
            s("Я встаю́ в семь часо́в утра́.", "I get up at seven in the morning."),
            s("Снача́ла я умыва́юсь и одева́юсь.", "First I wash my face and get dressed."),
            s("На за́втрак я ем ка́шу и пью ко́фе.", "For breakfast I eat porridge and drink coffee."),
            s("В во́семь я е́ду на рабо́ту на метро́.", "At eight I go to work by metro."),
            s("Я рабо́таю в о́фисе в це́нтре го́рода.", "I work in an office in the city center."),
            s("В час дня мы с колле́гами обе́даем.", "At one o'clock my colleagues and I have lunch."),
            s("По́сле рабо́ты я иногда́ гуля́ю в па́рке.", "After work I sometimes walk in the park."),
            s("Ве́чером я гото́влю у́жин и смотрю́ фильм.", "In the evening I cook dinner and watch a film."),
            s("Пе́ред сном я немно́го чита́ю.", "Before bed I read a little."),
            s("Я ложу́сь спать в оди́ннадцать часо́в.", "I go to bed at eleven o'clock."),
        ],
    },
    {
        "slug": "pogoda-v-rossii", "title": "Пого́да в Росси́и",
        "title_translation": "Weather in Russia",
        "kind": "article", "cefr_level": "A2", "topic": "nature",
        "summary": "Seasons and weather across the world's largest country.",
        "sentences": [
            s("Росси́я — о́чень больша́я страна́.", "Russia is a very big country."),
            s("Здесь есть четы́ре вре́мени го́да.", "There are four seasons here."),
            s("Зима́ в Росси́и дли́нная и холо́дная.", "Winter in Russia is long and cold."),
            s("В Сиби́ри зимо́й быва́ет ми́нус со́рок гра́дусов.", "In Siberia it can be minus forty degrees in winter."),
            s("Весно́й снег та́ет, и появля́ются пе́рвые цветы́.", "In spring the snow melts and the first flowers appear."),
            s("Ле́то тёплое, а иногда́ жа́ркое.", "Summer is warm, and sometimes hot."),
            s("Ле́том мно́гие лю́ди е́дут на да́чу.", "In summer many people go to their dacha."),
            s("О́сенью ча́сто идёт дождь.", "In autumn it often rains."),
            s("Но в сентябре́ быва́ет «ба́бье ле́то» — тёплые со́лнечные дни.", "But in September there is an 'Indian summer' — warm sunny days."),
            s("Ру́сские говоря́т: у приро́ды нет плохо́й пого́ды.", "Russians say: nature has no bad weather."),
        ],
    },
    {
        "slug": "razgovor-s-taksistom", "title": "Разгово́р с такси́стом",
        "title_translation": "Conversation with a Taxi Driver",
        "kind": "dialogue", "cefr_level": "A2", "topic": "city",
        "summary": "Small talk in a Moscow taxi — where are you from, what do "
                   "you do, and of course the traffic.",
        "sentences": [
            s("— Здра́вствуйте! Куда́ е́дем?", "— Hello! Where are we going?"),
            s("— На Кра́сную пло́щадь, пожа́луйста.", "— To Red Square, please."),
            s("— Хорошо́. А вы отку́да? У вас интере́сный акце́нт.", "— OK. Where are you from? You have an interesting accent."),
            s("— Я из Аме́рики. Я учу́ ру́сский язы́к.", "— I'm from America. I'm learning Russian."),
            s("— Молоде́ц! Ру́сский — тру́дный язы́к.", "— Well done! Russian is a difficult language."),
            s("— Да, но о́чень краси́вый. Я учу́сь ка́ждый день.", "— Yes, but very beautiful. I study every day."),
            s("— И давно́ вы в Москве́?", "— Have you been in Moscow long?"),
            s("— Две неде́ли. Мне о́чень нра́вится го́род.", "— Two weeks. I really like the city."),
            s("— То́лько не нра́вятся про́бки, да?", "— Except the traffic jams, right?"),
            s("— Да! Про́бки — э́то интернациона́льная пробле́ма!", "— Yes! Traffic jams are an international problem!"),
        ],
    },
    {
        "slug": "pismo-drugu", "title": "Письмо́ дру́гу", "title_translation": "A Letter to a Friend",
        "kind": "story", "cefr_level": "B1", "topic": "travel",
        "summary": "A letter home after a month in St. Petersburg — impressions, "
                   "small victories, and language struggles.",
        "sentences": [
            s("Дорого́й Том!", "Dear Tom!"),
            s("Пишу́ тебе́ из Санкт-Петербу́рга, где я живу́ уже́ це́лый ме́сяц.", "I'm writing to you from Saint Petersburg, where I've been living for a whole month now."),
            s("Э́тот го́род невозмо́жно не полюби́ть.", "It is impossible not to fall in love with this city."),
            s("Ка́ждый день я хожу́ пешко́м вдоль кана́лов и мосто́в.", "Every day I walk along the canals and bridges."),
            s("Вчера́ я наконе́ц побыва́л в Эрмита́же.", "Yesterday I finally visited the Hermitage."),
            s("Говоря́т, е́сли смотре́ть на ка́ждую карти́ну мину́ту, ну́жно во́семь лет!", "They say that if you look at each painting for a minute, you would need eight years!"),
            s("Мой ру́сский стано́вится лу́чше, хотя́ падежи́ всё ещё тру́дные.", "My Russian is getting better, although the cases are still difficult."),
            s("На про́шлой неде́ле я впервы́е заказа́л у́жин по-ру́сски без оши́бок.", "Last week, for the first time, I ordered dinner in Russian without mistakes."),
            s("Официа́нт да́же не перешёл на англи́йский — э́то была́ настоя́щая побе́да!", "The waiter didn't even switch to English — it was a real victory!"),
            s("Приезжа́й в го́сти: бе́лые но́чи начина́ются в ма́е.", "Come visit: the white nights begin in May."),
            s("Обнима́ю, твой Марк.", "Hugs, your Mark."),
        ],
    },
    {
        "slug": "novosti-tekhnologiy", "title": "Но́вости техноло́гий",
        "title_translation": "Technology News",
        "kind": "news", "cefr_level": "B1", "topic": "tech",
        "summary": "A short news-style piece about remote work — journalistic "
                   "register with everyday tech vocabulary.",
        "sentences": [
            s("Всё бо́льше люде́й в Росси́и рабо́тают из до́ма.", "More and more people in Russia work from home."),
            s("По да́нным опро́сов, ка́ждый пя́тый сотру́дник хоте́л бы рабо́тать удалённо постоя́нно.", "According to surveys, every fifth employee would like to work remotely permanently."),
            s("Компа́нии экономя́т на офиса́х, а лю́ди — на доро́ге.", "Companies save on offices, and people save on commuting."),
            s("Одна́ко психо́логи предупрежда́ют: до́ма тру́дно отдели́ть рабо́ту от ли́чной жи́зни.", "However, psychologists warn: at home it is hard to separate work from personal life."),
            s("«Гла́вное — режи́м», — говори́т психо́лог Еле́на Соколо́ва.", "'The main thing is a routine,' says psychologist Elena Sokolova."),
            s("Она́ сове́тует начина́ть день в одно́ и то же вре́мя.", "She advises starting the day at the same time."),
            s("Та́кже ва́жно де́лать переры́вы и гуля́ть хотя́ бы полчаса́.", "It is also important to take breaks and walk at least half an hour."),
            s("Техноло́гии меня́ют не то́лько рабо́ту, но и города́.", "Technology is changing not only work but also cities."),
            s("Вопро́с в том, гото́вы ли мы к э́тим измене́ниям.", "The question is whether we are ready for these changes."),
        ],
    },
]
