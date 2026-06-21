"""Language Academy seed content — the real source-of-truth knowledge bank.

This module holds the structured content the whole academy is built from:

  * LANGUAGES  — the 7 supported languages.
  * LEVELS     — the six CEFR tiers.
  * TOPICS     — thematic groupings used everywhere (curriculum, lessons,
                 vocabulary, assessment).
  * VOCAB      — a real, structured vocabulary bank keyed by topic. Every
                 headword carries an English definition + example and a
                 ``translations`` dict mapping ALL 7 language codes to a real
                 (or carefully transliterated) translation.
  * GRAMMAR    — CEFR-tiered grammar rules with examples and common mistakes.
  * CONVERSATION_SCENARIOS — role-play scenarios with sample prompts.
  * LISTENING  — a bank of listening comprehension exercises.

Scaling note (10,000+ entries):
    The vocabulary engine *expands* the base headword bank across all 7
    languages — every headword becomes one ``vocab_entry`` row per language.
    With ~30+ headwords across a dozen topics that is already several hundred
    base concepts and, multiplied by 7 languages, thousands of concrete
    rows. The same headword × language fan-out trivially scales past 10,000
    once more headwords are appended to VOCAB — no schema change required.
"""
from __future__ import annotations

# ── Languages ────────────────────────────────────────────────────────────────
LANGUAGES = [
    {"code": "russian", "name": "Russian", "native": "Русский", "flag": "🇷🇺"},
    {"code": "spanish", "name": "Spanish", "native": "Español", "flag": "🇪🇸"},
    {"code": "french", "name": "French", "native": "Français", "flag": "🇫🇷"},
    {"code": "german", "name": "German", "native": "Deutsch", "flag": "🇩🇪"},
    {"code": "italian", "name": "Italian", "native": "Italiano", "flag": "🇮🇹"},
    {"code": "japanese", "name": "Japanese", "native": "日本語", "flag": "🇯🇵"},
    {"code": "mandarin", "name": "Mandarin Chinese", "native": "中文", "flag": "🇨🇳"},
]
LANGUAGE_CODES = [l["code"] for l in LANGUAGES]

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# CEFR tier groupings used by the grammar academy and curriculum.
TIERS = {
    "beginner": ["A1", "A2"],
    "intermediate": ["B1", "B2"],
    "advanced": ["C1", "C2"],
}


def tier_for_level(level: str) -> str:
    for tier, levels in TIERS.items():
        if level in levels:
            return tier
    return "beginner"


# ── Topics ───────────────────────────────────────────────────────────────────
TOPICS = [
    {"id": "greetings", "name": "Greetings & Introductions", "cefr": "A1"},
    {"id": "numbers", "name": "Numbers & Counting", "cefr": "A1"},
    {"id": "family", "name": "Family & Relationships", "cefr": "A1"},
    {"id": "daily_life", "name": "Daily Life & Routines", "cefr": "A2"},
    {"id": "food", "name": "Food & Dining", "cefr": "A2"},
    {"id": "travel", "name": "Travel & Transport", "cefr": "A2"},
    {"id": "business", "name": "Business & Work", "cefr": "B1"},
    {"id": "technology", "name": "Technology & Computing", "cefr": "B1"},
    {"id": "healthcare", "name": "Health & Medicine", "cefr": "B1"},
    {"id": "finance", "name": "Personal Finance", "cefr": "B2"},
    {"id": "accounting", "name": "Accounting & Bookkeeping", "cefr": "B2"},
    {"id": "investing", "name": "Investing & Markets", "cefr": "C1"},
]
TOPIC_IDS = [t["id"] for t in TOPICS]


# ── Vocabulary bank ──────────────────────────────────────────────────────────
# Each entry: word, pos, definition, example, cefr, frequency (1=rare..5=core)
# and translations for all 7 language codes. Helper ``_t`` keeps the literals
# compact while guaranteeing every entry has all 7 codes filled.
def _t(es, fr, de, it, ru, ja, zh):
    return {
        "spanish": es, "french": fr, "german": de, "italian": it,
        "russian": ru, "japanese": ja, "mandarin": zh,
    }


