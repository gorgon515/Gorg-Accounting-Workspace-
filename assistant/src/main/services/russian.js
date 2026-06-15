'use strict';

// Russian language program — a full CEFR A1→C2 path to fluency for ARIA.
//
// This module owns the CURRICULUM (embedded content), the learner's PROGRESS
// (persisted in store under `russianProgress`), and the brain tools/system
// prompt that let ARIA run the program conversationally. Spaced repetition is
// NOT re-implemented here: we reuse study.js (SM-2). New vocab is pushed into
// study.api.addVocab({...subject:'russian'}) so it joins the existing review
// queue, and the due queue is read back via study.api.dueFlashcards.
//
// Everything is plain data (arrays/objects) so the renderer and brain can read
// it directly. A1/A2 lessons carry full teaching content; B1–C2 carry rich
// outlines (title + grammarFocus + canDo + key vocab) the AI tutor expands on
// demand. This file is intentionally large — the content IS the product.

const store = require('../store');
const study = require('./study');

const STORE_KEY = 'russianProgress';
const SUBJECT = 'russian';
const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

const today = () => new Date().toISOString().slice(0, 10);
const addDays = (d, n) => {
  const dt = new Date(d + 'T00:00:00');
  dt.setDate(dt.getDate() + n);
  return dt.toISOString().slice(0, 10);
};
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));

// ===========================================================================
// ALPHABET — all 33 Cyrillic letters.
// sound is a plain/IPA-ish hint; translit is the common romanization.
// ===========================================================================
const ALPHABET = [
  { char: 'А а', name: 'a', sound: 'a as in "father"', translit: 'a', example: { ru: 'а́збука', en: 'alphabet' } },
  { char: 'Б б', name: 'be', sound: 'b as in "bat"', translit: 'b', example: { ru: 'банк', en: 'bank' } },
  { char: 'В в', name: 've', sound: 'v as in "van"', translit: 'v', example: { ru: 'вода́', en: 'water' } },
  { char: 'Г г', name: 'ge', sound: 'g as in "go"', translit: 'g', example: { ru: 'го́род', en: 'city' } },
  { char: 'Д д', name: 'de', sound: 'd as in "dog"', translit: 'd', example: { ru: 'да', en: 'yes' } },
  { char: 'Е е', name: 'ye', sound: 'ye as in "yes"', translit: 'ye/e', example: { ru: 'е́сли', en: 'if' } },
  { char: 'Ё ё', name: 'yo', sound: 'yo as in "yonder" (always stressed)', translit: 'yo', example: { ru: 'ёж', en: 'hedgehog' } },
  { char: 'Ж ж', name: 'zhe', sound: 's as in "measure"', translit: 'zh', example: { ru: 'жена́', en: 'wife' } },
  { char: 'З з', name: 'ze', sound: 'z as in "zoo"', translit: 'z', example: { ru: 'зо́нт', en: 'umbrella' } },
  { char: 'И и', name: 'i', sound: 'ee as in "see"', translit: 'i', example: { ru: 'и', en: 'and' } },
  { char: 'Й й', name: 'i kratkoye', sound: 'y as in "boy" (short i)', translit: 'y', example: { ru: 'мой', en: 'my' } },
  { char: 'К к', name: 'ka', sound: 'k as in "kit"', translit: 'k', example: { ru: 'кот', en: 'cat' } },
  { char: 'Л л', name: 'el', sound: 'l as in "lamp"', translit: 'l', example: { ru: 'ло́жка', en: 'spoon' } },
  { char: 'М м', name: 'em', sound: 'm as in "map"', translit: 'm', example: { ru: 'ма́ма', en: 'mom' } },
  { char: 'Н н', name: 'en', sound: 'n as in "net"', translit: 'n', example: { ru: 'нос', en: 'nose' } },
  { char: 'О о', name: 'o', sound: 'o as in "more" (stressed); "a"-like unstressed', translit: 'o', example: { ru: 'окно́', en: 'window' } },
  { char: 'П п', name: 'pe', sound: 'p as in "pet"', translit: 'p', example: { ru: 'па́па', en: 'dad' } },
  { char: 'Р р', name: 'er', sound: 'rolled r', translit: 'r', example: { ru: 'рука́', en: 'hand/arm' } },
  { char: 'С с', name: 'es', sound: 's as in "sun"', translit: 's', example: { ru: 'суп', en: 'soup' } },
  { char: 'Т т', name: 'te', sound: 't as in "top"', translit: 't', example: { ru: 'там', en: 'there' } },
  { char: 'У у', name: 'u', sound: 'oo as in "boot"', translit: 'u', example: { ru: 'у́тро', en: 'morning' } },
  { char: 'Ф ф', name: 'ef', sound: 'f as in "fan"', translit: 'f', example: { ru: 'фо́то', en: 'photo' } },
  { char: 'Х х', name: 'kha', sound: 'ch as in Scottish "loch"', translit: 'kh', example: { ru: 'хлеб', en: 'bread' } },
  { char: 'Ц ц', name: 'tse', sound: 'ts as in "cats"', translit: 'ts', example: { ru: 'цена́', en: 'price' } },
  { char: 'Ч ч', name: 'che', sound: 'ch as in "chip"', translit: 'ch', example: { ru: 'час', en: 'hour' } },
  { char: 'Ш ш', name: 'sha', sound: 'sh as in "shop" (hard)', translit: 'sh', example: { ru: 'шко́ла', en: 'school' } },
  { char: 'Щ щ', name: 'shcha', sound: 'soft "sh", like "fresh sheets"', translit: 'shch', example: { ru: 'щи', en: 'cabbage soup' } },
  { char: 'Ъ ъ', name: 'tvyordy znak', sound: 'hard sign — no sound, hardens before vowel', translit: '"', example: { ru: 'объе́кт', en: 'object' } },
  { char: 'Ы ы', name: 'y', sound: 'rough "i", tongue pulled back', translit: 'y', example: { ru: 'сын', en: 'son' } },
  { char: 'Ь ь', name: 'myagky znak', sound: 'soft sign — no sound, softens preceding consonant', translit: '\'', example: { ru: 'день', en: 'day' } },
  { char: 'Э э', name: 'e', sound: 'e as in "met"', translit: 'e', example: { ru: 'э́то', en: 'this/that is' } },
  { char: 'Ю ю', name: 'yu', sound: 'yu as in "universe"', translit: 'yu', example: { ru: 'ю́бка', en: 'skirt' } },
  { char: 'Я я', name: 'ya', sound: 'ya as in "yard"', translit: 'ya', example: { ru: 'я', en: 'I' } },
];

// ===========================================================================
// CURRICULUM. Each level => { level, summary, units:[ { id, title, goal,
// lessons:[ lesson ] } ] }. A lesson => { id, title, cefr, grammarFocus,
// canDo, explanation, vocab, examples, dialogue, notes }.
// A1/A2 are fully authored; B1–C2 are outlines for on-demand expansion.
// ===========================================================================

