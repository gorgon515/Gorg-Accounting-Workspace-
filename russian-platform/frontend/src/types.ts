export interface User {
  id: number;
  email: string;
  display_name: string;
  cefr_estimate: string;
  xp: number;
  level: number;
  streak_days: number;
  daily_goal_minutes: number;
  ui_immersion_ratio: number;
  preferences: Record<string, unknown>;
}

export interface Quest {
  slug: string;
  title: string;
  title_native: string;
  description: string;
  target: number;
  xp: number;
  icon: string;
  progress: number;
  complete: boolean;
  claimed: boolean;
}

export interface ForecastDay {
  date: string;
  due: number;
}

export interface LexemeSummary {
  id: number;
  lemma: string;
  stressed: string;
  ipa: string;
  transliteration: string;
  part_of_speech: string;
  cefr_level: string;
  frequency_rank: number | null;
  register: string;
  domain: string;
  translation: string;
}

export interface LexemeDetail extends LexemeSummary {
  literal_translation: string | null;
  meanings: string[];
  root: string | null;
  aspect: string | null;
  aspect_partner: string | null;
  gender: string | null;
  inflections: Record<string, Record<string, string>>;
  government: { case?: string; preposition?: string; meaning: string }[];
  mnemonic: string | null;
  usage_notes: string | null;
  cultural_notes: string | null;
  common_mistakes: string[];
  examples: { text: string; translation: string }[];
  relations: { type: string; target: string; note: string | null }[];
}

export interface AlphabetLetter {
  letter: string;
  name: string;
  ipa: string;
  type: string;
  translit: string;
  note: string;
  example: { word: string; translation: string };
}

export interface GrammarTopicSummary {
  slug: string;
  title: string;
  title_native: string;
  cefr_level: string;
  summary: string;
  has_content: boolean;
  drill_count: number;
  prerequisites: string[];
  mastery: number;
}

export interface CourseInfo {
  slug: string;
  title: string;
  cefr_level: string;
  description: string;
  track: string;
  prerequisite_slug: string | null;
  lessons: {
    slug: string;
    title: string;
    order_index: number;
    objectives: string[];
    passed: boolean;
    unlocked: boolean;
  }[];
}

export interface LessonBlock {
  type: string;
  [key: string]: unknown;
}

export interface ReviewCard {
  card_id: number;
  state: string;
  direction: string;
  lexeme: {
    id: number;
    lemma: string;
    stressed: string;
    ipa: string;
    transliteration: string;
    translation: string;
    part_of_speech: string;
    mnemonic: string | null;
    examples: { text: string; translation: string }[];
  };
}

export interface Scenario {
  slug: string;
  title: string;
  persona: string;
  setting: string;
  cefr_level: string;
  description: string;
  key_vocabulary: string[];
}

export interface PartnerReply {
  text: string;
  translation: string | null;
  corrections: { error: string; correction: string; explanation: string }[];
  hints: string[];
  completed?: boolean;
}

export interface Dashboard {
  cefr: {
    level: string;
    progress_to_next: number;
    known_words: number;
    lessons_passed: number;
  };
  xp: { level: number; xp_in_level: number; xp_for_next: number };
  streak_days: number;
  vocabulary: {
    known_words: number;
    card_states: Record<string, number>;
    due_now: number;
    predicted_retention: number | null;
  };
  reviews_7d: { total: number; accuracy: number | null; ratings: Record<string, number> };
  weak_grammar: { slug: string; title: string; mastery: number }[];
  time_studied_7d_minutes: number;
  activity: Record<string, number>;
  achievements: { slug: string; title: string; icon: string; earned_at: string }[];
}