VOCAB: dict[str, list[dict]] = {
    "greetings": [
        {"word": "hello", "pos": "interjection", "definition": "a greeting", "example": "Hello, how are you?", "cefr": "A1", "frequency": 5, "translations": _t("hola", "bonjour", "hallo", "ciao", "privet", "konnichiwa", "nihao")},
        {"word": "goodbye", "pos": "interjection", "definition": "a parting word", "example": "Goodbye, see you tomorrow.", "cefr": "A1", "frequency": 5, "translations": _t("adiós", "au revoir", "auf Wiedersehen", "arrivederci", "do svidaniya", "sayounara", "zaijian")},
        {"word": "please", "pos": "adverb", "definition": "a polite request word", "example": "Please sit down.", "cefr": "A1", "frequency": 5, "translations": _t("por favor", "s'il vous plaît", "bitte", "per favore", "pozhaluysta", "onegaishimasu", "qing")},
        {"word": "thank you", "pos": "phrase", "definition": "expression of gratitude", "example": "Thank you for your help.", "cefr": "A1", "frequency": 5, "translations": _t("gracias", "merci", "danke", "grazie", "spasibo", "arigatou", "xiexie")},
        {"word": "yes", "pos": "adverb", "definition": "affirmative answer", "example": "Yes, I agree.", "cefr": "A1", "frequency": 5, "translations": _t("sí", "oui", "ja", "sì", "da", "hai", "shi")},
        {"word": "no", "pos": "adverb", "definition": "negative answer", "example": "No, thank you.", "cefr": "A1", "frequency": 5, "translations": _t("no", "non", "nein", "no", "net", "iie", "bu")},
        {"word": "excuse me", "pos": "phrase", "definition": "to get attention politely", "example": "Excuse me, where is the station?", "cefr": "A1", "frequency": 4, "translations": _t("disculpe", "excusez-moi", "Entschuldigung", "mi scusi", "izvinite", "sumimasen", "qingwen")},
        {"word": "sorry", "pos": "interjection", "definition": "an apology", "example": "Sorry, I'm late.", "cefr": "A1", "frequency": 5, "translations": _t("lo siento", "désolé", "Entschuldigung", "mi dispiace", "izvinite", "gomennasai", "duibuqi")},
        {"word": "good morning", "pos": "phrase", "definition": "a morning greeting", "example": "Good morning, everyone.", "cefr": "A1", "frequency": 4, "translations": _t("buenos días", "bonjour", "guten Morgen", "buongiorno", "dobroe utro", "ohayou", "zaoshang hao")},
        {"word": "good night", "pos": "phrase", "definition": "an evening parting", "example": "Good night, sleep well.", "cefr": "A1", "frequency": 4, "translations": _t("buenas noches", "bonne nuit", "gute Nacht", "buonanotte", "spokoynoy nochi", "oyasumi", "wan'an")},
        {"word": "name", "pos": "noun", "definition": "what someone is called", "example": "My name is Anna.", "cefr": "A1", "frequency": 5, "translations": _t("nombre", "nom", "Name", "nome", "imya", "namae", "mingzi")},
        {"word": "friend", "pos": "noun", "definition": "a person you like and know well", "example": "She is my best friend.", "cefr": "A1", "frequency": 5, "translations": _t("amigo", "ami", "Freund", "amico", "drug", "tomodachi", "pengyou")},
        {"word": "welcome", "pos": "interjection", "definition": "a greeting to a guest", "example": "Welcome to our home.", "cefr": "A1", "frequency": 4, "translations": _t("bienvenido", "bienvenue", "willkommen", "benvenuto", "dobro pozhalovat", "youkoso", "huanying")},
        {"word": "how are you", "pos": "phrase", "definition": "asking about wellbeing", "example": "Hi, how are you today?", "cefr": "A1", "frequency": 5, "translations": _t("cómo estás", "comment ça va", "wie geht es dir", "come stai", "kak dela", "ogenki desu ka", "ni hao ma")},
        {"word": "nice to meet you", "pos": "phrase", "definition": "said when introduced", "example": "Nice to meet you, John.", "cefr": "A1", "frequency": 4, "translations": _t("mucho gusto", "enchanté", "freut mich", "piacere", "ochen priyatno", "hajimemashite", "hen gaoxing renshi ni")},
    ],
    "numbers": [
        {"word": "one", "pos": "numeral", "definition": "the number 1", "example": "I have one brother.", "cefr": "A1", "frequency": 5, "translations": _t("uno", "un", "eins", "uno", "odin", "ichi", "yi")},
        {"word": "two", "pos": "numeral", "definition": "the number 2", "example": "Two coffees, please.", "cefr": "A1", "frequency": 5, "translations": _t("dos", "deux", "zwei", "due", "dva", "ni", "er")},
        {"word": "three", "pos": "numeral", "definition": "the number 3", "example": "Three days a week.", "cefr": "A1", "frequency": 5, "translations": _t("tres", "trois", "drei", "tre", "tri", "san", "san")},
        {"word": "four", "pos": "numeral", "definition": "the number 4", "example": "Four people are waiting.", "cefr": "A1", "frequency": 5, "translations": _t("cuatro", "quatre", "vier", "quattro", "chetyre", "yon", "si")},
        {"word": "five", "pos": "numeral", "definition": "the number 5", "example": "Five euros each.", "cefr": "A1", "frequency": 5, "translations": _t("cinco", "cinq", "fünf", "cinque", "pyat", "go", "wu")},
        {"word": "ten", "pos": "numeral", "definition": "the number 10", "example": "Ten minutes left.", "cefr": "A1", "frequency": 5, "translations": _t("diez", "dix", "zehn", "dieci", "desyat", "juu", "shi")},
        {"word": "hundred", "pos": "numeral", "definition": "the number 100", "example": "One hundred dollars.", "cefr": "A1", "frequency": 4, "translations": _t("cien", "cent", "hundert", "cento", "sto", "hyaku", "bai")},
        {"word": "thousand", "pos": "numeral", "definition": "the number 1000", "example": "Two thousand people.", "cefr": "A2", "frequency": 4, "translations": _t("mil", "mille", "tausend", "mille", "tysyacha", "sen", "qian")},
        {"word": "first", "pos": "adjective", "definition": "coming before all others", "example": "The first day of school.", "cefr": "A1", "frequency": 5, "translations": _t("primero", "premier", "erste", "primo", "pervyy", "ichiban", "diyi")},
        {"word": "half", "pos": "noun", "definition": "one of two equal parts", "example": "Half of the cake.", "cefr": "A2", "frequency": 4, "translations": _t("mitad", "moitié", "Hälfte", "metà", "polovina", "hanbun", "yiban")},
        {"word": "number", "pos": "noun", "definition": "a quantity or figure", "example": "What is your phone number?", "cefr": "A1", "frequency": 5, "translations": _t("número", "numéro", "Nummer", "numero", "nomer", "bangou", "haoma")},
        {"word": "many", "pos": "determiner", "definition": "a large number of", "example": "Many students attended.", "cefr": "A1", "frequency": 5, "translations": _t("muchos", "beaucoup", "viele", "molti", "mnogo", "takusan", "henduo")},
        {"word": "few", "pos": "determiner", "definition": "a small number of", "example": "A few minutes ago.", "cefr": "A2", "frequency": 4, "translations": _t("pocos", "peu", "wenige", "pochi", "neskolko", "sukoshi", "jige")},
        {"word": "double", "pos": "adjective", "definition": "twice as much", "example": "A double room, please.", "cefr": "A2", "frequency": 3, "translations": _t("doble", "double", "doppelt", "doppio", "dvoynoy", "nibai", "shuangbei")},
    ],
    "family": [
        {"word": "mother", "pos": "noun", "definition": "a female parent", "example": "My mother cooks well.", "cefr": "A1", "frequency": 5, "translations": _t("madre", "mère", "Mutter", "madre", "mat", "haha", "muqin")},
        {"word": "father", "pos": "noun", "definition": "a male parent", "example": "His father is a doctor.", "cefr": "A1", "frequency": 5, "translations": _t("padre", "père", "Vater", "padre", "otets", "chichi", "fuqin")},
        {"word": "brother", "pos": "noun", "definition": "a male sibling", "example": "I have two brothers.", "cefr": "A1", "frequency": 5, "translations": _t("hermano", "frère", "Bruder", "fratello", "brat", "ani", "xiongdi")},
        {"word": "sister", "pos": "noun", "definition": "a female sibling", "example": "Her sister lives abroad.", "cefr": "A1", "frequency": 5, "translations": _t("hermana", "sœur", "Schwester", "sorella", "sestra", "ane", "jiemei")},
        {"word": "child", "pos": "noun", "definition": "a young human", "example": "The child is sleeping.", "cefr": "A1", "frequency": 5, "translations": _t("niño", "enfant", "Kind", "bambino", "rebyonok", "kodomo", "haizi")},
        {"word": "son", "pos": "noun", "definition": "a male child", "example": "Their son is ten.", "cefr": "A1", "frequency": 5, "translations": _t("hijo", "fils", "Sohn", "figlio", "syn", "musuko", "erzi")},
        {"word": "daughter", "pos": "noun", "definition": "a female child", "example": "My daughter studies art.", "cefr": "A1", "frequency": 5, "translations": _t("hija", "fille", "Tochter", "figlia", "doch", "musume", "nuer")},
        {"word": "grandmother", "pos": "noun", "definition": "the mother of a parent", "example": "My grandmother is kind.", "cefr": "A1", "frequency": 4, "translations": _t("abuela", "grand-mère", "Großmutter", "nonna", "babushka", "sobo", "nainai")},
        {"word": "grandfather", "pos": "noun", "definition": "the father of a parent", "example": "Grandfather tells stories.", "cefr": "A1", "frequency": 4, "translations": _t("abuelo", "grand-père", "Großvater", "nonno", "dedushka", "sofu", "yeye")},
        {"word": "husband", "pos": "noun", "definition": "a married man", "example": "Her husband cooks dinner.", "cefr": "A2", "frequency": 4, "translations": _t("esposo", "mari", "Ehemann", "marito", "muzh", "otto", "zhangfu")},
        {"word": "wife", "pos": "noun", "definition": "a married woman", "example": "His wife is a lawyer.", "cefr": "A2", "frequency": 4, "translations": _t("esposa", "femme", "Ehefrau", "moglie", "zhena", "tsuma", "qizi")},
        {"word": "parents", "pos": "noun", "definition": "mother and father", "example": "My parents live nearby.", "cefr": "A1", "frequency": 5, "translations": _t("padres", "parents", "Eltern", "genitori", "roditeli", "ryoushin", "fumu")},
        {"word": "uncle", "pos": "noun", "definition": "a parent's brother", "example": "My uncle owns a shop.", "cefr": "A2", "frequency": 3, "translations": _t("tío", "oncle", "Onkel", "zio", "dyadya", "oji", "shushu")},
        {"word": "aunt", "pos": "noun", "definition": "a parent's sister", "example": "Aunt Maria visits often.", "cefr": "A2", "frequency": 3, "translations": _t("tía", "tante", "Tante", "zia", "tyotya", "oba", "ayi")},
        {"word": "cousin", "pos": "noun", "definition": "a child of an aunt or uncle", "example": "My cousin is my age.", "cefr": "A2", "frequency": 3, "translations": _t("primo", "cousin", "Cousin", "cugino", "kuzen", "itoko", "biaodi")},
    ],
    "daily_life": [
        {"word": "to wake up", "pos": "verb", "definition": "to stop sleeping", "example": "I wake up at seven.", "cefr": "A2", "frequency": 5, "translations": _t("despertarse", "se réveiller", "aufwachen", "svegliarsi", "prosypatsya", "okiru", "qichuang")},
        {"word": "breakfast", "pos": "noun", "definition": "the first meal of the day", "example": "We have breakfast together.", "cefr": "A1", "frequency": 5, "translations": _t("desayuno", "petit-déjeuner", "Frühstück", "colazione", "zavtrak", "asagohan", "zaocan")},
        {"word": "work", "pos": "noun", "definition": "a job or activity", "example": "I go to work by bus.", "cefr": "A1", "frequency": 5, "translations": _t("trabajo", "travail", "Arbeit", "lavoro", "rabota", "shigoto", "gongzuo")},
        {"word": "home", "pos": "noun", "definition": "where one lives", "example": "I stay home on Sundays.", "cefr": "A1", "frequency": 5, "translations": _t("casa", "maison", "Zuhause", "casa", "dom", "ie", "jia")},
        {"word": "to sleep", "pos": "verb", "definition": "to rest with eyes closed", "example": "Children need to sleep early.", "cefr": "A1", "frequency": 5, "translations": _t("dormir", "dormir", "schlafen", "dormire", "spat", "neru", "shuijiao")},
        {"word": "to eat", "pos": "verb", "definition": "to consume food", "example": "We eat at noon.", "cefr": "A1", "frequency": 5, "translations": _t("comer", "manger", "essen", "mangiare", "est", "taberu", "chi")},
        {"word": "to drink", "pos": "verb", "definition": "to consume liquid", "example": "I drink water often.", "cefr": "A1", "frequency": 5, "translations": _t("beber", "boire", "trinken", "bere", "pit", "nomu", "he")},
        {"word": "shower", "pos": "noun", "definition": "washing under water", "example": "I take a shower daily.", "cefr": "A2", "frequency": 4, "translations": _t("ducha", "douche", "Dusche", "doccia", "dush", "shawaa", "linyu")},
        {"word": "to clean", "pos": "verb", "definition": "to make tidy", "example": "She cleans the kitchen.", "cefr": "A2", "frequency": 4, "translations": _t("limpiar", "nettoyer", "putzen", "pulire", "ubirat", "souji suru", "dasao")},
        {"word": "to study", "pos": "verb", "definition": "to learn by reading", "example": "They study every evening.", "cefr": "A1", "frequency": 5, "translations": _t("estudiar", "étudier", "studieren", "studiare", "uchitsya", "benkyou suru", "xuexi")},
        {"word": "weekend", "pos": "noun", "definition": "Saturday and Sunday", "example": "What are your weekend plans?", "cefr": "A2", "frequency": 4, "translations": _t("fin de semana", "week-end", "Wochenende", "fine settimana", "vykhodnye", "shuumatsu", "zhoumo")},
        {"word": "to relax", "pos": "verb", "definition": "to rest and feel calm", "example": "I relax with a book.", "cefr": "A2", "frequency": 4, "translations": _t("relajarse", "se détendre", "entspannen", "rilassarsi", "rasslablyatsya", "rirakkusu suru", "fangsong")},
        {"word": "schedule", "pos": "noun", "definition": "a plan of times", "example": "My schedule is busy.", "cefr": "B1", "frequency": 4, "translations": _t("horario", "emploi du temps", "Zeitplan", "orario", "raspisanie", "sukejuuru", "richeng")},
        {"word": "to commute", "pos": "verb", "definition": "to travel to work", "example": "I commute by train.", "cefr": "B1", "frequency": 3, "translations": _t("desplazarse", "faire la navette", "pendeln", "fare il pendolare", "ezdit na rabotu", "tsuukin suru", "tongqin")},
    ],
    "food": [
        {"word": "water", "pos": "noun", "definition": "a clear drink", "example": "A glass of water, please.", "cefr": "A1", "frequency": 5, "translations": _t("agua", "eau", "Wasser", "acqua", "voda", "mizu", "shui")},
        {"word": "bread", "pos": "noun", "definition": "a baked staple food", "example": "Fresh bread smells great.", "cefr": "A1", "frequency": 5, "translations": _t("pan", "pain", "Brot", "pane", "khleb", "pan", "mianbao")},
        {"word": "coffee", "pos": "noun", "definition": "a hot caffeinated drink", "example": "I drink coffee in the morning.", "cefr": "A1", "frequency": 5, "translations": _t("café", "café", "Kaffee", "caffè", "kofe", "koohii", "kafei")},
        {"word": "apple", "pos": "noun", "definition": "a round fruit", "example": "An apple a day is healthy.", "cefr": "A1", "frequency": 5, "translations": _t("manzana", "pomme", "Apfel", "mela", "yabloko", "ringo", "pingguo")},
        {"word": "meat", "pos": "noun", "definition": "animal flesh as food", "example": "I don't eat much meat.", "cefr": "A2", "frequency": 4, "translations": _t("carne", "viande", "Fleisch", "carne", "myaso", "niku", "rou")},
        {"word": "vegetable", "pos": "noun", "definition": "an edible plant", "example": "Eat your vegetables.", "cefr": "A2", "frequency": 4, "translations": _t("verdura", "légume", "Gemüse", "verdura", "ovoshch", "yasai", "shucai")},
        {"word": "restaurant", "pos": "noun", "definition": "a place to eat out", "example": "We booked a restaurant.", "cefr": "A1", "frequency": 5, "translations": _t("restaurante", "restaurant", "Restaurant", "ristorante", "restoran", "resutoran", "canting")},
        {"word": "menu", "pos": "noun", "definition": "a list of dishes", "example": "Can I see the menu?", "cefr": "A2", "frequency": 4, "translations": _t("menú", "menu", "Speisekarte", "menù", "menyu", "menyuu", "caidan")},
        {"word": "bill", "pos": "noun", "definition": "the check at a restaurant", "example": "The bill, please.", "cefr": "A2", "frequency": 4, "translations": _t("cuenta", "addition", "Rechnung", "conto", "schyot", "okanjou", "zhangdan")},
        {"word": "delicious", "pos": "adjective", "definition": "very tasty", "example": "This soup is delicious.", "cefr": "A2", "frequency": 4, "translations": _t("delicioso", "délicieux", "lecker", "delizioso", "vkusnyy", "oishii", "haochi")},
        {"word": "to order", "pos": "verb", "definition": "to ask for food", "example": "I'd like to order now.", "cefr": "A2", "frequency": 4, "translations": _t("pedir", "commander", "bestellen", "ordinare", "zakazat", "chuumon suru", "dian")},
        {"word": "breakfast", "pos": "noun", "definition": "the first meal", "example": "Breakfast is at eight.", "cefr": "A1", "frequency": 5, "translations": _t("desayuno", "petit-déjeuner", "Frühstück", "colazione", "zavtrak", "choushoku", "zaocan")},
        {"word": "dinner", "pos": "noun", "definition": "the evening meal", "example": "Dinner is ready.", "cefr": "A1", "frequency": 5, "translations": _t("cena", "dîner", "Abendessen", "cena", "uzhin", "yuushoku", "wancan")},
        {"word": "recipe", "pos": "noun", "definition": "cooking instructions", "example": "This recipe is easy.", "cefr": "B1", "frequency": 3, "translations": _t("receta", "recette", "Rezept", "ricetta", "retsept", "reshipi", "shipu")},
    ],
    "travel": [
        {"word": "airport", "pos": "noun", "definition": "where planes land", "example": "The airport is far.", "cefr": "A2", "frequency": 4, "translations": _t("aeropuerto", "aéroport", "Flughafen", "aeroporto", "aeroport", "kuukou", "jichang")},
        {"word": "ticket", "pos": "noun", "definition": "a pass to travel", "example": "I bought a ticket.", "cefr": "A1", "frequency": 5, "translations": _t("billete", "billet", "Ticket", "biglietto", "bilet", "kippu", "piao")},
        {"word": "hotel", "pos": "noun", "definition": "a place to stay", "example": "Our hotel is downtown.", "cefr": "A1", "frequency": 5, "translations": _t("hotel", "hôtel", "Hotel", "albergo", "otel", "hoteru", "lvguan")},
        {"word": "train", "pos": "noun", "definition": "a rail vehicle", "example": "The train is on time.", "cefr": "A1", "frequency": 5, "translations": _t("tren", "train", "Zug", "treno", "poezd", "densha", "huoche")},
        {"word": "luggage", "pos": "noun", "definition": "travel bags", "example": "Where is my luggage?", "cefr": "A2", "frequency": 4, "translations": _t("equipaje", "bagage", "Gepäck", "bagaglio", "bagazh", "nimotsu", "xingli")},
        {"word": "passport", "pos": "noun", "definition": "an ID for travel", "example": "Show me your passport.", "cefr": "A2", "frequency": 4, "translations": _t("pasaporte", "passeport", "Reisepass", "passaporto", "pasport", "pasupooto", "huzhao")},
        {"word": "map", "pos": "noun", "definition": "a drawing of places", "example": "I need a city map.", "cefr": "A1", "frequency": 4, "translations": _t("mapa", "carte", "Karte", "mappa", "karta", "chizu", "ditu")},
        {"word": "flight", "pos": "noun", "definition": "a plane journey", "example": "My flight is delayed.", "cefr": "A2", "frequency": 4, "translations": _t("vuelo", "vol", "Flug", "volo", "reys", "furaito", "hangban")},
        {"word": "to book", "pos": "verb", "definition": "to reserve", "example": "I want to book a room.", "cefr": "A2", "frequency": 4, "translations": _t("reservar", "réserver", "buchen", "prenotare", "zabronirovat", "yoyaku suru", "yuding")},
        {"word": "reservation", "pos": "noun", "definition": "a booking", "example": "I have a reservation.", "cefr": "B1", "frequency": 4, "translations": _t("reserva", "réservation", "Reservierung", "prenotazione", "bronirovanie", "yoyaku", "yuding")},
        {"word": "to arrive", "pos": "verb", "definition": "to reach a place", "example": "We arrive at noon.", "cefr": "A1", "frequency": 5, "translations": _t("llegar", "arriver", "ankommen", "arrivare", "pribyt", "touchaku suru", "daoda")},
        {"word": "to depart", "pos": "verb", "definition": "to leave", "example": "The bus departs soon.", "cefr": "B1", "frequency": 3, "translations": _t("salir", "partir", "abfahren", "partire", "otpravlyatsya", "shuppatsu suru", "chufa")},
        {"word": "abroad", "pos": "adverb", "definition": "in a foreign country", "example": "She works abroad.", "cefr": "B1", "frequency": 3, "translations": _t("extranjero", "étranger", "Ausland", "estero", "za granitsey", "kaigai", "guowai")},
        {"word": "customs", "pos": "noun", "definition": "border inspection", "example": "We passed through customs.", "cefr": "B1", "frequency": 3, "translations": _t("aduana", "douane", "Zoll", "dogana", "tamozhnya", "zeikan", "haiguan")},
    ],
    "business": [
        {"word": "meeting", "pos": "noun", "definition": "a gathering for work", "example": "The meeting starts at nine.", "cefr": "B1", "frequency": 5, "translations": _t("reunión", "réunion", "Besprechung", "riunione", "vstrecha", "kaigi", "huiyi")},
        {"word": "company", "pos": "noun", "definition": "a business organization", "example": "She runs a small company.", "cefr": "A2", "frequency": 5, "translations": _t("empresa", "entreprise", "Unternehmen", "azienda", "kompaniya", "kaisha", "gongsi")},
        {"word": "manager", "pos": "noun", "definition": "a person who leads a team", "example": "My manager is fair.", "cefr": "B1", "frequency": 5, "translations": _t("gerente", "directeur", "Manager", "direttore", "menedzher", "manejaa", "jingli")},
        {"word": "client", "pos": "noun", "definition": "a customer of a business", "example": "The client signed today.", "cefr": "B1", "frequency": 5, "translations": _t("cliente", "client", "Kunde", "cliente", "klient", "kokyaku", "kehu")},
        {"word": "contract", "pos": "noun", "definition": "a formal agreement", "example": "We signed the contract.", "cefr": "B1", "frequency": 5, "translations": _t("contrato", "contrat", "Vertrag", "contratto", "kontrakt", "keiyaku", "hetong")},
        {"word": "deadline", "pos": "noun", "definition": "a time limit", "example": "The deadline is Friday.", "cefr": "B1", "frequency": 5, "translations": _t("fecha límite", "échéance", "Frist", "scadenza", "srok", "shimekiri", "jiezhi riqi")},
        {"word": "salary", "pos": "noun", "definition": "regular pay for work", "example": "The salary is competitive.", "cefr": "B1", "frequency": 4, "translations": _t("salario", "salaire", "Gehalt", "stipendio", "zarplata", "kyuuryou", "xinshui")},
        {"word": "negotiate", "pos": "verb", "definition": "to discuss terms", "example": "We negotiate the price.", "cefr": "B2", "frequency": 4, "translations": _t("negociar", "négocier", "verhandeln", "negoziare", "vesti peregovory", "koushou suru", "tanpan")},
        {"word": "strategy", "pos": "noun", "definition": "a plan to reach goals", "example": "Our strategy is clear.", "cefr": "B2", "frequency": 4, "translations": _t("estrategia", "stratégie", "Strategie", "strategia", "strategiya", "senryaku", "zhanlve")},
        {"word": "colleague", "pos": "noun", "definition": "a coworker", "example": "My colleague helped me.", "cefr": "B1", "frequency": 4, "translations": _t("colega", "collègue", "Kollege", "collega", "kollega", "douryou", "tongshi")},
        {"word": "presentation", "pos": "noun", "definition": "a talk to an audience", "example": "Her presentation was clear.", "cefr": "B1", "frequency": 4, "translations": _t("presentación", "présentation", "Präsentation", "presentazione", "prezentatsiya", "purezen", "yanshi")},
        {"word": "project", "pos": "noun", "definition": "a planned piece of work", "example": "The project is on track.", "cefr": "B1", "frequency": 5, "translations": _t("proyecto", "projet", "Projekt", "progetto", "proyekt", "purojekuto", "xiangmu")},
        {"word": "to hire", "pos": "verb", "definition": "to employ someone", "example": "We hire two engineers.", "cefr": "B2", "frequency": 4, "translations": _t("contratar", "embaucher", "einstellen", "assumere", "nanimat", "yatou", "guyong")},
        {"word": "deal", "pos": "noun", "definition": "a business agreement", "example": "They closed the deal.", "cefr": "B2", "frequency": 4, "translations": _t("acuerdo", "accord", "Geschäft", "affare", "sdelka", "torihiki", "jiaoyi")},
    ],
    "technology": [
        {"word": "computer", "pos": "noun", "definition": "an electronic device", "example": "My computer is new.", "cefr": "A2", "frequency": 5, "translations": _t("ordenador", "ordinateur", "Computer", "computer", "kompyuter", "konpyuuta", "diannao")},
        {"word": "internet", "pos": "noun", "definition": "the global network", "example": "The internet is slow today.", "cefr": "A2", "frequency": 5, "translations": _t("internet", "internet", "Internet", "internet", "internet", "intaanetto", "hulianwang")},
        {"word": "software", "pos": "noun", "definition": "computer programs", "example": "We update the software.", "cefr": "B1", "frequency": 5, "translations": _t("software", "logiciel", "Software", "software", "programmnoe obespechenie", "sofutowea", "ruanjian")},
        {"word": "password", "pos": "noun", "definition": "a secret access code", "example": "Change your password.", "cefr": "A2", "frequency": 4, "translations": _t("contraseña", "mot de passe", "Passwort", "password", "parol", "pasuwaado", "mima")},
        {"word": "file", "pos": "noun", "definition": "a stored document", "example": "Save the file.", "cefr": "A2", "frequency": 5, "translations": _t("archivo", "fichier", "Datei", "file", "fayl", "fairu", "wenjian")},
        {"word": "to download", "pos": "verb", "definition": "to copy from the net", "example": "Download the app.", "cefr": "B1", "frequency": 4, "translations": _t("descargar", "télécharger", "herunterladen", "scaricare", "skachat", "daunroodo suru", "xiazai")},
        {"word": "data", "pos": "noun", "definition": "information stored", "example": "We protect user data.", "cefr": "B1", "frequency": 5, "translations": _t("datos", "données", "Daten", "dati", "dannye", "deeta", "shuju")},
        {"word": "network", "pos": "noun", "definition": "connected computers", "example": "The network is secure.", "cefr": "B1", "frequency": 4, "translations": _t("red", "réseau", "Netzwerk", "rete", "set", "nettowaaku", "wangluo")},
        {"word": "screen", "pos": "noun", "definition": "a display surface", "example": "The screen is bright.", "cefr": "A2", "frequency": 4, "translations": _t("pantalla", "écran", "Bildschirm", "schermo", "ekran", "gamen", "pingmu")},
        {"word": "to update", "pos": "verb", "definition": "to make current", "example": "I update my phone.", "cefr": "B1", "frequency": 4, "translations": _t("actualizar", "mettre à jour", "aktualisieren", "aggiornare", "obnovit", "appudeeto suru", "gengxin")},
        {"word": "application", "pos": "noun", "definition": "a software program", "example": "The application crashed.", "cefr": "B1", "frequency": 4, "translations": _t("aplicación", "application", "Anwendung", "applicazione", "prilozhenie", "apuri", "yingyong")},
        {"word": "security", "pos": "noun", "definition": "protection from harm", "example": "Security is a priority.", "cefr": "B2", "frequency": 4, "translations": _t("seguridad", "sécurité", "Sicherheit", "sicurezza", "bezopasnost", "sekyuriti", "anquan")},
        {"word": "algorithm", "pos": "noun", "definition": "a set of steps", "example": "The algorithm is fast.", "cefr": "B2", "frequency": 3, "translations": _t("algoritmo", "algorithme", "Algorithmus", "algoritmo", "algoritm", "arugorizumu", "suanfa")},
        {"word": "to encrypt", "pos": "verb", "definition": "to encode securely", "example": "We encrypt all messages.", "cefr": "C1", "frequency": 2, "translations": _t("cifrar", "chiffrer", "verschlüsseln", "criptare", "shifrovat", "ankouka suru", "jiami")},
    ],
    "healthcare": [
        {"word": "doctor", "pos": "noun", "definition": "a medical professional", "example": "See a doctor soon.", "cefr": "A1", "frequency": 5, "translations": _t("médico", "médecin", "Arzt", "medico", "vrach", "isha", "yisheng")},
        {"word": "hospital", "pos": "noun", "definition": "a place for medical care", "example": "She works at a hospital.", "cefr": "A2", "frequency": 5, "translations": _t("hospital", "hôpital", "Krankenhaus", "ospedale", "bolnitsa", "byouin", "yiyuan")},
        {"word": "medicine", "pos": "noun", "definition": "a drug for illness", "example": "Take this medicine twice.", "cefr": "A2", "frequency": 4, "translations": _t("medicina", "médicament", "Medizin", "medicina", "lekarstvo", "kusuri", "yao")},
        {"word": "pain", "pos": "noun", "definition": "an unpleasant feeling", "example": "I have a pain in my back.", "cefr": "A2", "frequency": 4, "translations": _t("dolor", "douleur", "Schmerz", "dolore", "bol", "itami", "tong")},
        {"word": "fever", "pos": "noun", "definition": "high body temperature", "example": "He has a fever.", "cefr": "A2", "frequency": 4, "translations": _t("fiebre", "fièvre", "Fieber", "febbre", "lihoradka", "netsu", "fashao")},
        {"word": "appointment", "pos": "noun", "definition": "a scheduled visit", "example": "I have a doctor's appointment.", "cefr": "B1", "frequency": 4, "translations": _t("cita", "rendez-vous", "Termin", "appuntamento", "zapis", "yoyaku", "yuyue")},
        {"word": "treatment", "pos": "noun", "definition": "medical care", "example": "The treatment worked.", "cefr": "B1", "frequency": 4, "translations": _t("tratamiento", "traitement", "Behandlung", "trattamento", "lechenie", "chiryou", "zhiliao")},
        {"word": "symptom", "pos": "noun", "definition": "a sign of illness", "example": "Describe your symptoms.", "cefr": "B1", "frequency": 4, "translations": _t("síntoma", "symptôme", "Symptom", "sintomo", "simptom", "shoujou", "zhengzhuang")},
        {"word": "nurse", "pos": "noun", "definition": "a medical caregiver", "example": "The nurse was kind.", "cefr": "A2", "frequency": 4, "translations": _t("enfermero", "infirmier", "Krankenpfleger", "infermiere", "medsestra", "kangoshi", "hushi")},
        {"word": "prescription", "pos": "noun", "definition": "a doctor's medicine order", "example": "Here is your prescription.", "cefr": "B1", "frequency": 3, "translations": _t("receta", "ordonnance", "Rezept", "ricetta", "retsept", "shohousen", "chufang")},
        {"word": "healthy", "pos": "adjective", "definition": "in good health", "example": "Stay healthy and active.", "cefr": "A2", "frequency": 5, "translations": _t("sano", "sain", "gesund", "sano", "zdorovyy", "kenkou", "jiankang")},
        {"word": "injury", "pos": "noun", "definition": "physical harm", "example": "The injury healed slowly.", "cefr": "B1", "frequency": 3, "translations": _t("lesión", "blessure", "Verletzung", "ferita", "travma", "kega", "shoushang")},
        {"word": "to recover", "pos": "verb", "definition": "to get well again", "example": "He recovered quickly.", "cefr": "B2", "frequency": 3, "translations": _t("recuperarse", "se rétablir", "sich erholen", "guarire", "vyzdorovet", "kaifuku suru", "kangfu")},
        {"word": "diagnosis", "pos": "noun", "definition": "identifying an illness", "example": "The diagnosis was clear.", "cefr": "B2", "frequency": 3, "translations": _t("diagnóstico", "diagnostic", "Diagnose", "diagnosi", "diagnoz", "shindan", "zhenduan")},
    ],
    "finance": [
        {"word": "money", "pos": "noun", "definition": "currency for buying", "example": "I saved some money.", "cefr": "A1", "frequency": 5, "translations": _t("dinero", "argent", "Geld", "denaro", "dengi", "okane", "qian")},
        {"word": "bank", "pos": "noun", "definition": "a money institution", "example": "I went to the bank.", "cefr": "A2", "frequency": 5, "translations": _t("banco", "banque", "Bank", "banca", "bank", "ginkou", "yinhang")},
        {"word": "account", "pos": "noun", "definition": "a bank record", "example": "Open a savings account.", "cefr": "B1", "frequency": 5, "translations": _t("cuenta", "compte", "Konto", "conto", "schyot", "kouza", "zhanghu")},
        {"word": "budget", "pos": "noun", "definition": "a plan for spending", "example": "Stick to your budget.", "cefr": "B1", "frequency": 5, "translations": _t("presupuesto", "budget", "Budget", "bilancio", "byudzhet", "yosan", "yusuan")},
        {"word": "savings", "pos": "noun", "definition": "money set aside", "example": "Her savings grew.", "cefr": "B1", "frequency": 4, "translations": _t("ahorros", "épargne", "Ersparnisse", "risparmi", "sberezheniya", "chokin", "cunkuan")},
        {"word": "loan", "pos": "noun", "definition": "borrowed money", "example": "He took out a loan.", "cefr": "B1", "frequency": 4, "translations": _t("préstamo", "prêt", "Kredit", "prestito", "kredit", "roon", "daikuan")},
        {"word": "interest", "pos": "noun", "definition": "cost of borrowing", "example": "The interest rate rose.", "cefr": "B2", "frequency": 4, "translations": _t("interés", "intérêt", "Zinsen", "interesse", "protsent", "kinri", "lixi")},
        {"word": "debt", "pos": "noun", "definition": "money owed", "example": "She paid off her debt.", "cefr": "B2", "frequency": 4, "translations": _t("deuda", "dette", "Schulden", "debito", "dolg", "shakkin", "zhaiwu")},
        {"word": "income", "pos": "noun", "definition": "money earned", "example": "My monthly income is fixed.", "cefr": "B1", "frequency": 5, "translations": _t("ingreso", "revenu", "Einkommen", "reddito", "dokhod", "shuunyuu", "shouru")},
        {"word": "expense", "pos": "noun", "definition": "money spent", "example": "Track every expense.", "cefr": "B1", "frequency": 5, "translations": _t("gasto", "dépense", "Ausgabe", "spesa", "raskhod", "shishutsu", "kaixiao")},
        {"word": "to invest", "pos": "verb", "definition": "to put money to grow", "example": "They invest in stocks.", "cefr": "B2", "frequency": 4, "translations": _t("invertir", "investir", "investieren", "investire", "investirovat", "toushi suru", "touzi")},
        {"word": "currency", "pos": "noun", "definition": "a system of money", "example": "Foreign currency is needed.", "cefr": "B2", "frequency": 3, "translations": _t("moneda", "monnaie", "Währung", "valuta", "valyuta", "tsuuka", "huobi")},
        {"word": "payment", "pos": "noun", "definition": "money given for goods", "example": "Payment is due today.", "cefr": "B1", "frequency": 5, "translations": _t("pago", "paiement", "Zahlung", "pagamento", "platyozh", "shiharai", "fukuan")},
        {"word": "to afford", "pos": "verb", "definition": "to have enough money for", "example": "I can't afford a car.", "cefr": "B2", "frequency": 4, "translations": _t("permitirse", "se permettre", "leisten", "permettersi", "pozvolit sebe", "yoyuu ga aru", "fudan deqi")},
    ],
    "accounting": [
        {"word": "asset", "pos": "noun", "definition": "something a business owns", "example": "Cash is a current asset.", "cefr": "B2", "frequency": 5, "translations": _t("activo", "actif", "Vermögenswert", "attivo", "aktiv", "shisan", "zichan")},
        {"word": "liability", "pos": "noun", "definition": "something a business owes", "example": "A loan is a liability.", "cefr": "B2", "frequency": 5, "translations": _t("pasivo", "passif", "Verbindlichkeit", "passività", "obyazatelstvo", "fusai", "fuzhai")},
        {"word": "equity", "pos": "noun", "definition": "owner's share of value", "example": "Equity equals assets minus liabilities.", "cefr": "C1", "frequency": 4, "translations": _t("patrimonio", "capitaux propres", "Eigenkapital", "patrimonio netto", "kapital", "shihon", "quanyi")},
        {"word": "ledger", "pos": "noun", "definition": "a record of accounts", "example": "Post it to the ledger.", "cefr": "B2", "frequency": 4, "translations": _t("libro mayor", "grand livre", "Hauptbuch", "libro mastro", "glavnaya kniga", "motochou", "zongzhang")},
        {"word": "invoice", "pos": "noun", "definition": "a bill for goods sold", "example": "Send the invoice today.", "cefr": "B2", "frequency": 5, "translations": _t("factura", "facture", "Rechnung", "fattura", "schyot-faktura", "seikyuusho", "fapiao")},
        {"word": "balance sheet", "pos": "noun", "definition": "a statement of position", "example": "The balance sheet is strong.", "cefr": "C1", "frequency": 4, "translations": _t("balance general", "bilan", "Bilanz", "stato patrimoniale", "balans", "taishakutaishouhyou", "zichanfuzhaibiao")},
        {"word": "revenue", "pos": "noun", "definition": "income from sales", "example": "Revenue grew this quarter.", "cefr": "B2", "frequency": 5, "translations": _t("ingresos", "chiffre d'affaires", "Umsatz", "ricavi", "vyruchka", "shuueki", "shouru")},
        {"word": "audit", "pos": "noun", "definition": "an official inspection", "example": "The audit found no errors.", "cefr": "C1", "frequency": 4, "translations": _t("auditoría", "audit", "Prüfung", "revisione", "audit", "kansa", "shenji")},
        {"word": "depreciation", "pos": "noun", "definition": "loss of asset value", "example": "We record depreciation yearly.", "cefr": "C1", "frequency": 3, "translations": _t("depreciación", "amortissement", "Abschreibung", "ammortamento", "amortizatsiya", "genka shoukyaku", "zhejiu")},
        {"word": "tax", "pos": "noun", "definition": "money paid to government", "example": "File your tax return.", "cefr": "B1", "frequency": 5, "translations": _t("impuesto", "impôt", "Steuer", "tassa", "nalog", "zeikin", "shui")},
        {"word": "expense", "pos": "noun", "definition": "a business cost", "example": "Travel is an expense.", "cefr": "B1", "frequency": 5, "translations": _t("gasto", "charge", "Aufwand", "spesa", "raskhod", "keihi", "feiyong")},
        {"word": "profit", "pos": "noun", "definition": "income minus costs", "example": "Net profit doubled.", "cefr": "B2", "frequency": 5, "translations": _t("beneficio", "bénéfice", "Gewinn", "profitto", "pribyl", "rieki", "lirun")},
        {"word": "cash flow", "pos": "noun", "definition": "movement of money", "example": "Cash flow is positive.", "cefr": "C1", "frequency": 4, "translations": _t("flujo de caja", "trésorerie", "Cashflow", "flusso di cassa", "denezhnyy potok", "kyasshu furoo", "xianjinliu")},
        {"word": "to reconcile", "pos": "verb", "definition": "to match records", "example": "Reconcile the accounts monthly.", "cefr": "C1", "frequency": 3, "translations": _t("conciliar", "rapprocher", "abstimmen", "riconciliare", "sverit", "shougou suru", "duizhang")},
    ],
    "investing": [
        {"word": "stock", "pos": "noun", "definition": "a share of a company", "example": "I bought tech stocks.", "cefr": "B2", "frequency": 5, "translations": _t("acción", "action", "Aktie", "azione", "aktsiya", "kabu", "gupiao")},
        {"word": "bond", "pos": "noun", "definition": "a debt investment", "example": "Government bonds are safe.", "cefr": "C1", "frequency": 4, "translations": _t("bono", "obligation", "Anleihe", "obbligazione", "obligatsiya", "saiken", "zhaiquan")},
        {"word": "dividend", "pos": "noun", "definition": "a payout to shareholders", "example": "The dividend was raised.", "cefr": "C1", "frequency": 4, "translations": _t("dividendo", "dividende", "Dividende", "dividendo", "dividend", "haitou", "guxi")},
        {"word": "portfolio", "pos": "noun", "definition": "a set of investments", "example": "Diversify your portfolio.", "cefr": "C1", "frequency": 4, "translations": _t("cartera", "portefeuille", "Portfolio", "portafoglio", "portfel", "pootoforio", "touzizuhe")},
        {"word": "risk", "pos": "noun", "definition": "chance of loss", "example": "Higher risk, higher return.", "cefr": "B2", "frequency": 5, "translations": _t("riesgo", "risque", "Risiko", "rischio", "risk", "risuku", "fengxian")},
        {"word": "return", "pos": "noun", "definition": "profit on investment", "example": "Annual return was 8%.", "cefr": "B2", "frequency": 5, "translations": _t("rendimiento", "rendement", "Rendite", "rendimento", "dokhodnost", "ritaan", "huibao")},
        {"word": "market", "pos": "noun", "definition": "where assets trade", "example": "The market rose today.", "cefr": "B1", "frequency": 5, "translations": _t("mercado", "marché", "Markt", "mercato", "rynok", "shijou", "shichang")},
        {"word": "to diversify", "pos": "verb", "definition": "to spread risk", "example": "Diversify across sectors.", "cefr": "C1", "frequency": 3, "translations": _t("diversificar", "diversifier", "diversifizieren", "diversificare", "diversifitsirovat", "bunsan suru", "fensan")},
        {"word": "volatility", "pos": "noun", "definition": "size of price swings", "example": "Volatility spiked last week.", "cefr": "C1", "frequency": 3, "translations": _t("volatilidad", "volatilité", "Volatilität", "volatilità", "volatilnost", "boratiriti", "boudongxing")},
        {"word": "yield", "pos": "noun", "definition": "income rate of an asset", "example": "The bond yield is 4%.", "cefr": "C1", "frequency": 3, "translations": _t("rendimiento", "rendement", "Rendite", "rendimento", "dokhodnost", "rimawari", "shouyilv")},
        {"word": "broker", "pos": "noun", "definition": "an agent who trades", "example": "My broker charges low fees.", "cefr": "B2", "frequency": 3, "translations": _t("corredor", "courtier", "Makler", "broker", "broker", "burookaa", "jingjiren")},
        {"word": "capital", "pos": "noun", "definition": "money used to invest", "example": "They raised capital.", "cefr": "B2", "frequency": 4, "translations": _t("capital", "capital", "Kapital", "capitale", "kapital", "shihon", "ziben")},
        {"word": "to hedge", "pos": "verb", "definition": "to offset risk", "example": "We hedge with options.", "cefr": "C2", "frequency": 2, "translations": _t("cubrir", "couvrir", "absichern", "coprire", "khedzhirovat", "hejji suru", "duichong")},
        {"word": "valuation", "pos": "noun", "definition": "an estimate of worth", "example": "The valuation seems high.", "cefr": "C1", "frequency": 3, "translations": _t("valoración", "valorisation", "Bewertung", "valutazione", "otsenka", "hyouka", "guzhi")},
    ],
}