const A1 = {
  level: 'A1',
  summary:
    'Absolute beginner. Read and write Cyrillic, greet people, introduce yourself, ' +
    'use present-tense verbs, grasp noun gender and the first cases (nominative, ' +
    'prepositional, accusative), count, and handle everyday survival situations.',
  units: [
    {
      id: 'a1-u1',
      title: 'Cyrillic & First Words',
      goal: 'Read and pronounce Cyrillic; say hello, goodbye, yes/no, thank you.',
      lessons: [
        {
          id: 'a1-u1-l1',
          title: 'The Cyrillic Alphabet',
          cefr: 'A1',
          grammarFocus: 'Letter–sound correspondence; stress and vowel reduction',
          canDo: ['I can recognize and pronounce the 33 Cyrillic letters.', 'I can sound out simple Russian words.'],
          explanation:
            'Russian uses the Cyrillic alphabet — 33 letters. Some look familiar and sound similar to English ' +
            '(А, К, М, Т, О), some are "false friends" that look familiar but sound different (В = v, Н = n, ' +
            'Р = r, С = s, У = oo), and some are entirely new (Ж, Ч, Ш, Щ, Ю, Я). Two letters, Ъ and Ь, make no ' +
            'sound of their own. Stress is strong and unpredictable, and it matters: unstressed О is pronounced ' +
            'like a short "a" (so молоко́ sounds like "ma-la-KO"). Learn to read first — everything else builds on it.',
          vocab: [
            { ru: 'да', en: 'yes', translit: 'da', ex: 'Да, коне́чно. — Yes, of course.' },
            { ru: 'нет', en: 'no', translit: 'nyet', ex: 'Нет, спаси́бо. — No, thank you.' },
            { ru: 'и', en: 'and', translit: 'i', ex: 'я и ты — you and I' },
            { ru: 'кот', en: 'cat', translit: 'kot', ex: 'Э́то кот. — This is a cat.' },
            { ru: 'дом', en: 'house/home', translit: 'dom', ex: 'мой дом — my house' },
          ],
          examples: [
            { ru: 'Э́то кот.', en: 'This is a cat.', translit: 'Eto kot.' },
            { ru: 'Э́то дом.', en: 'This is a house.', translit: 'Eto dom.' },
          ],
          dialogue: null,
          notes: 'Practice writing each letter. Use getAlphabet() for the full chart with examples.',
        },
        {
          id: 'a1-u1-l2',
          title: 'Greetings & Politeness',
          cefr: 'A1',
          grammarFocus: 'Formal vs. informal address (ты/вы); fixed greeting phrases',
          canDo: ['I can greet and say goodbye formally and informally.', 'I can say please, thank you, and sorry.'],
          explanation:
            'Russian distinguishes informal "ты" (one friend/child) from formal/plural "вы" (a stranger, an older ' +
            'person, or a group). Greetings follow this split: "Приве́т!" (informal hi) vs. "Здра́вствуйте!" (formal ' +
            'hello — the first "в" is silent). Time-of-day greetings ("До́брое у́тро", "До́брый день", "До́брый ' +
            'ве́чер") work in any register. Politeness words come up constantly: "пожа́луйста" (please / you\'re ' +
            'welcome), "спаси́бо" (thank you), "извини́те" (excuse me, formal).',
          vocab: [
            { ru: 'приве́т', en: 'hi (informal)', translit: 'privet', ex: 'Приве́т, Анна! — Hi, Anna!' },
            { ru: 'здра́вствуйте', en: 'hello (formal)', translit: 'zdravstvuyte', ex: 'Здра́вствуйте! — Hello!' },
            { ru: 'до свида́ния', en: 'goodbye', translit: 'do svidaniya', ex: 'До свида́ния! — Goodbye!' },
            { ru: 'пока́', en: 'bye (informal)', translit: 'poka', ex: 'Пока́! — Bye!' },
            { ru: 'спаси́бо', en: 'thank you', translit: 'spasibo', ex: 'Большо́е спаси́бо. — Thank you very much.' },
            { ru: 'пожа́луйста', en: 'please / you\'re welcome', translit: 'pozhaluysta', ex: 'Да, пожа́луйста. — Yes, please.' },
            { ru: 'извини́те', en: 'excuse me / sorry (formal)', translit: 'izvinite', ex: 'Извини́те! — Excuse me!' },
            { ru: 'до́брое у́тро', en: 'good morning', translit: 'dobroye utro', ex: 'До́брое у́тро! — Good morning!' },
          ],
          examples: [
            { ru: 'Здра́вствуйте! Как дела́?', en: 'Hello! How are you?', translit: 'Zdravstvuyte! Kak dela?' },
            { ru: 'Спаси́бо большо́е! — Пожа́луйста.', en: 'Thank you very much! — You\'re welcome.', translit: 'Spasibo bolshoye! — Pozhaluysta.' },
          ],
          dialogue: [
            { ru: '— Приве́т! Как дела́?', en: '— Hi! How are you?' },
            { ru: '— Хорошо́, спаси́бо! А у тебя́?', en: '— Good, thanks! And you?' },
            { ru: '— То́же хорошо́. Пока́!', en: '— Also good. Bye!' },
          ],
          notes: 'Use вы with strangers and elders until invited to use ты ("дава́й на ты").',
        },
      ],
    },
    {
      id: 'a1-u2',
      title: 'Me & You',
      goal: 'Introduce yourself, ask names, use pronouns and the verb "to be".',
      lessons: [
        {
          id: 'a1-u2-l1',
          title: 'Personal Pronouns & "to be"',
          cefr: 'A1',
          grammarFocus: 'Pronouns я/ты/он/она́/оно́/мы/вы/они́; быть (to be) dropped in the present',
          canDo: ['I can use subject pronouns.', 'I can make simple "X is Y" sentences without a verb.'],
          explanation:
            'The subject pronouns are: я (I), ты (you, informal), он (he/it-masc), она́ (she/it-fem), оно́ (it-neut), ' +
            'мы (we), вы (you formal/plural), они́ (they). The crucial beginner rule: Russian DROPS the verb "to be" ' +
            'in the present tense. "I am a student" is simply "Я студе́нт" — literally "I student." The dash in ' +
            'writing ("Москва́ — го́род") stands in for "is". The verb быть does exist but mainly appears in the ' +
            'past (был/была́/бы́ло) and future (бу́ду/бу́дешь…), which come later.',
          vocab: [
            { ru: 'я', en: 'I', translit: 'ya', ex: 'Я студе́нт. — I am a student.' },
            { ru: 'ты', en: 'you (informal)', translit: 'ty', ex: 'Ты до́ма? — Are you home?' },
            { ru: 'он', en: 'he / it (masc.)', translit: 'on', ex: 'Он врач. — He is a doctor.' },
            { ru: 'она́', en: 'she / it (fem.)', translit: 'ona', ex: 'Она́ учи́тель. — She is a teacher.' },
            { ru: 'мы', en: 'we', translit: 'my', ex: 'Мы друзья́. — We are friends.' },
            { ru: 'вы', en: 'you (formal/plural)', translit: 'vy', ex: 'Вы гото́вы? — Are you ready?' },
            { ru: 'они́', en: 'they', translit: 'oni', ex: 'Они́ до́ма. — They are home.' },
          ],
          examples: [
            { ru: 'Я студе́нт.', en: 'I am a student.', translit: 'Ya student.' },
            { ru: 'Она́ из Москвы́.', en: 'She is from Moscow.', translit: 'Ona iz Moskvy.' },
            { ru: 'Москва́ — большо́й го́род.', en: 'Moscow is a big city.', translit: 'Moskva — bolshoy gorod.' },
          ],
          dialogue: null,
          notes: 'No "am/is/are" in the present. The dash replaces "is" between two nouns.',
        },
        {
          id: 'a1-u2-l2',
          title: 'Introducing Yourself',
          cefr: 'A1',
          grammarFocus: 'меня́ зову́т construction; asking and giving your name',
          canDo: ['I can ask and tell someone my name.', 'I can ask where someone is from and say where I am from.'],
          explanation:
            'To give your name Russians say "Меня́ зову́т Анна" — literally "(They) call me Anna." To ask, use ' +
            '"Как вас зову́т?" (formal) or "Как тебя́ зову́т?" (informal). To say where you are from: "Я из ' +
            'Аме́рики" (I am from America) — note из + the genitive case form, which you will meet properly later; ' +
            'for now learn these as set phrases. "Очень прия́тно!" (Nice to meet you) is the standard reply.',
          vocab: [
            { ru: 'меня́ зову́т…', en: 'my name is… (lit. they call me)', translit: 'menya zovut', ex: 'Меня́ зову́т Ива́н. — My name is Ivan.' },
            { ru: 'как вас зову́т?', en: 'what is your name? (formal)', translit: 'kak vas zovut', ex: '' },
            { ru: 'о́чень прия́тно', en: 'nice to meet you', translit: 'ochen priyatno', ex: 'О́чень прия́тно! — Nice to meet you!' },
            { ru: 'я из…', en: 'I am from…', translit: 'ya iz', ex: 'Я из Кана́ды. — I am from Canada.' },
            { ru: 'и́мя', en: 'name (first name)', translit: 'imya', ex: 'Как твоё и́мя? — What\'s your (first) name?' },
            { ru: 'отку́да', en: 'from where', translit: 'otkuda', ex: 'Отку́да вы? — Where are you from?' },
          ],
          examples: [
            { ru: 'Меня́ зову́т Мари́я. А вас?', en: 'My name is Maria. And you?', translit: 'Menya zovut Mariya. A vas?' },
            { ru: 'Отку́да ты? — Я из Ло́ндона.', en: 'Where are you from? — I\'m from London.', translit: 'Otkuda ty? — Ya iz Londona.' },
          ],
          dialogue: [
            { ru: '— Здра́вствуйте! Как вас зову́т?', en: '— Hello! What is your name?' },
            { ru: '— Меня́ зову́т Питер. А вас?', en: '— My name is Peter. And you?' },
            { ru: '— Анна. О́чень прия́тно!', en: '— Anna. Nice to meet you!' },
          ],
          notes: 'зову́т is literally "they call"; you do not change it for who is speaking.',
        },
      ],
    },
    {
      id: 'a1-u3',
      title: 'Nouns: Gender & "This is"',
      goal: 'Recognize noun gender, point things out, use это and possessives.',
      lessons: [
        {
          id: 'a1-u3-l1',
          title: 'Gender of Nouns',
          cefr: 'A1',
          grammarFocus: 'Three genders from the noun ending; это as "this is"',
          canDo: ['I can tell a noun\'s gender from its ending.', 'I can say "this/that is …".'],
          explanation:
            'Every Russian noun is masculine, feminine, or neuter — and usually the ENDING tells you which. ' +
            'Consonant or -й → masculine (стол, чай, музе́й). -а / -я → feminine (ма́ма, неде́ля). -о / -е → neuter ' +
            '(окно́, мо́ре). Nouns ending in -ь can be either, so you memorize those. Gender drives almost ' +
            'everything later (adjectives, the past tense, pronouns), so anchor it now. "Э́то" is an all-purpose ' +
            'pointer meaning "this is / that is / these are", and it never changes: "Э́то стол", "Э́то ма́ма", ' +
            '"Э́то окно́".',
          vocab: [
            { ru: 'стол', en: 'table (masc.)', translit: 'stol', ex: 'Э́то стол. — This is a table.' },
            { ru: 'кни́га', en: 'book (fem.)', translit: 'kniga', ex: 'Э́то кни́га. — This is a book.' },
            { ru: 'окно́', en: 'window (neut.)', translit: 'okno', ex: 'Э́то окно́. — This is a window.' },
            { ru: 'дверь', en: 'door (fem., soft sign)', translit: 'dver', ex: 'Э́то дверь. — This is a door.' },
            { ru: 'чай', en: 'tea (masc., -й)', translit: 'chay', ex: 'Э́то чай. — This is tea.' },
            { ru: 'мо́ре', en: 'sea (neut.)', translit: 'more', ex: 'Э́то мо́ре. — This is the sea.' },
            { ru: 'студе́нт', en: 'student (masc.)', translit: 'student', ex: 'Он студе́нт. — He is a student.' },
            { ru: 'студе́нтка', en: 'student (fem.)', translit: 'studentka', ex: 'Она́ студе́нтка. — She is a student.' },
          ],
          examples: [
            { ru: 'Э́то стол, а э́то стул.', en: 'This is a table, and this is a chair.', translit: 'Eto stol, a eto stul.' },
            { ru: 'Кни́га — она́. Окно́ — оно́.', en: 'The book — "she". The window — "it".', translit: 'Kniga — ona. Okno — ono.' },
          ],
          dialogue: null,
          notes: 'Soft-sign nouns (-ь) must be learned with their gender; дверь is feminine, день is masculine.',
        },
        {
          id: 'a1-u3-l2',
          title: 'My, Your & Adjective Agreement',
          cefr: 'A1',
          grammarFocus: 'Possessives мой/моя́/моё/мои́; adjectives agree with gender',
          canDo: ['I can say "my / your" with the right gender.', 'I can describe a noun with a basic adjective.'],
          explanation:
            'Possessives and adjectives must MATCH the noun\'s gender. "My": мой (masc.), моя́ (fem.), моё ' +
            '(neut.), мои́ (plural) — so мой брат, моя́ сестра́, моё окно́, мои́ друзья́. "Your" (informal) works the ' +
            'same: твой / твоя́ / твоё / твои́. Adjectives take gendered endings too: -ый/-ой (masc.), -ая (fem.), ' +
            '-ое (neut.): но́вый дом, но́вая маши́на, но́вое окно́. This agreement is the backbone of Russian — once ' +
            'gender is automatic, agreement follows.',
          vocab: [
            { ru: 'мой / моя́ / моё', en: 'my', translit: 'moy / moya / moyo', ex: 'мой друг — my friend' },
            { ru: 'твой / твоя́ / твоё', en: 'your (informal)', translit: 'tvoy / tvoya / tvoyo', ex: 'твоя́ кни́га — your book' },
            { ru: 'наш / на́ша', en: 'our', translit: 'nash / nasha', ex: 'наш дом — our house' },
            { ru: 'но́вый', en: 'new', translit: 'novy', ex: 'но́вый телефо́н — a new phone' },
            { ru: 'ста́рый', en: 'old', translit: 'stary', ex: 'ста́рый го́род — an old city' },
            { ru: 'большо́й', en: 'big', translit: 'bolshoy', ex: 'большо́й дом — a big house' },
            { ru: 'ма́ленький', en: 'small', translit: 'malenky', ex: 'ма́ленькая кварти́ра — a small apartment' },
            { ru: 'хоро́ший', en: 'good', translit: 'khoroshy', ex: 'хоро́ший день — a good day' },
          ],
          examples: [
            { ru: 'Э́то моя́ но́вая маши́на.', en: 'This is my new car.', translit: 'Eto moya novaya mashina.' },
            { ru: 'Мой брат — хоро́ший студе́нт.', en: 'My brother is a good student.', translit: 'Moy brat — khoroshy student.' },
          ],
          dialogue: null,
          notes: 'Adjective + possessive both bow to the noun\'s gender — change the noun, change them.',
        },
      ],
    },
    {
      id: 'a1-u4',
      title: 'Verbs in the Present',
      goal: 'Conjugate regular verbs and talk about everyday actions.',
      lessons: [
        {
          id: 'a1-u4-l1',
          title: 'Present Tense: First Conjugation (-ть)',
          cefr: 'A1',
          grammarFocus: 'First-conjugation endings -ю/-ешь/-ет/-ем/-ете/-ют (e.g. рабо́тать, чита́ть)',
          canDo: ['I can conjugate common -ать verbs in the present.', 'I can say what I and others do.'],
          explanation:
            'Russian verbs change their ending for the subject — there is no separate "I/you/he". Most everyday ' +
            'verbs follow the FIRST conjugation. Take рабо́тать (to work): drop -ть and add я рабо́та-ю, ты ' +
            'рабо́та-ешь, он рабо́та-ет, мы рабо́та-ем, вы рабо́та-ете, они́ рабо́та-ют. The same pattern fits ' +
            'чита́ть (read), де́лать (do), понима́ть (understand), знать (know). Russian present tense covers both ' +
            '"I work" and "I am working" — there is no separate continuous form.',
          vocab: [
            { ru: 'рабо́тать', en: 'to work', translit: 'rabotat', ex: 'Я рабо́таю до́ма. — I work at home.' },
            { ru: 'чита́ть', en: 'to read', translit: 'chitat', ex: 'Она́ чита́ет кни́гу. — She is reading a book.' },
            { ru: 'де́лать', en: 'to do / make', translit: 'delat', ex: 'Что ты де́лаешь? — What are you doing?' },
            { ru: 'знать', en: 'to know', translit: 'znat', ex: 'Я зна́ю. — I know.' },
            { ru: 'понима́ть', en: 'to understand', translit: 'ponimat', ex: 'Я не понима́ю. — I don\'t understand.' },
            { ru: 'ду́мать', en: 'to think', translit: 'dumat', ex: 'Я ду́маю, да. — I think so.' },
            { ru: 'слу́шать', en: 'to listen', translit: 'slushat', ex: 'Мы слу́шаем му́зыку. — We are listening to music.' },
          ],
          examples: [
            { ru: 'Я рабо́таю, а ты отдыха́ешь.', en: 'I am working and you are resting.', translit: 'Ya rabotayu, a ty otdykhayesh.' },
            { ru: 'Они́ чита́ют и слу́шают му́зыку.', en: 'They read and listen to music.', translit: 'Oni chitayut i slushayut muzyku.' },
          ],
          dialogue: null,
          notes: 'Negate with "не" before the verb: Я не зна́ю — I don\'t know.',
        },
        {
          id: 'a1-u4-l2',
          title: 'Second Conjugation & Key Irregulars',
          cefr: 'A1',
          grammarFocus: 'Second-conjugation -ишь/-ит/-ят (говори́ть); irregular хоте́ть, мочь',
          canDo: ['I can conjugate -ить verbs like говори́ть.', 'I can say I want / can / speak a language.'],
          explanation:
            'SECOND-conjugation verbs (mostly -ить) take -ю/-у, -ишь, -ит, -им, -ите, -ат/-ят. Example говори́ть ' +
            '(to speak): я говорю́, ты говори́шь, он говори́т, мы говори́м, вы говори́те, они́ говоря́т. Two ' +
            'super-common verbs are irregular and worth memorizing whole: хоте́ть (to want) — хочу́, хо́чешь, ' +
            'хо́чет, хоти́м, хоти́те, хотя́т; and мочь (can) — могу́, мо́жешь, мо́жет, мо́жем, мо́жете, мо́гут. ' +
            'Use "по-ру́сски / по-англи́йски" with говори́ть to say which language you speak.',
          vocab: [
            { ru: 'говори́ть', en: 'to speak / say', translit: 'govorit', ex: 'Я говорю́ по-ру́сски. — I speak Russian.' },
            { ru: 'люби́ть', en: 'to love / like', translit: 'lyubit', ex: 'Я люблю́ ко́фе. — I love coffee.' },
            { ru: 'хоте́ть', en: 'to want (irreg.)', translit: 'khotet', ex: 'Я хочу́ есть. — I want to eat (I\'m hungry).' },
            { ru: 'мочь', en: 'can / to be able (irreg.)', translit: 'moch', ex: 'Я могу́ помо́чь. — I can help.' },
            { ru: 'жить', en: 'to live', translit: 'zhit', ex: 'Я живу́ в Москве́. — I live in Moscow.' },
            { ru: 'по-ру́сски', en: 'in Russian', translit: 'po-russki', ex: 'Говори́те по-ру́сски? — Do you speak Russian?' },
            { ru: 'немно́го', en: 'a little', translit: 'nemnogo', ex: 'Я немно́го говорю́. — I speak a little.' },
          ],
          examples: [
            { ru: 'Вы говори́те по-англи́йски? — Да, немно́го.', en: 'Do you speak English? — Yes, a little.', translit: 'Vy govorite po-angliyski? — Da, nemnogo.' },
            { ru: 'Я хочу́ ко́фе, но не могу́ сейча́с.', en: 'I want coffee but I can\'t right now.', translit: 'Ya khochu kofe, no ne mogu seychas.' },
          ],
          dialogue: null,
          notes: 'люблю́ has a "л" inserted in the "я" form (л-mutation) — это normal for -ить verbs with б/в/м/п/ф stems.',
        },
      ],
    },
    {
      id: 'a1-u5',
      title: 'First Cases: Where & What',
      goal: 'Use the prepositional case for location and the accusative for direct objects.',
      lessons: [
        {
          id: 'a1-u5-l1',
          title: 'Prepositional Case: Location',
          cefr: 'A1',
          grammarFocus: 'в/на + prepositional ending -е for "in / at"',
          canDo: ['I can say where something or someone is.', 'I can answer "где?" (where?).'],
          explanation:
            'Russian marks meaning with CASES — endings that show a noun\'s role. The first you need is the ' +
            'PREPOSITIONAL case, used after в (in) and на (on/at) to say location. The basic ending is -е: Москва́ ' +
            '→ в Москве́, рабо́та → на рабо́те, теа́тр → в теа́тре. Use в for enclosed spaces/cities/countries and ' +
            'на for "open" surfaces, events and a fixed list (на рабо́те, на по́чте, на ста́нции). It answers the ' +
            'question где? (where?).',
          vocab: [
            { ru: 'где', en: 'where', translit: 'gde', ex: 'Где ты? — Where are you?' },
            { ru: 'в', en: 'in (+ prep.)', translit: 'v', ex: 'в Москве́ — in Moscow' },
            { ru: 'на', en: 'on / at (+ prep.)', translit: 'na', ex: 'на рабо́те — at work' },
            { ru: 'до́ма', en: 'at home', translit: 'doma', ex: 'Я до́ма. — I am home.' },
            { ru: 'рабо́та', en: 'work', translit: 'rabota', ex: 'Он на рабо́те. — He is at work.' },
            { ru: 'го́род', en: 'city', translit: 'gorod', ex: 'в го́роде — in the city' },
            { ru: 'магази́н', en: 'shop / store', translit: 'magazin', ex: 'в магази́не — in the store' },
            { ru: 'университе́т', en: 'university', translit: 'universitet', ex: 'в университе́те — at the university' },
          ],
          examples: [
            { ru: 'Я живу́ в го́роде.', en: 'I live in the city.', translit: 'Ya zhivu v gorode.' },
            { ru: 'Ма́ма на рабо́те, а па́па до́ма.', en: 'Mom is at work and dad is home.', translit: 'Mama na rabote, a papa doma.' },
          ],
          dialogue: [
            { ru: '— Где Анна?', en: '— Where is Anna?' },
            { ru: '— Она́ в университе́те.', en: '— She is at the university.' },
          ],
          notes: 'до́ма (at home) and домо́й (homeward) are special adverbs — no preposition needed.',
        },
        {
          id: 'a1-u5-l2',
          title: 'Accusative Case: The Direct Object',
          cefr: 'A1',
          grammarFocus: 'Accusative of feminine -а→-у; inanimate masc./neuter unchanged',
          canDo: ['I can say what I read, want, love, or buy.', 'I can use the accusative for the object of a verb.'],
          explanation:
            'The ACCUSATIVE marks the direct object — the thing the action is done to. Good news: for inanimate ' +
            'masculine and all neuter nouns it looks exactly like the dictionary (nominative) form — Я чита́ю ' +
            'журна́л, Я люблю́ мо́ре. The main change is FEMININE -а → -у / -я → -ю: кни́га → Я чита́ю кни́гу; ' +
            'Москва́ → Я люблю́ Москву́. (Animate masculine nouns and plurals come later.) Verbs that take a direct ' +
            'object: чита́ть, люби́ть, хоте́ть, покупа́ть, смотре́ть.',
          vocab: [
            { ru: 'покупа́ть', en: 'to buy', translit: 'pokupat', ex: 'Я покупа́ю газе́ту. — I am buying a newspaper.' },
            { ru: 'смотре́ть', en: 'to watch / look', translit: 'smotret', ex: 'Я смотрю́ фильм. — I am watching a film.' },
            { ru: 'газе́та', en: 'newspaper', translit: 'gazeta', ex: 'Я чита́ю газе́ту. — I read a newspaper.' },
            { ru: 'му́зыка', en: 'music', translit: 'muzyka', ex: 'Я люблю́ му́зыку. — I love music.' },
            { ru: 'вода́', en: 'water', translit: 'voda', ex: 'Я хочу́ во́ду. — I want water.' },
            { ru: 'фильм', en: 'film / movie', translit: 'film', ex: 'Мы смо́трим фильм. — We are watching a movie.' },
            { ru: 'что', en: 'what', translit: 'chto', ex: 'Что ты чита́ешь? — What are you reading?' },
          ],
          examples: [
            { ru: 'Я чита́ю интере́сную кни́гу.', en: 'I am reading an interesting book.', translit: 'Ya chitayu interesnuyu knigu.' },
            { ru: 'Она́ лю́бит ру́сскую му́зыку.', en: 'She loves Russian music.', translit: 'Ona lyubit russkuyu muzyku.' },
          ],
          dialogue: null,
          notes: 'Feminine adjectives shift too: но́вую кни́гу, ру́сскую му́зыку (-ая → -ую).',
        },
      ],
    },
    {
      id: 'a1-u6',
      title: 'Numbers, Family & Survival',
      goal: 'Count, talk about family, and handle a café/shop.',
      lessons: [
        {
          id: 'a1-u6-l1',
          title: 'Numbers 0–20 & Family',
          cefr: 'A1',
          grammarFocus: 'Cardinal numbers; у меня́ есть for "I have"',
          canDo: ['I can count from 0 to 20.', 'I can name family members and say "I have…".'],
          explanation:
            'Learn 0–10 first (ноль, оди́н, два, три, четы́ре, пять, шесть, семь, во́семь, де́вять, де́сять), then ' +
            '11–20 which mostly add -надцать (оди́ннадцать, двена́дцать… два́дцать). To say you HAVE something, ' +
            'Russians use "у меня́ есть" + nominative: "У меня́ есть брат" (I have a brother). The owner goes in ' +
            'the form у меня́ / у тебя́ / у него́ / у неё / у нас / у вас / у них.',
          vocab: [
            { ru: 'оди́н, два, три', en: 'one, two, three', translit: 'odin, dva, tri', ex: 'У меня́ два бра́та. — I have two brothers.' },
            { ru: 'четы́ре, пять', en: 'four, five', translit: 'chetyre, pyat', ex: 'пять рубле́й — five rubles' },
            { ru: 'де́сять', en: 'ten', translit: 'desyat', ex: 'де́сять мину́т — ten minutes' },
            { ru: 'семья́', en: 'family', translit: 'semya', ex: 'У меня́ больша́я семья́. — I have a big family.' },
            { ru: 'мать / ма́ма', en: 'mother / mom', translit: 'mat / mama', ex: 'Моя́ ма́ма врач. — My mom is a doctor.' },
            { ru: 'оте́ц / па́па', en: 'father / dad', translit: 'otets / papa', ex: 'Мой па́па — инжене́р. — My dad is an engineer.' },
            { ru: 'брат', en: 'brother', translit: 'brat', ex: 'У меня́ есть брат. — I have a brother.' },
            { ru: 'сестра́', en: 'sister', translit: 'sestra', ex: 'Моя́ сестра́ студе́нтка. — My sister is a student.' },
            { ru: 'у меня́ есть', en: 'I have', translit: 'u menya yest', ex: 'У меня́ есть соба́ка. — I have a dog.' },
          ],
          examples: [
            { ru: 'У меня́ есть брат и сестра́.', en: 'I have a brother and a sister.', translit: 'U menya yest brat i sestra.' },
            { ru: 'В семье́ пять челове́к.', en: 'There are five people in the family.', translit: 'V semye pyat chelovek.' },
          ],
          dialogue: null,
          notes: 'After 2–4 use the genitive singular (два бра́та); after 5+ the genitive plural (пять бра́тьев) — a B-level deep-dive.',
        },
        {
          id: 'a1-u6-l2',
          title: 'At the Café: Ordering',
          cefr: 'A1',
          grammarFocus: 'Polite requests with "Я хочу́… / Мо́жно…?"; food & drink vocab',
          canDo: ['I can order food and drink politely.', 'I can ask the price and pay.'],
          explanation:
            'To order, use "Я хочу́…" (I want) or the softer "Мо́жно…?" (May I have…?) plus the accusative: ' +
            '"Мо́жно ко́фе, пожа́луйста?" To ask the price: "Ско́лько сто́ит?" (How much does it cost?). "Счёт, ' +
            'пожа́луйста" asks for the bill. These survival phrases let you function in a café from day one even ' +
            'before the grammar is solid.',
          vocab: [
            { ru: 'ко́фе', en: 'coffee', translit: 'kofe', ex: 'Мо́жно ко́фе? — Can I have a coffee?' },
            { ru: 'чай', en: 'tea', translit: 'chay', ex: 'Я хочу́ чай. — I want tea.' },
            { ru: 'вода́', en: 'water', translit: 'voda', ex: 'Мо́жно во́ду, пожа́луйста. — Some water, please.' },
            { ru: 'хлеб', en: 'bread', translit: 'khleb', ex: 'хлеб и сыр — bread and cheese' },
            { ru: 'суп', en: 'soup', translit: 'sup', ex: 'Я бу́ду суп. — I\'ll have the soup.' },
            { ru: 'ско́лько сто́ит?', en: 'how much is it?', translit: 'skolko stoit', ex: 'Ско́лько сто́ит ко́фе? — How much is the coffee?' },
            { ru: 'счёт', en: 'the bill', translit: 'schyot', ex: 'Счёт, пожа́луйста. — The bill, please.' },
            { ru: 'мо́жно', en: 'may I / is it allowed', translit: 'mozhno', ex: 'Мо́жно меню́? — Can I have the menu?' },
          ],
          examples: [
            { ru: 'Мо́жно чай и хлеб, пожа́луйста?', en: 'May I have tea and bread, please?', translit: 'Mozhno chay i khleb, pozhaluysta?' },
            { ru: 'Ско́лько сто́ит? — Две́сти рубле́й.', en: 'How much is it? — Two hundred rubles.', translit: 'Skolko stoit? — Dvesti rubley.' },
          ],
          dialogue: [
            { ru: '— Здра́вствуйте! Что вы хоти́те?', en: '— Hello! What would you like?' },
            { ru: '— Мо́жно ко́фе и суп, пожа́луйста.', en: '— Can I have a coffee and soup, please.' },
            { ru: '— Коне́чно. Что-нибу́дь ещё?', en: '— Of course. Anything else?' },
          ],
          notes: '"Я бу́ду…" (lit. "I will have…") is a natural way to order in a restaurant.',
        },
      ],
    },
  ],
};

