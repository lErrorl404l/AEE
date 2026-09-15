import re, sys, json, glob, os

MARKETING = [
    "seamless",
    "seamlessly",
    "robust",
    "powerful",
    "cutting-edge",
    "effortless",
    "effortlessly",
    "world-class",
    "next-generation",
    "revolutionary",
    "blazing",
    "lightning-fast",
    "elegant",
    "delightful",
    "turnkey",
    "best-in-class",
    "state-of-the-art",
    "game-changing",
    "first-class",
    "battle-tested",
    "enterprise-grade",
    "supercharge",
    "unlock",
    "unleash",
    "empower",
    "empowers",
]
BANNED = [
    "begin",
    "begins",
    "commence",
    "commences",
    "initiate",
    "initiates",
    "originate",
    "utilize",
    "utilizes",
    "utilizing",
    "utilise",
    "license",
    "licenses",
    "colorful",
    "defenseless",
    "honorable",
    "theater",
    "fiber",
    "labeling",
    "traveling",
    "centering",
    "offense",
    "practiced",
    "utilises",
    "utilised",
    "utilising",
    "utilisation",
    "leverage",
    "leverages",
    "leveraging",
    "facilitate",
    "facilitates",
    "ensure",
    "ensures",
    "ensuring",
    "prior to",
    "subsequent to",
    "obtain",
    "obtains",
    "acquire",
    "acquires",
    "regarding",
    "concerning",
    "demonstrate",
    "demonstrates",
    "additionally",
    "furthermore",
    "moreover",
    "comprehensive",
    "comprehensively",
    "utilization",
    "aforementioned",
    # American spellings (British -ise/-yse/-our/-re mandated; see instructions.md)
    "organize",
    "organizes",
    "organized",
    "organizing",
    "organization",
    "organizations",
    "analyze",
    "analyzes",
    "analyzed",
    "analyzing",
    "realize",
    "realizes",
    "realized",
    "realizing",
    "recognize",
    "recognizes",
    "recognized",
    "recognizing",
    "emphasize",
    "emphasizes",
    "emphasized",
    "emphasizing",
    "maximize",
    "maximizes",
    "maximized",
    "maximizing",
    "minimize",
    "minimizes",
    "minimized",
    "minimizing",
    "optimize",
    "optimizes",
    "optimized",
    "optimizing",
    "prioritize",
    "prioritizes",
    "prioritized",
    "prioritizing",
    "customize",
    "customizes",
    "customized",
    "customizing",
    "summarize",
    "summarizes",
    "summarized",
    "summarizing",
    "specialize",
    "specializes",
    "specialized",
    "specializing",
    "categorize",
    "categorizes",
    "categorized",
    "categorizing",
    "authorize",
    "authorizes",
    "authorized",
    "authorizing",
    "characterize",
    "characterizes",
    "characterized",
    "characterizing",
    "generalize",
    "generalizes",
    "generalized",
    "generalizing",
    "formalize",
    "formalizes",
    "formalized",
    "formalizing",
    "normalize",
    "normalizes",
    "normalized",
    "normalizing",
    "initialize",
    "initializes",
    "initialized",
    "initializing",
    "standardize",
    "standardizes",
    "standardized",
    "standardizing",
    "visualize",
    "visualizes",
    "visualized",
    "visualizing",
    "finalize",
    "finalizes",
    "finalized",
    "finalizing",
    "familiarize",
    "familiarizes",
    "familiarized",
    "familiarizing",
    "fulfill",
    "fulfills",
    "fulfilling",
    "fulfillment",
    "program",
    "programs",
    "authorization",
    "authorizations",
    "reauthorization",
    "specialization",
    "specializations",
    "categorization",
    "categorizations",
    "realization",
    "realizations",
    "normalization",
    "normalizations",
    "standardization",
    "standardizations",
    "optimization",
    "optimizations",
    "customization",
    "customizations",
    "initialization",
    "initializations",
    "generalization",
    "generalizations",
    "formalization",
    "formalizations",
    "visualization",
    "visualizations",
    "finalization",
    "finalizations",
    "familiarization",
    "familiarizations",
    "minimization",
    "minimizations",
    "maximization",
    "maximizations",
    "prioritization",
    "prioritizations",
    "color",
    "colors",
    "colored",
    "coloring",
    "defense",
    "behavior",
    "behaviors",
    "center",
    "centers",
    "centered",
    "labor",
    "favorite",
    "honor",
    "honored",
    "modeling",
    "canceled",
    "canceling",
    "gray",
    "henceforth",
    "therein",
    "whilst",
    "amongst",
    "numerous",
    "myriad",
    "plethora",
    "in order to",
    "a variety of",
    "in the event that",
    "due to the fact that",
]
PHRASAL = [
    "spin up",
    "spin down",
    "reach out",
    "dive into",
    "dives into",
    "diving into",
    "kick off",
    "kicks off",
    "roll out",
    "rolls out",
    "tear down",
    "ramp up",
    "circle back",
    "drill down",
    "spun up",
    "reaching out",
]
MODAL_HEDGE = [
    "it is important to note",
    "it should be noted",
    "it is worth noting",
    "please note that",
    "as mentioned",
    "as noted above",
]
BE = r"(?:am|is|are|was|were|be|been|being)"
PP_IRREG = r"(?:done|made|sent|read|built|kept|held|set|put|run|written|shown|given|taken|found|got|gotten|seen|known|thrown|drawn)"