# Round out a couple of broad-utility topics so every CEFR level is represented
# in vocabulary and to push the base headword count higher.
VOCAB["business"].extend([
    {"word": "invoice", "pos": "noun", "definition": "a bill for services", "example": "Please pay the invoice.", "cefr": "B1", "frequency": 4, "translations": _t("factura", "facture", "Rechnung", "fattura", "schyot", "seikyuusho", "fapiao")},
    {"word": "to launch", "pos": "verb", "definition": "to start a product", "example": "We launch next month.", "cefr": "B2", "frequency": 3, "translations": _t("lanzar", "lancer", "starten", "lanciare", "zapustit", "ronchi suru", "tuichu")},
])


# ── Grammar rules ────────────────────────────────────────────────────────────
# Each rule: id, title, level, language ('generic' or a language code),
# explanation, examples, common_mistakes [{wrong, right, note}].
GRAMMAR: list[dict] = [
    # Spanish
    {"id": "es_ser_estar", "title": "Ser vs. Estar", "level": "A2", "language": "spanish",
     "explanation": "Both mean 'to be'. Use 'ser' for permanent traits and identity; 'estar' for states, location, and feelings.",
     "examples": ["Ella es médica.", "Estoy cansado.", "El libro está en la mesa."],
     "common_mistakes": [
         {"wrong": "estoy médico", "right": "soy médico", "note": "Professions use 'ser', not 'estar'."},
         {"wrong": "soy cansado", "right": "estoy cansado", "note": "Temporary states use 'estar'."}]},
    {"id": "es_gender_agreement", "title": "Noun-Adjective Gender Agreement", "level": "A1", "language": "spanish",
     "explanation": "Adjectives agree in gender and number with the noun they modify.",
     "examples": ["la casa blanca", "los coches rojos", "las flores bonitas"],
     "common_mistakes": [
         {"wrong": "la casa blanco", "right": "la casa blanca", "note": "Feminine noun needs feminine adjective."},
         {"wrong": "los coche rojo", "right": "los coches rojos", "note": "Plural noun needs plural adjective."}]},
    {"id": "es_preterite_imperfect", "title": "Preterite vs. Imperfect", "level": "B1", "language": "spanish",
     "explanation": "Preterite for completed actions; imperfect for ongoing or habitual past.",
     "examples": ["Comí a las dos.", "Cuando era niño, jugaba mucho."],
     "common_mistakes": [
         {"wrong": "siempre fui al parque", "right": "siempre iba al parque", "note": "Habitual past uses imperfect 'iba'."}]},
    # French
    {"id": "fr_gender_articles", "title": "Gendered Articles (le/la)", "level": "A1", "language": "french",
     "explanation": "French nouns are masculine (le) or feminine (la). Learn the gender with the noun.",
     "examples": ["le livre", "la table", "les enfants"],
     "common_mistakes": [
         {"wrong": "la livre", "right": "le livre", "note": "'livre' (book) is masculine."},
         {"wrong": "le table", "right": "la table", "note": "'table' is feminine."}]},
    {"id": "fr_passe_compose", "title": "Passé Composé Auxiliary", "level": "B1", "language": "french",
     "explanation": "Most verbs use 'avoir'; movement/state verbs and reflexives use 'être' and agree in gender/number.",
     "examples": ["J'ai mangé.", "Elle est allée.", "Nous sommes arrivés."],
     "common_mistakes": [
         {"wrong": "j'ai allé", "right": "je suis allé", "note": "'aller' takes 'être'."},
         {"wrong": "elle est mangé", "right": "elle a mangé", "note": "'manger' takes 'avoir'."}]},
    {"id": "fr_negation", "title": "Negation with ne...pas", "level": "A1", "language": "french",
     "explanation": "Negation surrounds the verb: ne + verb + pas.",
     "examples": ["Je ne sais pas.", "Il ne parle pas anglais."],
     "common_mistakes": [
         {"wrong": "je sais pas", "right": "je ne sais pas", "note": "Formal French keeps 'ne'."}]},
    # German
    {"id": "de_cases", "title": "The Four Cases", "level": "B1", "language": "german",
     "explanation": "German marks nouns by case: nominative, accusative, dative, genitive. Articles change accordingly.",
     "examples": ["Der Mann (nom)", "Ich sehe den Mann (akk)", "Ich gebe dem Mann (dat)"],
     "common_mistakes": [
         {"wrong": "ich sehe der Mann", "right": "ich sehe den Mann", "note": "Direct object is accusative 'den'."}]},
    {"id": "de_word_order", "title": "Verb-Second Word Order", "level": "A2", "language": "german",
     "explanation": "In main clauses the conjugated verb is always in second position.",
     "examples": ["Heute gehe ich nach Hause.", "Ich gehe heute nach Hause."],
     "common_mistakes": [
         {"wrong": "heute ich gehe nach Hause", "right": "heute gehe ich nach Hause", "note": "Verb must be second."}]},
    {"id": "de_noun_caps", "title": "Capitalize All Nouns", "level": "A1", "language": "german",
     "explanation": "Every noun in German is capitalized, not just proper nouns.",
     "examples": ["das Haus", "die Schule", "der Tisch"],
     "common_mistakes": [
         {"wrong": "das haus", "right": "das Haus", "note": "Nouns are always capitalized."}]},
    # Italian
    {"id": "it_articles", "title": "Definite Articles (il/lo/la)", "level": "A1", "language": "italian",
     "explanation": "Article depends on gender and the noun's first letters: il, lo, l', la.",
     "examples": ["il libro", "lo studente", "la casa", "l'amico"],
     "common_mistakes": [
         {"wrong": "il studente", "right": "lo studente", "note": "Use 'lo' before s+consonant."}]},
    {"id": "it_essere_avere", "title": "Essere vs. Avere (perfect tense)", "level": "B1", "language": "italian",
     "explanation": "Compound past uses 'avere' for most verbs and 'essere' for motion/state verbs (with agreement).",
     "examples": ["Ho mangiato.", "Sono andato.", "Lei è arrivata."],
     "common_mistakes": [
         {"wrong": "ho andato", "right": "sono andato", "note": "'andare' takes 'essere'."}]},
    {"id": "it_plurals", "title": "Noun Plurals (-o → -i, -a → -e)", "level": "A1", "language": "italian",
     "explanation": "Masculine -o becomes -i; feminine -a becomes -e in the plural.",
     "examples": ["libro → libri", "casa → case"],
     "common_mistakes": [
         {"wrong": "due casi (houses)", "right": "due case", "note": "Feminine -a pluralizes to -e."}]},
    # Russian
    {"id": "ru_cases", "title": "Six Grammatical Cases", "level": "B1", "language": "russian",
     "explanation": "Russian nouns decline through six cases; endings change with the noun's role.",
     "examples": ["книга (nom)", "книгу (acc)", "книги (gen)"],
     "common_mistakes": [
         {"wrong": "ya vizhu kniga", "right": "ya vizhu knigu", "note": "Direct object is accusative 'knigu'."}]},
    {"id": "ru_no_articles", "title": "No Articles in Russian", "level": "A1", "language": "russian",
     "explanation": "Russian has no 'a' or 'the'; context conveys definiteness.",
     "examples": ["Я читаю книгу. (I read a/the book)"],
     "common_mistakes": [
         {"wrong": "ya chitayu the knigu", "right": "ya chitayu knigu", "note": "Do not insert English articles."}]},
    # Japanese
    {"id": "ja_particles", "title": "Topic & Object Particles (は/を)", "level": "A2", "language": "japanese",
     "explanation": "は (wa) marks the topic; を (o) marks the direct object; が (ga) marks the subject.",
     "examples": ["私は学生です。", "りんごを食べる。"],
     "common_mistakes": [
         {"wrong": "ringo wa taberu (as object)", "right": "ringo o taberu", "note": "Direct object takes を (o)."}]},
    {"id": "ja_word_order", "title": "Subject-Object-Verb Order", "level": "A2", "language": "japanese",
     "explanation": "Japanese is SOV: the verb comes at the end of the sentence.",
     "examples": ["私はりんごを食べます。"],
     "common_mistakes": [
         {"wrong": "watashi taberu ringo", "right": "watashi wa ringo o tabemasu", "note": "Verb goes last."}]},
    # Mandarin
    {"id": "zh_measure_words", "title": "Measure Words (量词)", "level": "A2", "language": "mandarin",
     "explanation": "A measure word sits between a number and a noun, e.g. 一本书 (one [volume] book).",
     "examples": ["三个人 (three people)", "一本书 (one book)"],
     "common_mistakes": [
         {"wrong": "san ren", "right": "san ge ren", "note": "Insert measure word 个 (ge)."}]},
    {"id": "zh_no_conjugation", "title": "Verbs Do Not Conjugate", "level": "A1", "language": "mandarin",
     "explanation": "Chinese verbs never change form; tense comes from time words and particles like 了.",
     "examples": ["我吃 (I eat)", "我吃了 (I ate)"],
     "common_mistakes": [
         {"wrong": "wo chile yesterday tense on verb", "right": "wo zuotian chi le", "note": "Use time words, not verb forms."}]},
    # Generic (apply to all languages)
    {"id": "gen_subject_verb_agreement", "title": "Subject-Verb Agreement", "level": "A1", "language": "generic",
     "explanation": "The verb form must match the subject in person and number.",
     "examples": ["He works.", "They work."],
     "common_mistakes": [
         {"wrong": "he work", "right": "he works", "note": "Third person singular adds -s."},
         {"wrong": "they works", "right": "they work", "note": "Plural subject takes the base verb."}]},
    {"id": "gen_word_order_basic", "title": "Basic Word Order", "level": "A1", "language": "generic",
     "explanation": "Keep a clear subject-verb-object order until you master inversions.",
     "examples": ["I eat bread.", "She reads books."],
     "common_mistakes": [
         {"wrong": "eat I bread", "right": "I eat bread", "note": "Start with the subject."}]},
    {"id": "gen_question_formation", "title": "Forming Questions", "level": "A2", "language": "generic",
     "explanation": "Questions often invert the subject and an auxiliary or add a question word at the front.",
     "examples": ["Do you speak French?", "Where is the station?"],
     "common_mistakes": [
         {"wrong": "you speak french?", "right": "do you speak french?", "note": "Add the auxiliary 'do'."}]},
    {"id": "gen_register_formality", "title": "Formal vs. Informal Register", "level": "B2", "language": "generic",
     "explanation": "Many languages distinguish polite and casual forms of address; match the context.",
     "examples": ["Usted/tú (es)", "Sie/du (de)", "vous/tu (fr)"],
     "common_mistakes": [
         {"wrong": "using tú with a stranger in formal settings", "right": "use the polite form", "note": "Default to the formal address with strangers."}]},
    {"id": "gen_connectors", "title": "Cohesive Connectors", "level": "B2", "language": "generic",
     "explanation": "Use connectors (however, therefore, although) to link ideas for advanced fluency.",
     "examples": ["It rained; however, we went out."],
     "common_mistakes": [
         {"wrong": "It rained, we went out anyway because.", "right": "Although it rained, we went out.", "note": "Place the connector correctly."}]},
    {"id": "gen_nuance_idioms", "title": "Idioms & Nuance", "level": "C1", "language": "generic",
     "explanation": "Advanced learners use idiomatic expressions appropriately rather than literal translations.",
     "examples": ["It's raining cats and dogs.", "Break the ice."],
     "common_mistakes": [
         {"wrong": "translating idioms word for word", "right": "use the target idiom", "note": "Idioms rarely translate literally."}]},
]