const A2 = {
  level: 'A2',
  summary:
    'Elementary. Talk about the past and future, tell time and dates, use the ' +
    'remaining cases (genitive, dative, instrumental), describe routines, give ' +
    'directions, and meet verb aspect for the first time.',
  units: [
    {
      id: 'a2-u1',
      title: 'The Past Tense',
      goal: 'Talk about what happened using gendered past-tense forms.',
      lessons: [
        {
          id: 'a2-u1-l1',
          title: 'Forming the Past Tense',
          cefr: 'A2',
          grammarFocus: 'Past tense -л/-ла/-ло/-ли agreeing with the SUBJECT\'s gender/number',
          canDo: ['I can say what I and others did.', 'I can use был/была́ for "was".'],
          explanation:
            'The past tense is wonderfully simple: drop the infinitive -ть and add -л for a masculine subject, ' +
            '-ла for feminine, -ло for neuter, -ли for plural. Crucially, it agrees with the SUBJECT\'S gender, ' +
            'not the speaker\'s: a woman says "Я чита́ла", a man "Я чита́л". The verb быть (to be) appears in the ' +
            'past as был / была́ / бы́ло / бы́ли — "Я был до́ма" (I was home). Negation: "Меня́ не́ было до́ма."',
          vocab: [
            { ru: 'был / была́ / бы́ли', en: 'was / were', translit: 'byl / byla / byli', ex: 'Я был на рабо́те. — I was at work.' },
            { ru: 'чита́л / чита́ла', en: 'read (past)', translit: 'chital / chitala', ex: 'Она́ чита́ла кни́гу. — She was reading a book.' },
            { ru: 'вчера́', en: 'yesterday', translit: 'vchera', ex: 'Вчера́ я рабо́тал. — Yesterday I worked.' },
            { ru: 'ра́ньше', en: 'earlier / before', translit: 'ranshe', ex: 'Ра́ньше я жил в Ки́еве. — I used to live in Kyiv.' },
            { ru: 'у́тром', en: 'in the morning', translit: 'utrom', ex: 'У́тром мы гуля́ли. — In the morning we walked.' },
            { ru: 'де́лал / де́лала', en: 'did (past)', translit: 'delal / delala', ex: 'Что ты де́лал вчера́? — What did you do yesterday?' },
          ],
          examples: [
            { ru: 'Вчера́ я был до́ма и чита́л.', en: 'Yesterday I was home and read.', translit: 'Vchera ya byl doma i chital.' },
            { ru: 'Она́ была́ в Москве́ ле́том.', en: 'She was in Moscow in the summer.', translit: 'Ona byla v Moskve letom.' },
          ],
          dialogue: null,
          notes: 'The past tense ignores person — only gender (singular) and number matter.',
        },
        {
          id: 'a2-u1-l2',
          title: 'Verb Aspect: Imperfective vs. Perfective',
          cefr: 'A2',
          grammarFocus: 'The aspect pair: process/repeated (imperfective) vs. completed result (perfective)',
          canDo: ['I can choose the right aspect in the past.', 'I can distinguish "was doing" from "did/finished".'],
          explanation:
            'Russian verbs come in PAIRS that differ in aspect. The IMPERFECTIVE describes a process, repetition, ' +
            'or general fact (чита́ть, де́лать, писа́ть); the PERFECTIVE stresses a single COMPLETED result, often ' +
            'with a prefix (прочита́ть, сде́лать, написа́ть). "Я чита́л кни́гу" = I was reading / used to read it; ' +
            '"Я прочита́л кни́гу" = I read it (finished, all of it). Aspect is the single most important Russian ' +
            'verb concept — we keep returning to it. In the present tense only the imperfective exists; the ' +
            'perfective in present form actually means the FUTURE.',
          vocab: [
            { ru: 'чита́ть / прочита́ть', en: 'to read (impf./pf.)', translit: 'chitat / prochitat', ex: 'Я прочита́л всю кни́гу. — I read the whole book.' },
            { ru: 'де́лать / сде́лать', en: 'to do (impf./pf.)', translit: 'delat / sdelat', ex: 'Я сде́лал дома́шнее зада́ние. — I did the homework.' },
            { ru: 'писа́ть / написа́ть', en: 'to write (impf./pf.)', translit: 'pisat / napisat', ex: 'Я написа́л письмо́. — I wrote a letter.' },
            { ru: 'смотре́ть / посмотре́ть', en: 'to watch (impf./pf.)', translit: 'smotret / posmotret', ex: 'Мы посмотре́ли фильм. — We watched the film.' },
            { ru: 'уже́', en: 'already', translit: 'uzhe', ex: 'Я уже́ сде́лал. — I already did it.' },
            { ru: 'ещё', en: 'still / yet', translit: 'eshchyo', ex: 'Я ещё чита́ю. — I am still reading.' },
          ],
          examples: [
            { ru: 'Я до́лго писа́л письмо́ и наконе́ц написа́л его́.', en: 'I wrote the letter for a long time and finally finished it.', translit: 'Ya dolgo pisal pismo i nakonets napisal ego.' },
            { ru: 'Ка́ждый день я де́лаю заря́дку.', en: 'Every day I do exercises.', translit: 'Kazhdy den ya delayu zaryadku.' },
          ],
          dialogue: null,
          notes: 'Rule of thumb: process/habit → imperfective; single finished result → perfective. Deep-dived again at B1.',
        },
      ],
    },
    {
      id: 'a2-u2',
      title: 'The Future & Telling Time',
      goal: 'Make plans, tell time, and talk about days and dates.',
      lessons: [
        {
          id: 'a2-u2-l1',
          title: 'The Future Tense',
          cefr: 'A2',
          grammarFocus: 'Compound future (бу́ду + imperfective) vs. simple future (perfective present)',
          canDo: ['I can say what I will do.', 'I can make plans for tomorrow.'],
          explanation:
            'There are two futures, and aspect decides which. For an ongoing/repeated future action use the ' +
            'COMPOUND future: бу́ду / бу́дешь / бу́дет / бу́дем / бу́дете / бу́дут + the IMPERFECTIVE infinitive — ' +
            '"За́втра я бу́ду рабо́тать." For a single completed future action use the SIMPLE future: just ' +
            'conjugate the PERFECTIVE verb in present-tense form — "Я прочита́ю кни́гу за́втра" (I will read the ' +
            'book tomorrow). Same endings you already know, but a perfective stem points to the future.',
          vocab: [
            { ru: 'бу́ду / бу́дешь', en: 'will (auxiliary)', translit: 'budu / budesh', ex: 'Я бу́ду до́ма. — I will be home.' },
            { ru: 'за́втра', en: 'tomorrow', translit: 'zavtra', ex: 'За́втра бу́дет дождь. — It will rain tomorrow.' },
            { ru: 'по́сле', en: 'after', translit: 'posle', ex: 'по́сле рабо́ты — after work' },
            { ru: 'пото́м', en: 'then / later', translit: 'potom', ex: 'Снача́ла поедим, пото́м пойдём. — First we\'ll eat, then go.' },
            { ru: 'план', en: 'plan', translit: 'plan', ex: 'Каки́е пла́ны? — What are the plans?' },
            { ru: 'встре́тить(ся)', en: 'to meet (pf.)', translit: 'vstretit(sya)', ex: 'Мы встре́тимся в семь. — We\'ll meet at seven.' },
          ],
          examples: [
            { ru: 'За́втра я бу́ду учи́ть ру́сский язы́к.', en: 'Tomorrow I will study Russian.', translit: 'Zavtra ya budu uchit russky yazyk.' },
            { ru: 'Я напишу́ тебе́ ве́чером.', en: 'I will write to you in the evening.', translit: 'Ya napishu tebe vecherom.' },
          ],
          dialogue: null,
          notes: 'Imperfective future = бу́ду + infinitive. Perfective future = conjugate the perfective directly.',
        },
        {
          id: 'a2-u2-l2',
          title: 'Telling Time, Days & Dates',
          cefr: 'A2',
          grammarFocus: 'Кото́рый час?; в + accusative for clock time; days of the week',
          canDo: ['I can ask and tell the time.', 'I can name days of the week and say when something happens.'],
          explanation:
            'Ask the time with "Кото́рый час?" or "Ско́лько вре́мени?". On the hour: "сейча́с три часа́" (it\'s ' +
            'three o\'clock) — note час / часа́ / часо́в change with the number (1 час, 2–4 часа́, 5+ часо́в). To ' +
            'say AT a time use в + accusative: "в три часа́" (at three). Days of the week: понеде́льник, вто́рник, ' +
            'среда́, четве́рг, пя́тница, суббо́та, воскресе́нье; "on Monday" = в понеде́льник.',
          vocab: [
            { ru: 'кото́рый час?', en: 'what time is it?', translit: 'kotory chas', ex: 'Кото́рый час? — Три часа́.' },
            { ru: 'час / часы́', en: 'hour / clock', translit: 'chas / chasy', ex: 'два часа́ — two o\'clock' },
            { ru: 'мину́та', en: 'minute', translit: 'minuta', ex: 'де́сять мину́т — ten minutes' },
            { ru: 'понеде́льник', en: 'Monday', translit: 'ponedelnik', ex: 'в понеде́льник — on Monday' },
            { ru: 'суббо́та', en: 'Saturday', translit: 'subbota', ex: 'в суббо́ту — on Saturday' },
            { ru: 'неде́ля', en: 'week', translit: 'nedelya', ex: 'на э́той неде́ле — this week' },
            { ru: 'сего́дня', en: 'today', translit: 'segodnya', ex: 'Сего́дня вто́рник. — Today is Tuesday.' },
            { ru: 'когда́', en: 'when', translit: 'kogda', ex: 'Когда́ ты придёшь? — When will you come?' },
          ],
          examples: [
            { ru: 'Сейча́с полови́на седьмо́го.', en: 'It is half past six.', translit: 'Seychas polovina sedmogo.' },
            { ru: 'В суббо́ту мы идём в кино́.', en: 'On Saturday we are going to the cinema.', translit: 'V subbotu my idyom v kino.' },
          ],
          dialogue: null,
          notes: '"Half past" uses the NEXT hour\'s ordinal in genitive: полови́на седьмо́го = "half of the seventh" = 6:30.',
        },
      ],
    },
    {
      id: 'a2-u3',
      title: 'Genitive Case',
      goal: 'Express possession, absence, quantity, and "from".',
      lessons: [
        {
          id: 'a2-u3-l1',
          title: 'Genitive: Of, From & Possession',
          cefr: 'A2',
          grammarFocus: 'Genitive endings -а/-я (masc/neut), -ы/-и (fem); у + gen. for "have"',
          canDo: ['I can show possession ("X\'s Y").', 'I can say where something is from.'],
          explanation:
            'The GENITIVE answers "whose? / of what? / from where?". Endings: masculine/neuter → -а/-я (дом → ' +
            'до́ма, музе́й → музе́я); feminine -а→-ы, -я→-и (Москва́ → из Москвы́, неде́ля → неде́ли). It expresses ' +
            'possession ("кни́га бра́та" = the brother\'s book), origin with из/с/от ("я из Аме́рики"), and the ' +
            'owner in the "have" construction (у бра́та есть…). English "of" is usually genitive in Russian.',
          vocab: [
            { ru: 'у (+ gen.)', en: 'at / by / "have"', translit: 'u', ex: 'у бра́та — at the brother\'s / brother\'s' },
            { ru: 'из (+ gen.)', en: 'from / out of', translit: 'iz', ex: 'из Москвы́ — from Moscow' },
            { ru: 'без (+ gen.)', en: 'without', translit: 'bez', ex: 'ко́фе без са́хара — coffee without sugar' },
            { ru: 'центр', en: 'center', translit: 'tsentr', ex: 'центр го́рода — the city center' },
            { ru: 'друг → дру́га', en: 'friend (gen.)', translit: 'drug → druga', ex: 'дом дру́га — the friend\'s house' },
            { ru: 'нет (+ gen.)', en: 'there is no…', translit: 'nyet', ex: 'У меня́ нет вре́мени. — I have no time.' },
          ],
          examples: [
            { ru: 'Э́то маши́на моего́ бра́та.', en: 'This is my brother\'s car.', translit: 'Eto mashina moyego brata.' },
            { ru: 'У меня́ нет де́нег.', en: 'I have no money.', translit: 'U menya nyet deneg.' },
          ],
          dialogue: null,
          notes: 'Absence/non-existence ALWAYS takes the genitive: нет + genitive ("there is no…").',
        },
        {
          id: 'a2-u3-l2',
          title: 'Genitive of Quantity & Numbers',
          cefr: 'A2',
          grammarFocus: 'Genitive after много/мало and numbers (2–4 gen. sing., 5+ gen. pl.)',
          canDo: ['I can express amounts ("a lot of / a little").', 'I can count nouns correctly.'],
          explanation:
            'Quantity words and numbers govern the genitive. After мно́го (a lot), ма́ло (few), ско́лько (how ' +
            'much), and нет use the genitive: мно́го рабо́ты, ма́ло вре́мени. Numbers are tricky: 1 → nominative ' +
            '(оди́н рубль), 2–4 → genitive SINGULAR (два рубля́, три кни́ги), 5 and up → genitive PLURAL (пять ' +
            'рубле́й, де́сять книг). This pattern repeats with every counted noun, so drill it.',
          vocab: [
            { ru: 'мно́го (+ gen.)', en: 'a lot of', translit: 'mnogo', ex: 'мно́го люде́й — many people' },
            { ru: 'ма́ло (+ gen.)', en: 'few / little', translit: 'malo', ex: 'ма́ло вре́мени — little time' },
            { ru: 'ско́лько (+ gen.)', en: 'how much/many', translit: 'skolko', ex: 'Ско́лько сто́ит? — How much is it?' },
            { ru: 'рубль / рубля́ / рубле́й', en: 'ruble (counted)', translit: 'rubl / rublya / rubley', ex: 'сто рубле́й — 100 rubles' },
            { ru: 'де́ньги', en: 'money', translit: 'dengi', ex: 'У меня́ ма́ло де́нег. — I have little money.' },
            { ru: 'не́сколько', en: 'a few / several', translit: 'neskolko', ex: 'не́сколько дней — a few days' },
          ],
          examples: [
            { ru: 'У меня́ два бра́та и три сестры́.', en: 'I have two brothers and three sisters.', translit: 'U menya dva brata i tri sestry.' },
            { ru: 'В кла́ссе мно́го студе́нтов.', en: 'There are many students in the class.', translit: 'V klasse mnogo studentov.' },
          ],
          dialogue: null,
          notes: 'Memorize: 2–4 = gen. singular, 5–20 = gen. plural. The pattern resets every 21, 31, …',
        },
      ],
    },
    {
      id: 'a2-u4',
      title: 'Dative & Instrumental',
      goal: 'Say "to whom", express age and feelings, and use "with".',
      lessons: [
        {
          id: 'a2-u4-l1',
          title: 'Dative Case: To Whom & Feelings',
          cefr: 'A2',
          grammarFocus: 'Dative -у/-ю (m/n), -е (f); impersonal мне ну́жно / мне нра́вится; age',
          canDo: ['I can say to/for whom I do something.', 'I can express likes, needs, and age.'],
          explanation:
            'The DATIVE marks the recipient — "to/for whom". Endings: masc/neut -у/-ю (бра́ту, дру́гу), fem -е ' +
            '(ма́ме, сестре́). The pronouns: мне, тебе́, ему́, ей, нам, вам, им. It powers many "impersonal" ' +
            'feelings where the person is in the dative: "Мне нра́вится…" (I like…), "Мне ну́жно…" (I need to…), ' +
            '"Мне хо́лодно" (I\'m cold). Age also uses the dative: "Мне два́дцать лет" (I am 20).',
          vocab: [
            { ru: 'мне / тебе́ / ему́', en: 'to me / you / him', translit: 'mne / tebe / yemu', ex: 'Дай мне кни́гу. — Give me the book.' },
            { ru: 'нра́виться', en: 'to be pleasing (= like)', translit: 'nravitsya', ex: 'Мне нра́вится Москва́. — I like Moscow.' },
            { ru: 'ну́жно / на́до', en: 'need to / must', translit: 'nuzhno / nado', ex: 'Мне ну́жно идти́. — I need to go.' },
            { ru: 'помога́ть (+ dat.)', en: 'to help (someone)', translit: 'pomogat', ex: 'Я помога́ю ма́ме. — I help mom.' },
            { ru: 'звони́ть (+ dat.)', en: 'to call (someone)', translit: 'zvonit', ex: 'Я звоню́ дру́гу. — I am calling a friend.' },
            { ru: 'год / го́да / лет', en: 'year(s) old', translit: 'god / goda / let', ex: 'Мне три́дцать лет. — I am 30.' },
          ],
          examples: [
            { ru: 'Мне нра́вится э́та кни́га.', en: 'I like this book.', translit: 'Mne nravitsya eta kniga.' },
            { ru: 'Ско́лько тебе́ лет? — Мне два́дцать пять.', en: 'How old are you? — I\'m twenty-five.', translit: 'Skolko tebe let? — Mne dvadtsat pyat.' },
          ],
          dialogue: null,
          notes: 'With нра́виться the thing LIKED is the grammatical subject: "Мне нра́вится кни́га" = "the book is pleasing to me".',
        },
        {
          id: 'a2-u4-l2',
          title: 'Instrumental Case: With & By Means Of',
          cefr: 'A2',
          grammarFocus: 'Instrumental -ом/-ем (m/n), -ой/-ей (f); с + instr. ("together with"); profession',
          canDo: ['I can say "with" someone or something.', 'I can say what someone works as.'],
          explanation:
            'The INSTRUMENTAL says "by means of / with". Endings: masc/neut -ом/-ем (но́жом, чáем), fem -ой/-ей ' +
            '(ру́чкой, Аней). Alone it means "by/using" (я пишу́ ру́чкой = I write with a pen). With the ' +
            'preposition с it means "together with" (ко́фе с молоко́м, я иду́ с дру́гом). It also names a ' +
            'profession/role after быть, стать, рабо́тать: "Он рабо́тает инжене́ром" (He works as an engineer).',
          vocab: [
            { ru: 'с (+ instr.)', en: 'with (together)', translit: 's', ex: 'ко́фе с молоко́м — coffee with milk' },
            { ru: 'рабо́тать (+ instr.)', en: 'to work as', translit: 'rabotat', ex: 'Я рабо́таю учи́телем. — I work as a teacher.' },
            { ru: 'друг → с дру́гом', en: 'with a friend', translit: 's drugom', ex: 'Я был с дру́гом. — I was with a friend.' },
            { ru: 'занима́ться (+ instr.)', en: 'to be busy with / do', translit: 'zanimatsya', ex: 'Я занима́юсь спо́ртом. — I do sports.' },
            { ru: 'ме́жду (+ instr.)', en: 'between', translit: 'mezhdu', ex: 'ме́жду на́ми — between us' },
            { ru: 'ста́ть (+ instr.)', en: 'to become', translit: 'stat', ex: 'Я хочу́ стать врачо́м. — I want to become a doctor.' },
          ],
          examples: [
            { ru: 'Я люблю́ чай с лимо́ном.', en: 'I like tea with lemon.', translit: 'Ya lyublyu chay s limonom.' },
            { ru: 'Моя́ сестра́ рабо́тает юри́стом.', en: 'My sister works as a lawyer.', translit: 'Moya sestra rabotayet yuristom.' },
          ],
          dialogue: null,
          notes: 'Profession after рабо́тать/быть/стать goes in the INSTRUMENTAL, not nominative.',
        },
      ],
    },
    {
      id: 'a2-u5',
      title: 'Getting Around',
      goal: 'Give and follow directions; talk about transport and travel.',
      lessons: [
        {
          id: 'a2-u5-l1',
          title: 'Directions & Motion Verbs (intro)',
          cefr: 'A2',
          grammarFocus: 'идти́ vs. е́хать (go on foot vs. by vehicle); куда́ + в/на + accusative',
          canDo: ['I can ask for and give simple directions.', 'I can say where I am going.'],
          explanation:
            'Russian has TWO basic "to go" verbs by mode: идти́ (on foot) and е́хать (by vehicle). For DESTINATION ' +
            '(куда́? where to?) use в/на + ACCUSATIVE — contrast with location (где?) which used the prepositional: ' +
            '"Я в теа́тре" (I\'m at the theater) vs. "Я иду́ в теа́тр" (I\'m going to the theater). Directions use ' +
            'нале́во (left), напра́во (right), пря́мо (straight). This is your first taste of motion verbs, a famously ' +
            'rich Russian system explored fully at B1.',
          vocab: [
            { ru: 'идти́', en: 'to go (on foot)', translit: 'idti', ex: 'Я иду́ домо́й. — I am walking home.' },
            { ru: 'е́хать', en: 'to go (by vehicle)', translit: 'yekhat', ex: 'Я е́ду в центр. — I am going to the center.' },
            { ru: 'куда́', en: 'where to', translit: 'kuda', ex: 'Куда́ ты идёшь? — Where are you going?' },
            { ru: 'нале́во / напра́во', en: 'left / right', translit: 'nalevo / napravo', ex: 'Иди́те напра́во. — Go right.' },
            { ru: 'пря́мо', en: 'straight ahead', translit: 'pryamo', ex: 'Иди́те пря́мо. — Go straight.' },
            { ru: 'остано́вка', en: 'stop (bus/tram)', translit: 'ostanovka', ex: 'на остано́вке — at the stop' },
            { ru: 'авто́бус / метро́', en: 'bus / metro', translit: 'avtobus / metro', ex: 'на метро́ — by metro' },
          ],
          examples: [
            { ru: 'Иди́те пря́мо, пото́м напра́во.', en: 'Go straight, then right.', translit: 'Idite pryamo, potom napravo.' },
            { ru: 'Мы е́дем в Санкт-Петербу́рг на по́езде.', en: 'We are going to St. Petersburg by train.', translit: 'My yedem v Sankt-Peterburg na poyezde.' },
          ],
          dialogue: [
            { ru: '— Извини́те, где метро́?', en: '— Excuse me, where is the metro?' },
            { ru: '— Иди́те пря́мо и нале́во.', en: '— Go straight and left.' },
          ],
          notes: 'Location (где) = prepositional; destination (куда) = accusative. Same prepositions в/на, different case.',
        },
      ],
    },
  ],
};

