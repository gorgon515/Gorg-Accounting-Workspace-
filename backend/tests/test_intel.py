import unittest

from accounting.parsers import feeds
from accounting.schemas import (
    IntelItem, classify, DocType, extract_asc_codes, extract_asu_number,
)
from accounting.collectors.sec import SECCollector
from accounting.collectors.base import run_all
from accounting.storage.db import IntelStore

# Real-format fixtures (the shapes SEC/FASB actually publish). Used only in tests.
RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>SEC Press</title>
<item>
  <title>SEC Adopts Final Rule on Climate Disclosures</title>
  <link>https://www.sec.gov/news/press-release/2025-10</link>
  <description>The Commission today adopted rules effective for fiscal years beginning after December 15, 2025.</description>
  <pubDate>Mon, 06 Jan 2025 14:00:00 GMT</pubDate>
  <guid>https://www.sec.gov/news/press-release/2025-10</guid>
</item>
<item>
  <title>SEC Proposes Amendments to Reporting</title>
  <link>https://www.sec.gov/news/press-release/2025-11</link>
  <description>Proposing release on disclosure.</description>
  <pubDate>Tue, 07 Jan 2025 14:00:00 GMT</pubDate>
  <guid>https://www.sec.gov/news/press-release/2025-11</guid>
</item>
</channel></rss>"""

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>FASB ASU</title>
<entry>
  <title>ASU 2025-03, Revenue from Contracts with Customers (ASC 606)</title>
  <link href="https://www.fasb.org/asu/2025-03" rel="alternate"/>
  <summary>Amends ASC 606 and is effective for fiscal years beginning after December 15, 2025.</summary>
  <updated>2025-02-10T00:00:00Z</updated>
  <id>tag:fasb.org,2025:asu-2025-03</id>
</entry></feed>"""


class FeedParseTest(unittest.TestCase):
    def test_rss(self):
        entries = feeds.parse(RSS)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["title"], "SEC Adopts Final Rule on Climate Disclosures")
        self.assertTrue(entries[0]["link"].startswith("https://www.sec.gov"))

    def test_atom(self):
        entries = feeds.parse(ATOM)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["link"], "https://www.fasb.org/asu/2025-03")
        self.assertIn("ASC 606", entries[0]["title"])

    def test_garbage_returns_empty(self):
        self.assertEqual(feeds.parse("<not xml"), [])
        self.assertEqual(feeds.parse(""), [])


class SchemaTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("ASU 2025-03 Revenue"), DocType.ASU)
        self.assertEqual(classify("Exposure Draft on Leases"), DocType.EXPOSURE_DRAFT)
        self.assertEqual(classify("Revenue Ruling 2025-5"), DocType.REVENUE_RULING)

    def test_extractors(self):
        self.assertEqual(extract_asc_codes("amends ASC 606 and ASC842"), ["606", "842"])
        self.assertEqual(extract_asu_number("ASU 2025-03, Revenue"), "2025-03")

    def test_from_feed_entry_effective_date(self):
        item = IntelItem.from_feed_entry("FASB", feeds.parse(ATOM)[0], DocType.ASU)
        self.assertEqual(item.source, "FASB")
        self.assertEqual(item.doc_type, DocType.ASU.value)
        self.assertEqual(item.asc_codes, ["606"])
        self.assertEqual(item.asu_number, "2025-03")
        self.assertEqual(item.effective_date, "2025-12-15")
        self.assertTrue(item.id)  # stable id present


class CollectorTest(unittest.TestCase):
    def test_collect_from_xml(self):
        items = SECCollector().collect_from_xml(RSS, DocType.SEC_RELEASE)
        self.assertEqual(len(items), 2)
        self.assertTrue(all(i.source == "SEC" for i in items))
        # Title-based reclassification: the proposing release is a Proposed Rule.
        kinds = {i.title: i.doc_type for i in items}
        self.assertEqual(kinds["SEC Proposes Amendments to Reporting"], DocType.PROPOSED_RULE.value)


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.store = IntelStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_dedup_and_query(self):
        items = SECCollector().collect_from_xml(RSS, DocType.SEC_RELEASE)
        items += [IntelItem.from_feed_entry("FASB", feeds.parse(ATOM)[0], DocType.ASU)]
        r1 = self.store.upsert_many(items)
        self.assertEqual(r1["inserted"], 3)
        # Re-running collects the same items → no new inserts (dedup by stable id).
        r2 = self.store.upsert_many(items)
        self.assertEqual(r2["inserted"], 0)
        self.assertEqual(r2["updated"], 3)
        self.assertEqual(self.store.count(), 3)
        self.assertEqual(len(self.store.query(source="SEC")), 2)

    def test_upcoming_effective(self):
        self.store.upsert_many([IntelItem.from_feed_entry("FASB", feeds.parse(ATOM)[0], DocType.ASU)])
        upcoming = self.store.upcoming_effective(today="2025-01-01")
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0]["effective_date"], "2025-12-15")
        # Nothing effective after the date itself.
        self.assertEqual(self.store.upcoming_effective(today="2026-01-01"), [])


class RunAllTest(unittest.TestCase):
    def test_errors_dont_crash(self):
        # No network in this sandbox → collectors raise SourceUnavailable, captured per-source.
        items, errors = run_all([SECCollector()])
        self.assertIsInstance(items, list)
        self.assertIsInstance(errors, dict)


if __name__ == "__main__":
    unittest.main()