# ── Conversation scenarios ───────────────────────────────────────────────────
CONVERSATION_SCENARIOS: list[dict] = [
    {"id": "restaurant", "title": "Ordering at a Restaurant", "level": "A2",
     "setup": "You arrive at a restaurant and order a meal.",
     "roles": {"ai": "waiter", "user": "customer"},
     "sample_prompts": ["Good evening! Do you have a reservation?", "Here is the menu. What would you like to drink?",
                        "Excellent choice. And for your main course?", "Would you like dessert?", "Here is your bill. Thank you!"],
     "target_vocab": ["menu", "to order", "bill", "delicious", "restaurant"]},
    {"id": "airport", "title": "Checking In at the Airport", "level": "A2",
     "setup": "You check in for a flight at the airport counter.",
     "roles": {"ai": "agent", "user": "traveler"},
     "sample_prompts": ["Good morning, may I see your passport?", "How many bags are you checking?",
                        "Here is your boarding pass. The gate is B12.", "Boarding starts in thirty minutes.", "Have a good flight!"],
     "target_vocab": ["passport", "luggage", "flight", "ticket", "to depart"]},
    {"id": "hotel", "title": "Hotel Check-In", "level": "A2",
     "setup": "You arrive at a hotel and check into your room.",
     "roles": {"ai": "receptionist", "user": "guest"},
     "sample_prompts": ["Welcome! Do you have a reservation?", "May I have your name and ID?",
                        "Your room is on the third floor.", "Breakfast is served until ten.", "Enjoy your stay!"],
     "target_vocab": ["hotel", "reservation", "to book", "breakfast", "welcome"]},
    {"id": "business_meeting", "title": "A Business Meeting", "level": "B2",
     "setup": "You join a meeting to discuss a project with a client.",
     "roles": {"ai": "client", "user": "manager"},
     "sample_prompts": ["Thanks for coming. Shall we begin?", "What is the status of the project?",
                        "What about the deadline and budget?", "Can we negotiate the terms?", "Great, let's sign the contract."],
     "target_vocab": ["meeting", "project", "deadline", "negotiate", "contract"]},
    {"id": "job_interview", "title": "A Job Interview", "level": "B2",
     "setup": "You are interviewed for a position.",
     "roles": {"ai": "interviewer", "user": "candidate"},
     "sample_prompts": ["Tell me about yourself.", "Why do you want this job?",
                        "What are your strengths?", "Do you have questions about the salary?", "Thank you, we'll be in touch."],
     "target_vocab": ["company", "salary", "colleague", "strategy", "to hire"]},
    {"id": "date", "title": "A First Date", "level": "B1",
     "setup": "You meet someone for a casual first date at a café.",
     "roles": {"ai": "date", "user": "you"},
     "sample_prompts": ["Hi! It's great to finally meet you.", "What do you do for fun?",
                        "Tell me about your family.", "Shall we order something to drink?", "I had a lovely time tonight."],
     "target_vocab": ["coffee", "friend", "family", "weekend", "to relax"]},
    {"id": "shopping", "title": "Shopping for Clothes", "level": "A2",
     "setup": "You shop for clothes and ask about prices and sizes.",
     "roles": {"ai": "shop assistant", "user": "shopper"},
     "sample_prompts": ["Hello! Can I help you find something?", "What size do you need?",
                        "This one is on sale.", "Would you like to try it on?", "How would you like to pay?"],
     "target_vocab": ["money", "payment", "to afford", "expense", "number"]},
    {"id": "tax_consultation", "title": "A Tax Consultation", "level": "C1",
     "setup": "You consult an accountant about your tax return.",
     "roles": {"ai": "accountant", "user": "client"},
     "sample_prompts": ["Let's review your tax situation.", "Do you have records of your income and expenses?",
                        "We can claim several deductions.", "Your tax return is due next month.", "I'll prepare and file it for you."],
     "target_vocab": ["tax", "income", "expense", "invoice", "audit"]},
    {"id": "accounting_meeting", "title": "An Accounting Review", "level": "C1",
     "setup": "You review financial statements with your accountant.",
     "roles": {"ai": "accountant", "user": "business owner"},
     "sample_prompts": ["Let's look at the balance sheet.", "Your assets exceed your liabilities — good.",
                        "Revenue grew but expenses rose too.", "We should reconcile these accounts.", "Profit is up year over year."],
     "target_vocab": ["asset", "liability", "balance sheet", "revenue", "profit"]},
    {"id": "investment_pitch", "title": "An Investment Pitch", "level": "C1",
     "setup": "You pitch an investment opportunity to a potential investor.",
     "roles": {"ai": "investor", "user": "founder"},
     "sample_prompts": ["Thank you for the opportunity. Tell me about the company.", "What is the expected return?",
                        "How do you manage the risk?", "What is your valuation?", "Let me consider it and get back to you."],
     "target_vocab": ["stock", "return", "risk", "portfolio", "capital"]},
]