// --- B1–C2: structured OUTLINES the AI tutor expands into full lessons. ---
// Each lesson still carries id/title/cefr/grammarFocus/canDo and key vocab so
// the program has a real spine to fluency; explanation/examples are generated
// on demand by ARIA (kept short here, with notes flagging "expand on demand").

const OUTLINE_NOTE = 'Outline lesson — ARIA expands this into a full interactive lesson on demand.';
function outline(id, title, grammarFocus, canDo, vocab) {
  return {
    id,
    title,
    cefr: id.slice(0, 2).toUpperCase(),
    grammarFocus,
    canDo: Array.isArray(canDo) ? canDo : [canDo],
    explanation: '',
    vocab: vocab || [],
    examples: [],
    dialogue: null,
    notes: OUTLINE_NOTE,
  };
}

const B1 = {
  level: 'B1',
  summary:
    'Intermediate. Master verb aspect in depth, the full motion-verb system with ' +
    'prefixes, comparatives, the conditional, reported speech, and connected ' +
    'narration about experiences, opinions, and plans.',
  units: [
    {
      id: 'b1-u1',
      title: 'Verb Aspect in Depth',
      goal: 'Choose aspect fluently across tenses and moods.',
      lessons: [
        outline('b1-u1-l1', 'Aspect Pairs & Formation', 'How perfectives are built (prefixes, suffix -ыва-/-ива-, stem changes)',
          ['I can predict and form the aspect partner of a verb.'],
          [{ ru: 'реша́ть / реши́ть', en: 'to solve', translit: 'reshat / reshit', ex: 'Я реши́л зада́чу. — I solved the problem.' },
           { ru: 'начина́ть / нача́ть', en: 'to begin', translit: 'nachinat / nachat', ex: 'Дождь на́чался. — The rain began.' }]),
        outline('b1-u1-l2', 'Aspect in the Future & Imperative', 'Aspect choice for requests, single vs. repeated future actions',
          ['I can pick aspect correctly when giving commands and making plans.'],
          [{ ru: 'возьми́ / бери́', en: 'take! (pf./impf.)', translit: 'vozmi / beri', ex: 'Возьми́ зонт! — Take an umbrella!' }]),
      ],
    },
    {
      id: 'b1-u2',
      title: 'Verbs of Motion',
      goal: 'Use directional/multidirectional pairs and motion prefixes.',
      lessons: [
        outline('b1-u2-l1', 'Unidirectional vs. Multidirectional', 'идти/ходи́ть, е́хать/е́здить, лете́ть/лета́ть pairs',
          ['I can distinguish a one-way trip from habitual/round-trip motion.'],
          [{ ru: 'ходи́ть', en: 'to go (regularly, on foot)', translit: 'khodit', ex: 'Я хожу́ в спортза́л. — I go to the gym (regularly).' }]),
        outline('b1-u2-l2', 'Prefixed Verbs of Motion', 'при-/у-/в-/вы-/под-/от-/пере- on motion stems',
          ['I can express arrive, leave, enter, exit, cross with prefixes.'],
          [{ ru: 'приходи́ть / прийти́', en: 'to arrive (on foot)', translit: 'prikhodit / priyti', ex: 'Он пришёл по́здно. — He arrived late.' },
           { ru: 'уходи́ть / уйти́', en: 'to leave', translit: 'ukhodit / uyti', ex: 'Я ухожу́. — I am leaving.' }]),
      ],
    },
    {
      id: 'b1-u3',
      title: 'Comparison, Conditionals & Reported Speech',
      goal: 'Compare things, hypothesize, and report what others say.',
      lessons: [
        outline('b1-u3-l1', 'Comparatives & Superlatives', 'бо́льше/лу́чше, -ее forms, са́мый + adjective',
          ['I can compare two things and express "the most".'],
          [{ ru: 'лу́чше / ху́же', en: 'better / worse', translit: 'luchshe / khuzhe', ex: 'Сего́дня лу́чше, чем вчера́. — Today is better than yesterday.' }]),
        outline('b1-u3-l2', 'The Conditional with бы', 'Hypothetical/subjunctive: past-tense verb + бы',
          ['I can say what I would do.'],
          [{ ru: 'е́сли бы', en: 'if (hypothetical)', translit: 'yesli by', ex: 'Е́сли бы я знал… — If I had known…' }]),
        outline('b1-u3-l3', 'Reported Speech & Conjunctions', 'что/чтобы, indirect questions, sequence of clauses',
          ['I can report statements, questions, and requests.'],
          [{ ru: 'чтобы', en: 'in order to / that', translit: 'chtoby', ex: 'Я хочу́, чтобы ты пришёл. — I want you to come.' }]),
      ],
    },
  ],
};

