"""Morphology engine: verified against known dictionary forms."""
import pytest

from app.services import morphology as m
from app.services.vocab_factory import build_all, build_entry
from app.seed.wordlist import W


class TestTransliteration:
    def test_basic(self):
        assert m.transliterate("молоко́") == "moloko"
        assert m.transliterate("щи") == "shchi"
        assert m.transliterate("объе́кт") == 'ob"yekt'.replace("ye", "e")


class TestIPA:
    @pytest.mark.parametrize(
        "word,expected",
        [
            ("молоко́", "[məɫɐˈko]"),
            ("говори́ть", "[ɡəvɐˈrʲitʲ]"),
            ("хлеб", "[xlʲep]"),  # final devoicing б→p, no ˈ on monosyllables
            ("го́род", "[ˈɡorət]"),  # final devoicing д→t, reduction
        ],
    )
    def test_known_words(self, word, expected):
        assert m.to_ipa(word) == expected

    def test_stress_marked_on_polysyllables_only(self):
        assert "ˈ" not in m.to_ipa("дом")
        assert "ˈ" in m.to_ipa("доро́га")


class TestNounDeclension:
    def test_feminine_a(self):
        d = m.decline_noun("кни́га", "f")
        assert d["gen_sg"] == "кни́ги"  # 7-letter rule: и after г
        assert d["acc_sg"] == "кни́гу"
        assert d["ins_sg"] == "кни́гой"

    def test_masculine_consonant_inanimate(self):
        d = m.decline_noun("вопро́с", "m")
        assert d["gen_sg"] == "вопро́са"
        assert d["acc_sg"] == "вопро́с"  # inanimate: acc = nom
        assert d["gen_pl"] == "вопро́сов"

    def test_masculine_animate_acc_equals_gen(self):
        d = m.decline_noun("студе́нт", "m", animacy="animate")
        assert d["acc_sg"] == d["gen_sg"] == "студе́нта"

    def test_neuter_end_stressed(self):
        d = m.decline_noun("окно́", "n")
        assert d["gen_sg"] == "окна́"
        assert d["pre_sg"] == "окне́"

    def test_feminine_soft_sign(self):
        d = m.decline_noun("дверь", "f")
        assert d["gen_sg"] == "две́ри"
        assert d["ins_sg"] == "две́рью"

    def test_overrides_win(self):
        d = m.decline_noun("рука́", "f", overrides={"acc_sg": "ру́ку"})
        assert d["acc_sg"] == "ру́ку"


class TestAdjectiveDeclension:
    def test_hard_stem(self):
        assert m.decline_adjective("но́вый") == {
            "m": "но́вый", "f": "но́вая", "n": "но́вое", "pl": "но́вые"
        }

    def test_end_stressed_oj(self):
        forms = m.decline_adjective("большо́й")
        assert forms["f"] == "больша́я"
        assert forms["pl"] == "больши́е"

    def test_velar_stem_takes_ie_plural(self):
        assert m.decline_adjective("высо́кий")["pl"] == "высо́кие"


class TestVerbConjugation:
    def test_first_conjugation_keeps_stem_stress(self):
        present = m.conjugate_verb("чита́ть")["present"]
        assert present["я"] == "чита́ю"
        assert present["они"] == "чита́ют"

    def test_second_conjugation_end_stress(self):
        present = m.conjugate_verb("говори́ть")["present"]
        assert present == {
            "я": "говорю́", "ты": "говори́шь", "он": "говори́т",
            "мы": "говори́м", "вы": "говори́те", "они": "говоря́т",
        }

    def test_ovat_verbs(self):
        assert m.conjugate_verb("рисова́ть")["present"]["я"] == "рису́ю"
        assert m.conjugate_verb("танцева́ть")["present"]["я"] == "танцу́ю"

    def test_husher_spelling_rule(self):
        present = m.conjugate_verb("учи́ть")["present"]
        assert present["я"] == "учу́"  # у not ю after ч
        assert present["они"] == "у́чат" or present["они"] == "уча́т"  # ат not ят

    def test_reflexive(self):
        present = m.conjugate_verb("занима́ться")["present"]
        assert present["я"] == "занима́юсь"  # -сь after vowel
        assert present["ты"] == "занима́ешься"  # -ся after consonant

    def test_past_tense(self):
        past = m.conjugate_verb("рабо́тать")["past"]
        assert past == {"m": "рабо́тал", "f": "рабо́тала", "n": "рабо́тало",
                        "pl": "рабо́тали"}

    def test_override_merges_single_form(self):
        present = m.conjugate_verb("плати́ть", {"present": {"я": "плачу́"}})["present"]
        assert present["я"] == "плачу́"
        assert present["ты"] == "плати́шь"  # rest still generated


class TestVocabFactory:
    def test_wordlist_builds_clean(self):
        entries = build_all(W)
        assert len(entries) >= 450
        for entry in entries:
            assert entry["lemma"] and entry["stressed"]
            assert entry["ipa"].startswith("[")
            assert entry["transliteration"]
            assert entry["topic"] != ""
            assert entry["difficulty"] >= 1.0
            if entry["part_of_speech"] == "noun":
                assert entry["gender"] in ("m", "f", "n")

    def test_ambiguous_gender_rejected(self):
        with pytest.raises(ValueError, match="ambiguous"):
            build_entry(("тень", "n", "shadow", "nature", "B1"))

    def test_duplicate_lemma_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            build_all([("дом", "n", "house", "home", "A1"),
                       ("дом", "n", "house", "home", "A1")])

    def test_no_overlap_with_curated_core(self):
        from app.seed.vocabulary_core import VOCABULARY

        core = {v["lemma"] for v in VOCABULARY}
        expanded = {e["lemma"] for e in build_all(W)}
        assert not core & expanded, core & expanded