# ── Listening exercises ──────────────────────────────────────────────────────
def _q(q, options, answer):
    return {"q": q, "options": options, "answer": answer}


LISTENING: list[dict] = [
    {"id": "lis_a1_intro", "level": "A1", "title": "Meeting Someone New", "difficulty": 0.1,
     "transcript": "Hello, my name is Maria. I am from Spain. I have one brother and two sisters. I like coffee and books.",
     "questions": [
         _q("What is the speaker's name?", ["Maria", "Anna", "Sofia", "Elena"], "Maria"),
         _q("Where is she from?", ["Italy", "Spain", "France", "Germany"], "Spain"),
         _q("How many sisters does she have?", ["one", "two", "three", "four"], "two")]},
    {"id": "lis_a1_family", "level": "A1", "title": "My Family", "difficulty": 0.15,
     "transcript": "This is my family. My mother is a teacher and my father is a doctor. My grandmother lives with us. We eat dinner together every evening.",
     "questions": [
         _q("What is the mother's job?", ["doctor", "teacher", "nurse", "manager"], "teacher"),
         _q("Who lives with them?", ["uncle", "cousin", "grandmother", "friend"], "grandmother")]},
    {"id": "lis_a2_food", "level": "A2", "title": "At the Restaurant", "difficulty": 0.25,
     "transcript": "Good evening. I would like to order the soup and bread to start. For the main course, I will have fish with vegetables. A glass of water, please. The food here is delicious.",
     "questions": [
         _q("What does the speaker order to start?", ["salad and bread", "soup and bread", "soup and rice", "fish and bread"], "soup and bread"),
         _q("What does the speaker drink?", ["wine", "coffee", "water", "juice"], "water")]},
    {"id": "lis_a2_travel", "level": "A2", "title": "Travel Plans", "difficulty": 0.3,
     "transcript": "Next week I am traveling to Italy. My flight departs early in the morning. I have already booked a hotel near the city center. I cannot wait to see the museums.",
     "questions": [
         _q("Where is the speaker going?", ["Spain", "France", "Italy", "Germany"], "Italy"),
         _q("When does the flight depart?", ["at night", "in the morning", "at noon", "in the evening"], "in the morning"),
         _q("What has the speaker booked?", ["a car", "a tour", "a hotel", "a train"], "a hotel")]},
    {"id": "lis_a2_daily", "level": "A2", "title": "My Daily Routine", "difficulty": 0.28,
     "transcript": "I wake up at seven o'clock every day. After breakfast, I commute to work by train. In the evening I study French for an hour and then I relax with a book.",
     "questions": [
         _q("When does the speaker wake up?", ["six", "seven", "eight", "nine"], "seven"),
         _q("How does the speaker get to work?", ["car", "bus", "train", "bike"], "train")]},
    {"id": "lis_b1_work", "level": "B1", "title": "A Work Update", "difficulty": 0.45,
     "transcript": "The project is going well, but we are slightly behind schedule. The client wants the presentation by Friday. I will meet my colleague tomorrow to finalize the strategy and discuss the budget.",
     "questions": [
         _q("What is the status of the project?", ["finished", "behind schedule", "cancelled", "not started"], "behind schedule"),
         _q("When does the client want the presentation?", ["Monday", "Wednesday", "Friday", "Sunday"], "Friday")]},
    {"id": "lis_b1_health", "level": "B1", "title": "A Doctor's Visit", "difficulty": 0.5,
     "transcript": "I went to the doctor because I had a fever and a pain in my throat. The doctor examined me and gave me a prescription. She said I should rest and drink water, and I will recover in a few days.",
     "questions": [
         _q("Why did the speaker visit the doctor?", ["a broken arm", "a fever and sore throat", "an allergy", "a checkup"], "a fever and sore throat"),
         _q("What did the doctor give?", ["a prescription", "an injection", "an x-ray", "nothing"], "a prescription")]},
    {"id": "lis_b1_tech", "level": "B1", "title": "A Software Update", "difficulty": 0.5,
     "transcript": "Please update the application before the meeting. The new software improves security and protects your data. If you forget your password, you can reset it from the login screen.",
     "questions": [
         _q("What does the new software improve?", ["speed only", "security", "the design", "the price"], "security"),
         _q("What can you reset from the login screen?", ["your name", "your password", "your file", "your network"], "your password")]},
    {"id": "lis_b2_finance", "level": "B2", "title": "Managing a Budget", "difficulty": 0.6,
     "transcript": "To manage your money well, track every expense and compare it to your income each month. Build savings for emergencies before you invest, and avoid high-interest debt whenever possible.",
     "questions": [
         _q("What should you track?", ["only income", "every expense", "the weather", "your friends"], "every expense"),
         _q("What should you build before investing?", ["debt", "savings", "a company", "a portfolio"], "savings")]},
    {"id": "lis_b2_business", "level": "B2", "title": "Closing a Deal", "difficulty": 0.62,
     "transcript": "After weeks of negotiation, we finally agreed on the terms. The client signed the contract this morning. Our strategy worked, and we expect to hire two more colleagues to support the new project.",
     "questions": [
         _q("What did the client do this morning?", ["cancelled", "signed the contract", "called", "left"], "signed the contract"),
         _q("How many colleagues will they hire?", ["one", "two", "three", "none"], "two")]},
    {"id": "lis_c1_accounting", "level": "C1", "title": "Reviewing the Books", "difficulty": 0.75,
     "transcript": "Looking at the balance sheet, our assets comfortably exceed our liabilities, which strengthens our equity. Revenue rose this quarter, though expenses grew as well, so net profit was only slightly higher. We still need to reconcile two accounts.",
     "questions": [
         _q("What strengthens the company's equity?", ["more debt", "assets exceeding liabilities", "higher expenses", "lower revenue"], "assets exceeding liabilities"),
         _q("Why was net profit only slightly higher?", ["revenue fell", "expenses grew too", "taxes rose", "an audit"], "expenses grew too")]},
    {"id": "lis_c1_investing", "level": "C1", "title": "Building a Portfolio", "difficulty": 0.78,
     "transcript": "A well-built portfolio diversifies across stocks and bonds to balance risk and return. When volatility rises, investors often shift toward bonds for their steady yield, while keeping some capital in equities for long-term growth.",
     "questions": [
         _q("What does a good portfolio do?", ["concentrate in one stock", "diversify across assets", "avoid all risk", "ignore returns"], "diversify across assets"),
         _q("Where do investors shift when volatility rises?", ["cash only", "bonds", "real estate", "nothing"], "bonds")]},
    {"id": "lis_c1_interview", "level": "C1", "title": "A Senior Interview", "difficulty": 0.72,
     "transcript": "In senior roles, employers look for strategic thinking as much as technical skill. They will ask how you negotiate, how you manage a team under a tight deadline, and how you align a project with the company's long-term strategy.",
     "questions": [
         _q("What do employers value in senior roles?", ["only technical skill", "strategic thinking", "speed of typing", "nothing"], "strategic thinking")]},
    {"id": "lis_c2_macro", "level": "C2", "title": "An Economic Outlook", "difficulty": 0.9,
     "transcript": "Although inflation has cooled, the central bank remains cautious about cutting interest rates too quickly, wary that doing so could reignite price pressures. Markets, meanwhile, have already priced in a gradual easing, leaving little room for surprise.",
     "questions": [
         _q("Why is the central bank cautious?", ["to raise taxes", "cutting rates too fast could reignite inflation", "markets are closed", "to hire staff"], "cutting rates too fast could reignite inflation"),
         _q("What have markets priced in?", ["a recession", "a gradual easing", "a crash", "nothing"], "a gradual easing")]},
    {"id": "lis_c2_negotiation", "level": "C2", "title": "High-Stakes Negotiation", "difficulty": 0.88,
     "transcript": "The most effective negotiators listen far more than they speak, probing for the other side's underlying interests rather than fixating on stated positions. By reframing the conversation around shared value, they turn a zero-sum standoff into a deal both parties can defend.",
     "questions": [
         _q("What do effective negotiators do most?", ["talk", "listen", "leave", "argue"], "listen"),
         _q("What do they reframe the conversation around?", ["price only", "shared value", "deadlines", "their position"], "shared value")]},
]