const B2 = {
  level: 'B2',
  summary:
    'Upper-intermediate. Use participles and verbal adverbs (gerunds), the full ' +
    'passive, complex sentence syntax, abstract and professional vocabulary, and ' +
    'argue a point with nuance and appropriate register.',
  units: [
    {
      id: 'b2-u1',
      title: 'Participles & Verbal Adverbs',
      goal: 'Compress clauses with participles and gerunds.',
      lessons: [
        outline('b2-u1-l1', 'Active & Passive Participles', 'present/past active (-ущ-/-вш-) and passive (-ем-/-нн-/-т-) participles',
          ['I can replace a "который" clause with a participle.'],
          [{ ru: 'чита́ющий', en: 'reading (one who reads)', translit: 'chitayushchy', ex: 'студе́нт, чита́ющий кни́гу — the student reading a book' }]),
        outline('b2-u1-l2', 'Verbal Adverbs (Gerunds)', 'simultaneous (-я) and prior (-в) деепричастия',
          ['I can express "while doing / having done" concisely.'],
          [{ ru: 'чита́я', en: 'while reading', translit: 'chitaya', ex: 'Чита́я, он де́лал заме́тки. — Reading, he made notes.' }]),
      ],
    },
    {
      id: 'b2-u2',
      title: 'Syntax, Voice & Register',
      goal: 'Build complex sentences and shift register appropriately.',
      lessons: [
        outline('b2-u2-l1', 'Passive & Impersonal Constructions', 'reflexive passive (-ся), impersonal sentences, word-order emphasis',
          ['I can use the passive voice and impersonal constructions naturally.'],
          [{ ru: 'строи́ться', en: 'to be built', translit: 'stroitsya', ex: 'Дом стро́ится. — The house is being built.' }]),
        outline('b2-u2-l2', 'Formal vs. Informal Register', 'bureaucratic/academic style, softening, polite distance',
          ['I can adjust formality for emails, interviews, and officialdom.'],
          [{ ru: 'в связи́ с', en: 'in connection with', translit: 'v svyazi s', ex: 'В связи́ с э́тим… — In connection with this…' }]),
      ],
    },
  ],
};

