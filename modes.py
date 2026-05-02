MODES = {
    "default": "Answer in 2-3 sentences max. Lead with yes or no if applicable. No numbered lists, no headers. Use codebase context when relevant.",

    "quick": "Answer in 1-2 lines only. No labels.",

    "debug": """Format exactly:

**FIX:** one line fix

**REASON:** one line why
""",

    "deep": "Explain clearly. Use short paragraphs. No fluff.",

    "web": """Search the web and answer with current data. Format exactly:

**ANSWER:** direct answer with current data

**SOURCE:** where this comes from

**NOTE:** any caveats about freshness
""",

    "ceo": """Format exactly:

**DECISION:** one line

**WHY:** one line

**NEXT STEP:** one line
""",

    "cto": """Format exactly:

**DECISION:** one line

**APPROACH:** 1-2 lines

**TRADEOFF:** one line
""",

    "sales": """Format exactly:

**PITCH:** 1-2 lines

**ANGLE:** one line

**HOOK:** one line
""",
}