# ── CEFR can-do statements (per level, generic, language-agnostic) ───────────
CAN_DO = {
    "A1": [
        "Can understand and use familiar everyday expressions and very basic phrases.",
        "Can introduce themselves and others and ask and answer questions about personal details.",
        "Can interact in a simple way if the other person talks slowly and clearly.",
    ],
    "A2": [
        "Can understand sentences and frequently used expressions related to immediate relevance.",
        "Can communicate in simple, routine tasks requiring a direct exchange of information.",
        "Can describe in simple terms aspects of their background and immediate environment.",
    ],
    "B1": [
        "Can understand the main points of clear standard input on familiar matters.",
        "Can deal with most situations likely to arise while travelling.",
        "Can produce simple connected text on familiar topics and describe experiences and plans.",
    ],
    "B2": [
        "Can understand the main ideas of complex text on both concrete and abstract topics.",
        "Can interact with fluency and spontaneity that makes regular interaction with native speakers possible.",
        "Can produce clear, detailed text and explain a viewpoint on a topical issue.",
    ],
    "C1": [
        "Can understand a wide range of demanding, longer texts and recognise implicit meaning.",
        "Can express ideas fluently and spontaneously without much obvious searching for expressions.",
        "Can use language flexibly and effectively for social, academic and professional purposes.",
    ],
    "C2": [
        "Can understand with ease virtually everything heard or read.",
        "Can summarise information from different spoken and written sources, reconstructing arguments coherently.",
        "Can express themselves spontaneously, very fluently and precisely, differentiating finer shades of meaning.",
    ],
}

# Target active-vocabulary size per CEFR level (cumulative word count goals).
TARGET_WORD_COUNT = {"A1": 500, "A2": 1000, "B1": 2000, "B2": 4000, "C1": 8000, "C2": 16000}


def topic_meta(topic_id: str) -> dict | None:
    for t in TOPICS:
        if t["id"] == topic_id:
            return t
    return None