const C1 = {
  level: 'C1',
  summary:
    'Advanced. Command idioms, aspectual subtleties, stylistic nuance, abstract ' +
    'and figurative language, and produce well-structured discourse on complex ' +
    'topics across spoken and written registers.',
  units: [
    {
      id: 'c1-u1',
      title: 'Nuance & Idiom',
      goal: 'Use idioms, fixed expressions, and fine aspectual/stylistic distinctions.',
      lessons: [
        outline('c1-u1-l1', 'Idioms & Set Phrases', 'frequent idioms, collocations, proverbs and their register',
          ['I can use idiomatic Russian appropriately.'],
          [{ ru: 'бить баклу́ши', en: 'to twiddle one\'s thumbs', translit: 'bit baklushi', ex: 'Хва́тит бить баклу́ши! — Stop loafing around!' }]),
        outline('c1-u1-l2', 'Aspect & Stylistic Subtleties', 'aspect with negation, modal nuance, connotation and emphasis',
          ['I can exploit aspect and word order for fine shades of meaning.'], []),
      ],
    },
    {
      id: 'c1-u2',
      title: 'Discourse & Argument',
      goal: 'Structure extended argument and abstract discussion.',
      lessons: [
        outline('c1-u2-l1', 'Cohesion & Discourse Markers', 'тем не ме́нее, таки́м о́бразом, paragraph-level connectors',
          ['I can structure a coherent extended argument.'],
          [{ ru: 'тем не ме́нее', en: 'nevertheless', translit: 'tem ne meneye', ex: 'Тем не ме́нее, э́то ва́жно. — Nevertheless, it matters.' }]),
        outline('c1-u2-l2', 'Abstract & Figurative Language', 'metaphor, abstraction, nuance in opinion and evaluation',
          ['I can discuss abstract topics with precision and style.'], []),
      ],
    },
  ],
};

const C2 = {
  level: 'C2',
  summary:
    'Mastery. Near-native control: literary and specialized registers, wordplay ' +
    'and subtext, regional/colloquial variation, and effortless, precise ' +
    'expression on any topic.',
  units: [
    {
      id: 'c2-u1',
      title: 'Mastery & Style',
      goal: 'Operate across literary, technical, and colloquial registers with full control.',
      lessons: [
        outline('c2-u1-l1', 'Literary & Specialized Registers', 'classical/literary style, technical and scientific discourse',
          ['I can read and produce literary and specialized texts.'], []),
        outline('c2-u1-l2', 'Colloquialism, Slang & Subtext', 'modern slang, irony, humor, regional variation, implied meaning',
          ['I can catch and use subtext, humor, and colloquial nuance.'],
          [{ ru: 'кру́то', en: 'cool / awesome (colloq.)', translit: 'kruto', ex: 'Э́то о́чень кру́то! — That\'s really cool!' }]),
      ],
    },
  ],
};

const CURRICULUM = [A1, A2, B1, B2, C1, C2];

// Flat list of every lesson, in curriculum order, tagged with its level/unit.
const LESSON_INDEX = [];
CURRICULUM.forEach((lvl) => {
  lvl.units.forEach((unit) => {
    (unit.lessons || []).forEach((lesson) => {
      LESSON_INDEX.push({ lesson, level: lvl.level, unitId: unit.id, unitTitle: unit.title });
    });
  });
});
const TOTAL_LESSONS = LESSON_INDEX.length;

function findLesson(id) {
  return LESSON_INDEX.find((e) => e.lesson.id === id) || null;
}
function firstLessonId() {
  return LESSON_INDEX.length ? LESSON_INDEX[0].lesson.id : null;
}
// The next lesson AFTER `id` in curriculum order (null if last/unknown).
function lessonAfter(id) {
  const i = LESSON_INDEX.findIndex((e) => e.lesson.id === id);
  if (i < 0 || i + 1 >= LESSON_INDEX.length) return null;
  return LESSON_INDEX[i + 1];
}

