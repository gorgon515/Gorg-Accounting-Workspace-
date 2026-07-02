"""Conversation scenarios with scripted dialogue trees.

Each script node: partner line (+translation, hints for the learner) and
`expects` branches keyword-matched against the learner's reply. `next: -1`
ends the dialogue. The same scenarios drive the LLM engine via
persona_prompt when a generative provider is configured.
"""


def node(partner, translation, hints=None, expects=None):
    return {"partner": partner, "translation": translation,
            "hints": hints or [], "expects": expects or []}


def branch(keywords, next_, feedback="", model_answer=""):
    return {"keywords": keywords, "next": next_, "feedback": feedback,
            "model_answer": model_answer}


SCENARIOS = [
    {
        "slug": "cafe-order", "title": "Ordering at a Café", "persona": "waiter",
        "setting": "café", "cefr_level": "A1",
        "description": "Order a drink and something to eat, then ask for the bill.",
        "persona_prompt": "You are a friendly waiter in a Moscow café. Greet the "
                          "customer, take their order, offer additions, bring the "
                          "bill when asked. Menu: coffee, tea, water, borscht, blini.",
        "key_vocabulary": ["кофе", "чай", "вода", "хотеть", "пожалуйста", "спасибо"],
        "script": [
            node("Здра́вствуйте! Что вы хоти́те?", "Hello! What would you like?",
                 hints=["Я хочу́ ко́фе, пожа́луйста", "Да́йте чай, пожа́луйста"],
                 expects=[
                     branch(["кофе", "чай", "воду", "вода"], 1,
                            feedback="Order with «Я хочу́...» or «Да́йте..., пожа́луйста»",
                            model_answer="Я хочу́ ко́фе, пожа́луйста."),
                 ]),
            node("Отли́чно! С молоко́м и́ли без?", "Excellent! With milk or without?",
                 hints=["С молоко́м, пожа́луйста", "Без молока́"],
                 expects=[
                     branch(["с молоком", "без", "молоком", "молока"], 2,
                            model_answer="С молоко́м, пожа́луйста.",
                            feedback="Say «с молоко́м» (with milk) or «без молока́» (without)."),
                 ]),
            node("Хорошо́. Что-нибу́дь ещё?", "OK. Anything else?",
                 hints=["Нет, спаси́бо", "Да, хлеб, пожа́луйста"],
                 expects=[
                     branch(["нет", "спасибо"], 3,
                            model_answer="Нет, спаси́бо."),
                     branch(["да", "хлеб", "блины", "борщ"], 3,
                            model_answer="Да, хлеб, пожа́луйста."),
                 ]),
            node("Пожа́луйста! Прия́тного аппети́та!", "Here you are! Enjoy your meal!",
                 hints=["Спаси́бо! Счёт, пожа́луйста"],
                 expects=[
                     branch(["спасибо", "счет", "счёт"], -1,
                            model_answer="Спаси́бо! Счёт, пожа́луйста."),
                 ]),
        ],
    },
    {
        "slug": "meeting-someone", "title": "Meeting Someone New",
        "persona": "stranger", "setting": "party", "cefr_level": "A1",
        "description": "Introduce yourself, ask names, say where you're from.",
        "persona_prompt": "You are a friendly Russian person at a small gathering, "
                          "meeting the learner for the first time. Exchange names, "
                          "ask where they are from and what they do.",
        "key_vocabulary": ["меня зовут", "очень", "жить", "работать", "как дела"],
        "script": [
            node("Приве́т! Меня́ зову́т Ди́ма. А тебя́ как зову́т?",
                 "Hi! My name is Dima. And what's your name?",
                 hints=["Меня́ зову́т ..."],
                 expects=[branch(["меня зовут", "я"], 1,
                                 model_answer="Меня́ зову́т Марк.",
                                 feedback="Say «Меня́ зову́т» + your name.")]),
            node("О́чень прия́тно! Отку́да ты?", "Very nice to meet you! Where are you from?",
                 hints=["Я из Аме́рики", "Я из А́нглии"],
                 expects=[branch(["я из", "из"], 2,
                                 model_answer="Я из Аме́рики.",
                                 feedback="Say «Я из» + country (genitive).")]),
            node("Как интере́сно! А где ты живёшь сейча́с?",
                 "How interesting! And where do you live now?",
                 hints=["Я живу́ в Москве́"],
                 expects=[branch(["я живу", "живу"], 3,
                                 model_answer="Я живу́ в Москве́.",
                                 feedback="Use «Я живу́ в» + city in the prepositional case.")]),
            node("Здо́рово! Ну, о́чень прия́тно познако́миться. Пока́!",
                 "Great! Well, very nice to meet you. Bye!",
                 hints=["Пока́!", "До свида́ния!"],
                 expects=[branch(["пока", "до свидания", "приятно"], -1,
                                 model_answer="Пока́!")]),
        ],
    },
    {
        "slug": "taxi-ride", "title": "Taking a Taxi", "persona": "taxi driver",
        "setting": "taxi", "cefr_level": "A1",
        "description": "Tell the driver where to go, make small talk, pay.",
        "persona_prompt": "You are a chatty Moscow taxi driver. Ask where to go, "
                          "make small talk about the weather, state the price at the end.",
        "key_vocabulary": ["куда", "пожалуйста", "сколько", "деньги", "спасибо"],
        "script": [
            node("Здра́вствуйте! Куда́ е́дем?", "Hello! Where are we going?",
                 hints=["В центр, пожа́луйста", "На вокза́л, пожа́луйста"],
                 expects=[branch(["центр", "вокзал", "аэропорт", "гостиницу", "в", "на"], 1,
                                 model_answer="В центр, пожа́луйста.",
                                 feedback="Name a destination: «В центр, пожа́луйста».")]),
            node("Хорошо́. Сего́дня хоро́шая пого́да, да?",
                 "OK. Nice weather today, right?",
                 hints=["Да, о́чень хоро́шая!", "Нет, хо́лодно"],
                 expects=[branch(["да", "нет", "хорошая", "холодно"], 2,
                                 model_answer="Да, о́чень хоро́шая!")]),
            node("Прие́хали! С вас три́ста рубле́й.",
                 "We've arrived! That'll be 300 rubles.",
                 hints=["Пожа́луйста. Спаси́бо большо́е!"],
                 expects=[branch(["пожалуйста", "спасибо", "вот"], -1,
                                 model_answer="Пожа́луйста. Спаси́бо большо́е!")]),
        ],
    },
    {
        "slug": "hotel-checkin", "title": "Hotel Check-in", "persona": "receptionist",
        "setting": "hotel", "cefr_level": "A2",
        "description": "Check in, give your name, ask about breakfast and Wi-Fi.",
        "persona_prompt": "You are a professional hotel receptionist in "
                          "St. Petersburg. Check the learner in: ask for their name "
                          "and passport, explain breakfast hours and Wi-Fi.",
        "key_vocabulary": ["меня зовут", "у меня", "есть", "сколько", "утро"],
        "script": [
            node("До́брый ве́чер! Вы брони́ровали но́мер?",
                 "Good evening! Did you book a room?",
                 hints=["Да, брони́ровал. Меня́ зову́т ..."],
                 expects=[branch(["да", "бронировал", "меня зовут"], 1,
                                 model_answer="Да, меня́ зову́т Марк Сми́т.",
                                 feedback="Confirm and give your name.")]),
            node("Отли́чно, ваш па́спорт, пожа́луйста.", "Excellent, your passport please.",
                 hints=["Вот, пожа́луйста"],
                 expects=[branch(["вот", "пожалуйста", "паспорт"], 2,
                                 model_answer="Вот, пожа́луйста.")]),
            node("Спаси́бо. За́втрак с семи́ до десяти́. Ваш но́мер — три́ста пять.",
                 "Thank you. Breakfast is from 7 to 10. Your room is 305.",
                 hints=["А есть Wi-Fi?", "Спаси́бо большо́е!"],
                 expects=[branch(["wi-fi", "вай", "интернет"], 3,
                                 model_answer="А есть Wi-Fi?"),
                          branch(["спасибо"], -1, model_answer="Спаси́бо большо́е!")]),
            node("Да, коне́чно, Wi-Fi беспла́тный. Хоро́шего ве́чера!",
                 "Yes of course, the Wi-Fi is free. Have a good evening!",
                 hints=["Спаси́бо, до свида́ния!"],
                 expects=[branch(["спасибо", "до свидания"], -1,
                                 model_answer="Спаси́бо, до свида́ния!")]),
        ],
    },
]
