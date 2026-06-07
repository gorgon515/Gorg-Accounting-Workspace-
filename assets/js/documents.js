/* Verum Advisory — client document register. Rendered by document.html.
   Demonstration content only; no real client data. */
window.VERUM_DOCS = {
  order: [
    "structure-memorandum",
    "treaty-position",
    "entity-chart",
    "engagement-letter",
    "statement-2026-014",
    "statement-2025-061",
    "statement-2025-048"
  ],
  items: {
    "structure-memorandum": {
      kind: "Memorandum", ref: "DOC-2025-0114", date: "14 NOV 2025",
      title: "Cross-Border Structure Memorandum",
      body: [
        "This memorandum summarizes the current holding structure and the tax positions taken in respect of it.",
        "HoldCo (Luxembourg) holds three operating entities: OpCo (United States), IP Co (Ireland), and Fin Co (Netherlands). Treaty access has been analyzed for each intercompany flow and documented contemporaneously with the structure.",
        "No positions remain open. The structure is documented to withstand examination in each relevant jurisdiction."
      ]
    },
    "treaty-position": {
      kind: "Supporting Documentation", ref: "DOC-2025-0119", date: "19 NOV 2025",
      title: "Treaty Position — Supporting Documentation",
      body: [
        "Beneficial-ownership analysis and treaty-access support for the holding structure, prepared at the time the structure was established.",
        "Each position is supported by contemporaneous board minutes, the governing intercompany agreements, and the relevant treaty articles relied upon.",
        "Prepared to be read by an examiner without a meeting."
      ]
    },
    "entity-chart": {
      kind: "Entity Chart", ref: "DOC-2025-0090", date: "02 OCT 2025",
      title: "Entity Chart — Current Holding Structure",
      body: [
        "HOLDCO (LU)",
        "  ├─ OPCO (US) ─ BRANCH",
        "  ├─ IP CO (IE)",
        "  └─ FIN CO (NL) ─ TREATY",
        "Current as of the date above. Changes are reflected within one business day of execution."
      ],
      pre: true
    },
    "engagement-letter": {
      kind: "Engagement Letter", ref: "DOC-2025-0061", date: "08 SEP 2025",
      title: "Engagement Letter (Executed)",
      body: [
        "This letter confirms the terms of engagement between Verum Advisory Group, Inc. and the named client.",
        "The partners work every file. There are no hand-offs. Advice is delivered before decisions are made, and positions are documented as taken.",
        "Executed by both parties. A countersigned copy is retained on file."
      ]
    },
    "statement-2026-014": {
      kind: "Statement", ref: "INV-2026-014", date: "31 MAR 2026",
      title: "Statement — Q1 2026 Advisory",
      lines: [
        ["Cross-border advisory — Q1 2026", "$48,000"],
        ["Treaty documentation review", "$12,000"],
        ["Less: retainer applied", "($60,000)"]
      ],
      total: "$0.00",
      body: ["Advisory services for the first quarter of 2026, itemized above. Settled in full against the standing retainer."]
    },
    "statement-2025-061": {
      kind: "Statement", ref: "INV-2025-061", date: "31 DEC 2025",
      title: "Statement — Q4 2025 Advisory",
      lines: [
        ["Cross-border advisory — Q4 2025", "$52,000"],
        ["Structure memorandum", "$8,000"],
        ["Less: retainer applied", "($60,000)"]
      ],
      total: "$0.00",
      body: ["Advisory services for the fourth quarter of 2025. Settled in full."]
    },
    "statement-2025-048": {
      kind: "Statement", ref: "INV-2025-048", date: "30 SEP 2025",
      title: "Statement — Transaction Engagement",
      lines: [
        ["Transaction advisory — structuring", "$120,000"],
        ["Step-plan and documentation", "$35,000"],
        ["Less: deposit applied", "($155,000)"]
      ],
      total: "$0.00",
      body: ["Fees for the transaction engagement concluded in Q3 2025. Settled in full."]
    }
  }
};