// ===========================================================================
// SEED VOCABULARY — ~150 high-frequency words across themes. Available to
// batch-add into SRS via seedVocab({theme}). Plain data; ex is optional.
// ===========================================================================
const SEED_VOCAB = {
  greetings: [
    { word: 'приве́т', translation: 'hi', example: 'Приве́т! Как дела́?' },
    { word: 'здра́вствуйте', translation: 'hello (formal)', example: 'Здра́вствуйте!' },
    { word: 'до свида́ния', translation: 'goodbye', example: 'До свида́ния!' },
    { word: 'спаси́бо', translation: 'thank you', example: 'Большо́е спаси́бо.' },
    { word: 'пожа́луйста', translation: 'please / you\'re welcome', example: 'Да, пожа́луйста.' },
    { word: 'извини́те', translation: 'excuse me (formal)', example: 'Извини́те!' },
    { word: 'да', translation: 'yes', example: 'Да, коне́чно.' },
    { word: 'нет', translation: 'no', example: 'Нет, спаси́бо.' },
    { word: 'как дела́?', translation: 'how are you?', example: 'Как дела́? — Хорошо́.' },
    { word: 'о́чень прия́тно', translation: 'nice to meet you', example: 'О́чень прия́тно!' },
  ],
  people: [
    { word: 'челове́к', translation: 'person', example: 'хоро́ший челове́к' },
    { word: 'мужчи́на', translation: 'man', example: 'Э́тот мужчи́на — врач.' },
    { word: 'же́нщина', translation: 'woman', example: 'Э́та же́нщина — учи́тель.' },
    { word: 'ребёнок', translation: 'child', example: 'ма́ленький ребёнок' },
    { word: 'друг', translation: 'friend (m)', example: 'мой лу́чший друг' },
    { word: 'подру́га', translation: 'friend (f)', example: 'её подру́га' },
    { word: 'сосе́д', translation: 'neighbor', example: 'мой сосе́д' },
    { word: 'нача́льник', translation: 'boss', example: 'строгий нача́льник' },
  ],
  family: [
    { word: 'семья́', translation: 'family', example: 'больша́я семья́' },
    { word: 'ма́ма', translation: 'mom', example: 'Моя́ ма́ма до́ма.' },
    { word: 'па́па', translation: 'dad', example: 'Мой па́па рабо́тает.' },
    { word: 'брат', translation: 'brother', example: 'У меня́ есть брат.' },
    { word: 'сестра́', translation: 'sister', example: 'Моя́ сестра́ — студе́нтка.' },
    { word: 'сын', translation: 'son', example: 'их сын' },
    { word: 'дочь', translation: 'daughter', example: 'их дочь' },
    { word: 'жена́', translation: 'wife', example: 'моя́ жена́' },
    { word: 'муж', translation: 'husband', example: 'её муж' },
    { word: 'ба́бушка', translation: 'grandmother', example: 'моя́ ба́бушка' },
    { word: 'де́душка', translation: 'grandfather', example: 'мой де́душка' },
  ],
  food: [
    { word: 'еда́', translation: 'food', example: 'вку́сная еда́' },
    { word: 'вода́', translation: 'water', example: 'стака́н воды́' },
    { word: 'хлеб', translation: 'bread', example: 'све́жий хлеб' },
    { word: 'мя́со', translation: 'meat', example: 'кусо́к мя́са' },
    { word: 'ры́ба', translation: 'fish', example: 'жа́реная ры́ба' },
    { word: 'о́вощи', translation: 'vegetables', example: 'све́жие о́вощи' },
    { word: 'фру́кты', translation: 'fruit', example: 'спе́лые фру́кты' },
    { word: 'молоко́', translation: 'milk', example: 'ко́фе с молоко́м' },
    { word: 'сыр', translation: 'cheese', example: 'хлеб и сыр' },
    { word: 'ко́фе', translation: 'coffee', example: 'ча́шка ко́фе' },
    { word: 'чай', translation: 'tea', example: 'чай с лимо́ном' },
    { word: 'суп', translation: 'soup', example: 'горя́чий суп' },
    { word: 'я́блоко', translation: 'apple', example: 'кра́сное я́блоко' },
    { word: 'са́хар', translation: 'sugar', example: 'без са́хара' },
  ],
  numbers: [
    { word: 'оди́н', translation: 'one', example: 'оди́н раз' },
    { word: 'два', translation: 'two', example: 'два часа́' },
    { word: 'три', translation: 'three', example: 'три дня' },
    { word: 'четы́ре', translation: 'four', example: 'четы́ре го́да' },
    { word: 'пять', translation: 'five', example: 'пять мину́т' },
    { word: 'шесть', translation: 'six', example: 'шесть рубле́й' },
    { word: 'семь', translation: 'seven', example: 'семь дней' },
    { word: 'во́семь', translation: 'eight', example: 'во́семь часо́в' },
    { word: 'де́вять', translation: 'nine', example: 'де́вять лет' },
    { word: 'де́сять', translation: 'ten', example: 'де́сять рубле́й' },
    { word: 'сто', translation: 'hundred', example: 'сто рубле́й' },
    { word: 'ты́сяча', translation: 'thousand', example: 'ты́сяча рубле́й' },
  ],
  time: [
    { word: 'вре́мя', translation: 'time', example: 'У меня́ нет вре́мени.' },
    { word: 'день', translation: 'day', example: 'До́брый день!' },
    { word: 'ночь', translation: 'night', example: 'Споко́йной но́чи.' },
    { word: 'у́тро', translation: 'morning', example: 'До́брое у́тро!' },
    { word: 'ве́чер', translation: 'evening', example: 'До́брый ве́чер!' },
    { word: 'неде́ля', translation: 'week', example: 'на э́той неде́ле' },
    { word: 'ме́сяц', translation: 'month', example: 'в сле́дующем ме́сяце' },
    { word: 'год', translation: 'year', example: 'в про́шлом году́' },
    { word: 'сего́дня', translation: 'today', example: 'Сего́дня хорошо́.' },
    { word: 'за́втра', translation: 'tomorrow', example: 'До за́втра!' },
    { word: 'вчера́', translation: 'yesterday', example: 'Вчера́ был дождь.' },
    { word: 'сейча́с', translation: 'now', example: 'Я за́нят сейча́с.' },
  ],
  places: [
    { word: 'дом', translation: 'house / home', example: 'мой дом' },
    { word: 'кварти́ра', translation: 'apartment', example: 'ма́ленькая кварти́ра' },
    { word: 'го́род', translation: 'city', example: 'большо́й го́род' },
    { word: 'у́лица', translation: 'street', example: 'на у́лице' },
    { word: 'магази́н', translation: 'shop / store', example: 'в магази́не' },
    { word: 'рестора́н', translation: 'restaurant', example: 'но́вый рестора́н' },
    { word: 'шко́ла', translation: 'school', example: 'в шко́ле' },
    { word: 'рабо́та', translation: 'work', example: 'на рабо́те' },
    { word: 'больни́ца', translation: 'hospital', example: 'в больни́це' },
    { word: 'вокза́л', translation: 'train station', example: 'на вокза́ле' },
    { word: 'аэропо́рт', translation: 'airport', example: 'в аэропорту́' },
    { word: 'банк', translation: 'bank', example: 'в ба́нке' },
  ],
  travel: [
    { word: 'маши́на', translation: 'car', example: 'но́вая маши́на' },
    { word: 'авто́бус', translation: 'bus', example: 'на авто́бусе' },
    { word: 'по́езд', translation: 'train', example: 'на по́езде' },
    { word: 'самолёт', translation: 'airplane', example: 'на самолёте' },
    { word: 'метро́', translation: 'metro', example: 'на метро́' },
    { word: 'биле́т', translation: 'ticket', example: 'биле́т на по́езд' },
    { word: 'каранда́ш', translation: 'pencil', example: 'кра́сный каранда́ш' },
    { word: 'чемода́н', translation: 'suitcase', example: 'тяжёлый чемода́н' },
    { word: 'карта', translation: 'map', example: 'карта го́рода' },
  ],
  verbs: [
    { word: 'быть', translation: 'to be', example: 'Я бу́ду до́ма.' },
    { word: 'име́ть', translation: 'to have', example: 'У меня́ есть вре́мя.' },
    { word: 'де́лать', translation: 'to do / make', example: 'Что ты де́лаешь?' },
    { word: 'говори́ть', translation: 'to speak / say', example: 'Я говорю́ по-ру́сски.' },
    { word: 'знать', translation: 'to know', example: 'Я не зна́ю.' },
    { word: 'ду́мать', translation: 'to think', example: 'Я так ду́маю.' },
    { word: 'хоте́ть', translation: 'to want', example: 'Я хочу́ есть.' },
    { word: 'мочь', translation: 'can / be able', example: 'Я могу́ помо́чь.' },
    { word: 'идти́', translation: 'to go (on foot)', example: 'Я иду́ домо́й.' },
    { word: 'е́хать', translation: 'to go (by vehicle)', example: 'Я е́ду в центр.' },
    { word: 'ви́деть', translation: 'to see', example: 'Я ви́жу дом.' },
    { word: 'слы́шать', translation: 'to hear', example: 'Я слы́шу му́зыку.' },
    { word: 'дава́ть', translation: 'to give', example: 'Дай мне ру́чку.' },
    { word: 'брать', translation: 'to take', example: 'Возьми́ э́то.' },
    { word: 'есть', translation: 'to eat', example: 'Я хочу́ есть.' },
    { word: 'пить', translation: 'to drink', example: 'Я пью чай.' },
    { word: 'рабо́тать', translation: 'to work', example: 'Я рабо́таю до́ма.' },
    { word: 'жить', translation: 'to live', example: 'Я живу́ в Москве́.' },
    { word: 'люби́ть', translation: 'to love / like', example: 'Я люблю́ тебя́.' },
    { word: 'покупа́ть', translation: 'to buy', example: 'Я покупа́ю хлеб.' },
  ],
  adjectives: [
    { word: 'большо́й', translation: 'big', example: 'большо́й дом' },
    { word: 'ма́ленький', translation: 'small', example: 'ма́ленький кот' },
    { word: 'но́вый', translation: 'new', example: 'но́вый телефо́н' },
    { word: 'ста́рый', translation: 'old', example: 'ста́рый го́род' },
    { word: 'хоро́ший', translation: 'good', example: 'хоро́ший день' },
    { word: 'плохо́й', translation: 'bad', example: 'плохо́й знак' },
    { word: 'краси́вый', translation: 'beautiful', example: 'краси́вая де́вушка' },
    { word: 'дорого́й', translation: 'expensive / dear', example: 'дорого́й пода́рок' },
    { word: 'дешёвый', translation: 'cheap', example: 'дешёвый биле́т' },
    { word: 'тёплый', translation: 'warm', example: 'тёплый день' },
    { word: 'холо́дный', translation: 'cold', example: 'холо́дная вода́' },
    { word: 'бы́стрый', translation: 'fast', example: 'бы́стрый по́езд' },
  ],
  common: [
    { word: 'и', translation: 'and', example: 'ты и я' },
    { word: 'но', translation: 'but', example: 'хорошо́, но до́рого' },
    { word: 'и́ли', translation: 'or', example: 'чай и́ли ко́фе?' },
    { word: 'потому́ что', translation: 'because', example: 'потому́ что хо́лодно' },
    { word: 'о́чень', translation: 'very', example: 'о́чень хорошо́' },
    { word: 'то́же', translation: 'also / too', example: 'Я то́же.' },
    { word: 'здесь', translation: 'here', example: 'Я здесь.' },
    { word: 'там', translation: 'there', example: 'Он там.' },
    { word: 'хорошо́', translation: 'good / well', example: 'Всё хорошо́.' },
    { word: 'пло́хо', translation: 'bad / badly', example: 'Я чу́вствую себя́ пло́хо.' },
    { word: 'мо́жно', translation: 'may / allowed', example: 'Мо́жно войти́?' },
    { word: 'нельзя́', translation: 'not allowed', example: 'Здесь нельзя́ кури́ть.' },
  ],
};

const SEED_THEMES = Object.keys(SEED_VOCAB);

// ===========================================================================
// PROGRESS — persisted under STORE_KEY. Mirrors study.js streak idea via a
// day-rollover keyed on lastStudiedDate (see touchStreak).
// ===========================================================================
function defaultProgress() {
  return {
    level: 'A1',
    currentLessonId: firstLessonId(),
    completedLessons: [],
    topicMastery: {}, // topic/lessonId -> 0..100
    wordsLearned: 0,
    streak: 0,
    lastStudiedDate: null,
    minutesToday: 0,
    dailyGoalMins: 15,
    settings: { showRomanization: true },
  };
}

function loadProgress() {
  const p = store.get(STORE_KEY, null);
  if (!p) {
    const init = defaultProgress();
    store.set(STORE_KEY, init);
    return init;
  }
  // Backfill any missing keys so older stores stay valid.
  const base = defaultProgress();
  const merged = { ...base, ...p, settings: { ...base.settings, ...(p.settings || {}) } };
  if (!merged.currentLessonId) merged.currentLessonId = firstLessonId();
  return merged;
}

function saveProgress(p) {
  store.set(STORE_KEY, p);
  return p;
}

// Roll the streak forward when the user studies. Same day = no change; the
// next calendar day = +1; a gap of 2+ days resets to 1. Also resets minutesToday
// on a new day. (Mirrors study.js's "consecutive days" streak idea.)
function touchStreak(p) {
  const t = today();
  if (p.lastStudiedDate === t) return p; // already counted today
  if (p.lastStudiedDate && addDays(p.lastStudiedDate, 1) === t) {
    p.streak = (p.streak || 0) + 1;
  } else {
    p.streak = 1; // first study ever, or a broken streak
  }
  p.lastStudiedDate = t;
  p.minutesToday = 0; // new day -> reset today's minutes
  return p;
}

// Has the calendar day rolled over since we last studied? If so, today's
// minutes are stale and should read 0 even before the next logPractice.
function freshMinutesToday(p) {
  return p.lastStudiedDate === today() ? (p.minutesToday || 0) : 0;
}

// ===========================================================================
// API — exact shapes the UI/IPC layer will wire to.
// ===========================================================================
function lessonRef(entry) {
  if (!entry) return null;
  return { id: entry.lesson.id, title: entry.lesson.title, unitTitle: entry.unitTitle, level: entry.level };
}

function getProgress() {
  const p = loadProgress();
  const completed = p.completedLessons || [];
  const curEntry = p.currentLessonId ? findLesson(p.currentLessonId) : null;
  // Recommend the first not-yet-done lesson as "next".
  let nextEntry = LESSON_INDEX.find((e) => !completed.includes(e.lesson.id)) || null;
  if (curEntry && !completed.includes(curEntry.lesson.id)) nextEntry = curEntry;
  return {
    level: p.level,
    streak: p.streak || 0,
    wordsLearned: p.wordsLearned || 0,
    dailyGoalMins: p.dailyGoalMins || 15,
    minutesToday: freshMinutesToday(p),
    completedCount: completed.length,
    totalLessons: TOTAL_LESSONS,
    currentLesson: lessonRef(curEntry),
    nextLesson: lessonRef(nextEntry),
    settings: p.settings || { showRomanization: true },
  };
}

// Lightweight curriculum tree with per-lesson done flags (no heavy content).
function getCurriculum() {
  const completed = loadProgress().completedLessons || [];
  return CURRICULUM.map((lvl) => ({
    level: lvl.level,
    summary: lvl.summary,
    units: lvl.units.map((unit) => ({
      id: unit.id,
      title: unit.title,
      goal: unit.goal,
      lessons: (unit.lessons || []).map((l) => ({
        id: l.id,
        title: l.title,
        cefr: l.cefr,
        grammarFocus: l.grammarFocus,
        canDo: l.canDo,
        done: completed.includes(l.id),
      })),
    })),
  }));
}

// Full lesson content + its level/unit context.
function getLesson(id) {
  const entry = findLesson(id);
  if (!entry) throw new Error(`No Russian lesson with id "${id}".`);
  return { ...entry.lesson, level: entry.level, unitTitle: entry.unitTitle };
}

function getAlphabet() {
  return ALPHABET;
}

function startLesson(id) {
  const entry = findLesson(id);
  if (!entry) throw new Error(`No Russian lesson with id "${id}".`);
  const p = loadProgress();
  p.currentLessonId = id;
  saveProgress(p);
  return getProgress();
}