def strip_code(t):
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"`[^`]*`", " ", t)
    # Handbook-first: blockquotes hold verbatim quoted material, and the
    # writers-handbook forbids changing quotes. Exempt them from linting.
    t = re.sub(r"(?m)^\s*>\s?.*$", " ", t)
    return t


def sentences(text):
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^\s*#{1,6}\s*", "", s)
        s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)
        if not s:
            continue
        parts = re.split(r"(?<=[.!?:])\s+(?=[A-Z0-9\"'\-])", s)
        for p in parts:
            p = p.strip()
            if p:
                out.append(p)
    return out


def wc(s):
    return len([w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-/]*", s)])


def count_ci(text, phrases):
    n = 0
    hits = []
    low = text.lower()
    for ph in phrases:
        for m in re.finditer(r"(?<![a-z])" + re.escape(ph) + r"(?![a-z])", low):
            n += 1
            hits.append(ph)
    return n, hits


def bullet_semicolons(text):
    """MOD Writers' Handbook: continuous bullet lists end each item with a
    semicolon (final item ends with a full stop). Table cells, numbered
    items, and wrapped bullet continuations also use semicolons as item
    separators. Do not count semicolons on any of these lines."""
    n = 0
    for line in text.split("\n"):
        s = line.strip()
        if re.match(r"^(?:[-*+]|\d+[.)])\s+", s) and s.rstrip().endswith(";"):
            n += 1
            continue
        # Table rows and any line that is a list item or continuation
        if re.match(r"^\|", s) and ";" in s:
            n += s.count(";")
            continue
        if (
            re.match(r"^\s", line)
            and ";" in line
            and re.match(r"^\s*(?:[-*+]|\d+[.)])", line)
        ):
            n += line.count(";")
    return n


def lint(text):
    # YAML front matter (---...---) is structured metadata, not prose.
    # It carries required fields such as title, author, and reference
    # that no STE gate should count. Strip it before any counting.
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    raw = text
    text = strip_code(text)
    sents = sentences(text)
    words = sum(wc(s) for s in sents) or 1
    v = {}
    longs = [(wc(s), s) for s in sents if wc(s) > 20]
    v["long_sentence(>20w)"] = len(longs)
    # Handbook-first: semicolon-terminated bullets are the MOD-mandated form
    v["semicolon"] = text.count(";") - bullet_semicolons(raw)
    # Handbook-first: possessive apostrophes are permitted ('Apostrophes:
    # Possession only'). Flag only clear contractions: 's after a pronoun,
    # and t/re/ve/ll/d/m after any word.
    v["contraction"] = len(
        re.findall(
            r"\b(?:it|that|there|he|she|who|what|how|let)['’]s\b|\b\w+['’](?:t|re|ve|ll|d|m)\b",
            text,
        )
    )
    v["passive_voice"] = len(
        re.findall(rf"\b{BE}\s+(?:\w+ed|{PP_IRREG})\b", text, re.I)
    )
    v["ing_main_verb"] = len(re.findall(rf"\b{BE}\s+\w+ing\b", text, re.I))
    v["nominalization"] = len(
        re.findall(
            r"\b(?:perform(?:s|ed)?|conduct(?:s|ed)?|provide(?:s|d)?|carry out|carries out|make use of|makes use of)\b",
            text,
            re.I,
        )
    ) + len(re.findall(r"\b\w{4,}(?:tion|ment|ance|ence)\s+of\b", text, re.I))
    v["phrasal_verb"], _ = count_ci(text, PHRASAL)
    v["banned_word"], bh = count_ci(text, BANNED)
    v["marketing_adjective"], mh = count_ci(text, MARKETING)
    v["modal_hedge"], _ = count_ci(text, MODAL_HEDGE)
    paras = [p for p in re.split(r"\n\s*\n", raw) if p.strip()]
    v["long_paragraph(>6s)"] = sum(
        1 for p in paras if len(sentences(strip_code(p))) > 6
    )
    # Handbook-first: en dash ( - ) with spaces is the MOD-mandated form.
    # Flag only em dashes (U+2014), which instructions.md says to avoid.
    em = raw.count("—")
    total = sum(v.values())
    per100 = {k: round(x * 100.0 / words, 2) for k, x in v.items()}
    return {
        "words": words,
        "sentences": len(sents),
        "violations": v,
        "total": total,
        "total_per100w": round(total * 100.0 / words, 2),
        "em_dash(slop-marker)": em,
        "longest_sentence_words": (
            max(longs)[0] if longs else max((wc(s) for s in sents), default=0)
        ),
        "sample_marketing": list(dict.fromkeys(mh))[:6],
        "sample_banned": list(dict.fromkeys(bh))[:6],
    }


if __name__ == "__main__":
    files = sys.argv[1:] or []
    threshold = None
    # Gate: default threshold 4.0/100w. Intended for the 42 briefs in
    # rules/briefs/*.md. Wordlist and skill reference files score far
    # higher by design (they must name the words they ban); do not gate
    # them with --gate.
    if "--gate" in files:
        files.remove("--gate")
        threshold = 4.0
    for i, a in enumerate(files):
        if a.startswith("--threshold="):
            threshold = float(a.split("=", 1)[1])
            files.pop(i)
            break
    if not files:
        print(json.dumps(lint(sys.stdin.read()), indent=2))
        sys.exit(0)
    exp = []
    for f in files:
        exp += sorted(glob.glob(f)) if any(c in f for c in "*?[") else [f]
    failed = []
    for f in exp:
        with open(f) as fh:
            r = lint(fh.read())
        print(
            f"{os.path.basename(f):32} words={r['words']:4d} total={r['total']:3d} per100w={r['total_per100w']:6.2f} em_dash={r['em_dash(slop-marker)']:2d}"
        )
        if threshold is not None and r["total_per100w"] > threshold:
            failed.append((f, r["total_per100w"]))
    if threshold is not None and failed:
        print()
        print(f"GATE FAILED: {len(failed)} file(s) above {threshold}/100w:")
        for f, p in failed:
            print(f"  {f}: {p}")
        sys.exit(1)
    if threshold is not None:
        print(f"GATE PASSED: all files at or below {threshold}/100w")
