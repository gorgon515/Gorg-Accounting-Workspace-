"""Import pipeline validation tests."""
from app.services.content_import import (
    apply_texts,
    apply_vocabulary,
    validate_text_dataset,
    validate_vocabulary_dataset,
)

GOOD_WORD = ["тень", "n", "shadow", "nature", "B1", {"gender": "f"}]


class TestVocabularyValidation:
    def test_valid_row_builds_full_entry(self, db_session):
        report = validate_vocabulary_dataset([GOOD_WORD], db_session)
        assert report.ok, report.errors
        entry = report.valid_items[0]
        assert entry["lemma"] == "тень"
        assert entry["inflections"]["declension"]["ins_sg"]

    def test_missing_stress_mark_rejected(self, db_session):
        report = validate_vocabulary_dataset(
            [["собрание", "n", "meeting", "work", "B1"]], db_session
        )
        assert not report.ok
        assert "stress mark" in report.errors[0]

    def test_yo_counts_as_stress(self, db_session):
        report = validate_vocabulary_dataset(
            [["стёкла", "n", "panes", "home", "B2", {"gender": "n",
              "inflections": {"declension": {"nom_pl": "стёкла"}}}]], db_session
        )
        assert report.ok, report.errors

    def test_bad_pos_and_cefr_rejected(self, db_session):
        report = validate_vocabulary_dataset(
            [["тень", "noun", "shadow", "nature", "B1"],
             ["тень", "n", "shadow", "nature", "Z9"]], db_session
        )
        assert len(report.errors) == 2

    def test_ambiguous_soft_sign_gender_rejected(self, db_session):
        report = validate_vocabulary_dataset(
            [["тень", "n", "shadow", "nature", "B1"]], db_session  # no gender
        )
        assert not report.ok
        assert "ambiguous" in report.errors[0]

    def test_existing_lemma_becomes_warning_not_error(self, db_session):
        report = validate_vocabulary_dataset(
            [["дом", "n", "house", "home", "A1"]], db_session
        )
        assert report.ok
        assert report.warnings and "already in database" in report.warnings[0]
        assert report.valid_items == []

    def test_duplicate_within_dataset_rejected(self, db_session):
        report = validate_vocabulary_dataset([GOOD_WORD, GOOD_WORD], db_session)
        assert not report.ok

    def test_apply_inserts_and_is_queryable(self, db_session, client, auth_headers):
        report = validate_vocabulary_dataset(
            [["тень", "n", "shadow", "nature", "B1",
              {"gender": "f", "examples": [["В тени́ прохла́дно.", "It is cool in the shade."]]}]],
            db_session,
        )
        assert report.ok
        assert apply_vocabulary(db_session, report.valid_items) == 1
        found = client.get("/api/v1/vocabulary?q=shadow", headers=auth_headers).json()
        assert found["total"] == 1
        detail = client.get(f"/api/v1/vocabulary/{found['items'][0]['id']}",
                            headers=auth_headers).json()
        assert detail["examples"][0]["translation"].startswith("It is cool")


class TestTextValidation:
    GOOD_TEXT = {
        "slug": "test-recipe", "title": "Борщ", "title_translation": "Borscht",
        "kind": "recipe", "cefr_level": "A2", "summary": "How to make borscht.",
        "sentences": [
            {"ru": "Снача́ла вари́м бульо́н.", "en": "First we cook the broth."},
            {"ru": "Пото́м добавля́ем свёклу.", "en": "Then we add the beets."},
            {"ru": "Гото́вим ещё час.", "en": "Cook for another hour."},
        ],
    }

    def test_valid_text_accepted_and_applied(self, db_session, client, auth_headers):
        report = validate_text_dataset([self.GOOD_TEXT], db_session)
        assert report.ok, report.errors
        assert apply_texts(db_session, report.valid_items) == 1
        texts = client.get("/api/v1/library/texts?kind=recipe",
                           headers=auth_headers).json()
        assert texts[0]["slug"] == "test-recipe"
        assert texts[0]["word_count"] == 9

    def test_too_few_sentences_rejected(self, db_session):
        bad = {**self.GOOD_TEXT, "slug": "x", "sentences": self.GOOD_TEXT["sentences"][:2]}
        report = validate_text_dataset([bad], db_session)
        assert not report.ok

    def test_missing_translation_rejected(self, db_session):
        bad = {**self.GOOD_TEXT, "slug": "y",
               "sentences": [{"ru": "Приве́т.", "en": ""}] * 3}
        report = validate_text_dataset([bad], db_session)
        assert not report.ok

    def test_unknown_kind_rejected(self, db_session):
        report = validate_text_dataset([{**self.GOOD_TEXT, "kind": "podcast"}], db_session)
        assert not report.ok

    def test_existing_slug_is_warning(self, db_session):
        report = validate_text_dataset([{**self.GOOD_TEXT, "slug": "repka"}], db_session)
        assert report.ok and report.warnings