// Mark a lesson done: record it, bump words/mastery, and advance currentLesson
// to the next not-yet-done lesson. score (0..100) feeds topic mastery.
function completeLesson({ id, score } = {}) {
  const entry = findLesson(id);
  if (!entry) throw new Error(`No Russian lesson with id "${id}".`);
  const p = loadProgress();
  const completed = p.completedLessons || [];
  const wasNew = !completed.includes(id);
  if (wasNew) completed.push(id);
  p.completedLessons = completed;

  // Mastery for this lesson's topic; default to a solid pass if no score given.
  const s = Number.isFinite(Number(score)) ? clamp(Math.round(Number(score)), 0, 100) : 85;
  p.topicMastery = p.topicMastery || {};
  p.topicMastery[id] = Math.max(p.topicMastery[id] || 0, s);

  // Count this lesson's vocab toward wordsLearned (only the first time).
  if (wasNew) {
    const n = (entry.lesson.vocab || []).length;
    p.wordsLearned = (p.wordsLearned || 0) + n;
  }

  // Advance: prefer the next lesson in order; if it's done, jump to first undone.
  const after = lessonAfter(id);
  if (after && !completed.includes(after.lesson.id)) {
    p.currentLessonId = after.lesson.id;
  } else {
    const firstUndone = LESSON_INDEX.find((e) => !completed.includes(e.lesson.id));
    p.currentLessonId = firstUndone ? firstUndone.lesson.id : id;
  }

  // Keep the learner's level aligned with where they are working.
  const curEntry = findLesson(p.currentLessonId);
  if (curEntry) p.level = curEntry.level;

  saveProgress(p);
  return getProgress();
}

function setLevel(level) {
  const lv = String(level || '').trim().toUpperCase();
  if (!LEVELS.includes(lv)) throw new Error(`level must be one of ${LEVELS.join(', ')}`);
  const p = loadProgress();
  p.level = lv;
  // Point currentLesson at the first not-yet-done lesson in that level.
  const completed = p.completedLessons || [];
  const target =
    LESSON_INDEX.find((e) => e.level === lv && !completed.includes(e.lesson.id)) ||
    LESSON_INDEX.find((e) => e.level === lv);
  if (target) p.currentLessonId = target.lesson.id;
  saveProgress(p);
  return getProgress();
}

// Add caller-supplied words to SRS via study.js. Returns how many were added.
function addVocabBatch({ words } = {}) {
  const list = Array.isArray(words) ? words : [];
  let added = 0;
  list.forEach((w) => {
    if (!w || !w.word || !w.translation) return;
    study.api.addVocab({
      word: String(w.word).trim(),
      translation: String(w.translation).trim(),
      example: w.example ? String(w.example).trim() : undefined,
      subject: SUBJECT,
    });
    added += 1;
  });
  if (added) {
    const p = loadProgress();
    p.wordsLearned = (p.wordsLearned || 0) + added;
    saveProgress(p);
  }
  return { added };
}

// Seed the SRS with the frequency/themed set. theme omitted => all themes.
function seedVocab({ theme } = {}) {
  let words = [];
  if (theme) {
    const key = String(theme).trim().toLowerCase();
    words = SEED_VOCAB[key] || [];
    if (!words.length) throw new Error(`Unknown theme "${theme}". Themes: ${SEED_THEMES.join(', ')}`);
  } else {
    words = SEED_THEMES.flatMap((k) => SEED_VOCAB[k]);
  }
  return addVocabBatch({ words });
}

// Log a study/practice session: roll the streak, add minutes for today.
function logPractice({ minutes, kind } = {}) {
  const mins = Math.round(Number(minutes));
  const p = loadProgress();
  touchStreak(p); // sets/keeps lastStudiedDate = today, resets minutes on new day
  if (Number.isFinite(mins) && mins > 0) {
    p.minutesToday = (p.minutesToday || 0) + mins;
  }
  // kind is advisory (lesson|conversation|review|grammar|reading) — stored as last.
  p.lastPracticeKind = kind ? String(kind).trim() : (p.lastPracticeKind || 'lesson');
  saveProgress(p);
  return getProgress();
}

function setSettings({ showRomanization, dailyGoalMins } = {}) {
  const p = loadProgress();
  p.settings = p.settings || { showRomanization: true };
  if (showRomanization !== undefined) p.settings.showRomanization = Boolean(showRomanization);
  if (dailyGoalMins !== undefined) {
    const g = Math.round(Number(dailyGoalMins));
    if (Number.isFinite(g) && g > 0) p.dailyGoalMins = clamp(g, 1, 600);
  }
  saveProgress(p);
  return getProgress();
}

// Reuse study.js's due queue, filtered to russian.
function reviewQueue() {
  return study.api.dueFlashcards({ subject: SUBJECT });
}

// Recommend the next concrete action for the brain/UI ("what's next").
function nextAction() {
  const prog = getProgress();
  const due = reviewQueue();
  const dueCount = Array.isArray(due) ? due.length : 0;
  let recommend;
  if (dueCount > 0) {
    recommend = `Review ${dueCount} due flashcard${dueCount === 1 ? '' : 's'} first, then continue with the next lesson.`;
  } else if (prog.nextLesson) {
    recommend = `Start the next lesson: "${prog.nextLesson.title}" (${prog.nextLesson.level}).`;
  } else {
    recommend = 'All lessons complete — switch to free conversation and reading practice to keep advancing.';
  }
  return {
    recommend,
    dueReviews: dueCount,
    nextLesson: prog.nextLesson,
    currentLesson: prog.currentLesson,
    level: prog.level,
    streak: prog.streak,
    minutesToday: prog.minutesToday,
    dailyGoalMins: prog.dailyGoalMins,
  };
}

// ===========================================================================
// BRAIN TOOLS — prescriptive descriptions so ARIA routes well.
// ===========================================================================
const tools = [
  {
    name: 'russian_progress',
    description:
      'Get the user\'s Russian program status: CEFR level, streak, words learned, today\'s minutes vs. daily goal, ' +
      'how many lessons are done, and the current and next lesson. Call this at the START of a tutoring session to orient yourself.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'russian_curriculum',
    description:
      'Get the full CEFR A1–C2 curriculum tree (levels → units → lessons) with a done flag on each lesson. ' +
      'Use to show the path, see what is left, or pick what to teach next.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'russian_lesson',
    description:
      'Get the full content of one lesson by id (explanation, vocab, examples, dialogue, notes). ' +
      'Call before teaching a lesson so you follow its grammar focus and use its exact vocab/examples. ' +
      'For B1+ outline lessons, expand the outline into a full interactive lesson yourself.',
    input_schema: {
      type: 'object',
      properties: { id: { type: 'string', description: 'Lesson id, e.g. "a1-u1-l1"' } },
      required: ['id'],
    },
  },
  {
    name: 'russian_alphabet',
    description: 'Get the full Cyrillic alphabet (33 letters) with names, sounds, transliteration, and an example word each. Use when teaching reading/pronunciation.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'russian_start_lesson',
    description: 'Mark a lesson as the current one the user is working on (by id). Call when the user begins a specific lesson.',
    input_schema: {
      type: 'object',
      properties: { id: { type: 'string', description: 'Lesson id, e.g. "a1-u2-l1"' } },
      required: ['id'],
    },
  },
  {
    name: 'russian_complete_lesson',
    description:
      'Mark a lesson finished and advance to the next one. Call when the user has worked through and can demonstrate the lesson. ' +
      'Pass an optional score 0–100 from how well they did on your drills to track mastery.',
    input_schema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: 'Lesson id just completed' },
        score: { type: 'number', description: 'Optional mastery score 0–100 from quizzing' },
      },
      required: ['id'],
    },
  },
  {
    name: 'russian_set_level',
    description: 'Set the user\'s CEFR level (A1, A2, B1, B2, C1, C2). Use after a placement check or when the user asks to jump to a level.',
    input_schema: {
      type: 'object',
      properties: { level: { type: 'string', enum: LEVELS } },
      required: ['level'],
    },
  },
  {
    name: 'russian_add_vocab',
    description:
      'Add one or more Russian words to spaced-repetition review. Call whenever new words come up in conversation or a lesson, ' +
      'so they enter the SM-2 queue. Provide Cyrillic word, English translation, and an optional example sentence each.',
    input_schema: {
      type: 'object',
      properties: {
        words: {
          type: 'array',
          description: 'Words to add',
          items: {
            type: 'object',
            properties: {
              word: { type: 'string', description: 'Russian word/phrase in Cyrillic' },
              translation: { type: 'string', description: 'English meaning' },
              example: { type: 'string', description: 'Optional example sentence' },
            },
            required: ['word', 'translation'],
          },
        },
      },
      required: ['words'],
    },
  },
  {
    name: 'russian_log_practice',
    description:
      'Log a Russian practice session after the user studies, to update minutes-today and the daily streak. ' +
      'kind is the activity type. Call at the end of a lesson, conversation, or review session.',
    input_schema: {
      type: 'object',
      properties: {
        minutes: { type: 'number', description: 'Minutes practiced' },
        kind: { type: 'string', enum: ['lesson', 'conversation', 'review', 'grammar', 'reading'] },
      },
      required: ['minutes'],
    },
  },
  {
    name: 'russian_next',
    description:
      'Get the single recommended next action for the user (review due cards, or which lesson to start next), plus due-review count and streak. ' +
      'Call when the user asks "what\'s next" or you need to decide what to do this session.',
    input_schema: { type: 'object', properties: {} },
  },
];

const handlers = {
  russian_progress: async () => getProgress(),
  russian_curriculum: async () => getCurriculum(),
  russian_lesson: ({ id }) => getLesson(id),
  russian_alphabet: async () => getAlphabet(),
  russian_start_lesson: ({ id }) => startLesson(id),
  russian_complete_lesson: ({ id, score }) => completeLesson({ id, score }),
  russian_set_level: ({ level }) => setLevel(level),
  russian_add_vocab: ({ words }) => addVocabBatch({ words }),
  russian_log_practice: ({ minutes, kind }) => logPractice({ minutes, kind }),
  russian_next: async () => nextAction(),
};

// ===========================================================================
// SYSTEM PROMPT — ARIA as a dedicated CEFR Russian tutor running a program.
// ===========================================================================
const systemPromptFragment =
  'You are also a dedicated, CEFR-aligned RUSSIAN tutor running a structured program from A1 to C2 and on to fluency. ' +
  'ORIENT first: call russian_progress (and russian_next) to see the user\'s level, current/next lesson, streak, and due reviews before deciding what to do. ' +
  'TEACH each lesson interactively: pull it with russian_lesson, explain the grammar focus simply and concretely, give Russian examples, then quiz and drill — do not just lecture. ' +
  'Correct mistakes gently and ALWAYS say WHY (which case, which aspect, which ending). Relentlessly drill the hard parts of Russian: the six cases, verb aspect (imperfective vs. perfective), conjugation, and verbs of motion. ' +
  'Build vocabulary with spaced repetition: call russian_add_vocab as new words come up so they enter SM-2 review, and remind the user to clear their due cards (russian_next reports how many are due). ' +
  'CONVERSE in Russian at the user\'s level, nudging difficulty up over time and shifting to more Russian as they advance. ' +
  'ALWAYS show Cyrillic. For A1–A2 include transliteration AND English; phase out romanization at B1+ (keep English glosses for new/hard words only) — respect the user\'s showRomanization setting. ' +
  'When voice is on, speak short Russian phrases aloud so the user hears pronunciation. Be warm and encouraging, and push the user slightly past their comfort zone. ' +
  'TRACK progress: call russian_start_lesson when they begin a lesson, russian_complete_lesson (with a 0–100 score from your drills) when they finish, and russian_log_practice after any session; then tell the user exactly what is next. ' +
  'Use russian_alphabet for reading/pronunciation work and russian_curriculum to show the path. Keep replies tight and conversational — they may be read aloud.';

module.exports = {
  name: 'russian',
  systemPromptFragment,
  tools,
  handlers,
  // Direct API for UI panels / IPC (no AI brain needed).
  api: {
    getProgress,
    getCurriculum,
    getLesson,
    getAlphabet,
    startLesson,
    completeLesson,
    setLevel,
    addVocabBatch,
    seedVocab,
    logPractice,
    setSettings,
    reviewQueue,
    nextAction,
    // Handy extras for the UI:
    levels: LEVELS,
    seedThemes: SEED_THEMES,
  },
};
