# PDAiS — **Pre-Digested Ai Structuring**
**Named by Keith, 2026-08-01.** The discipline of preparing a document corpus so that an AI reads
the *record* rather than a distortion of it.

> *"We need a name for that whole process of 'predigestion' for Ai consumption and some guidelines
> for optimum process."* — Keith, 2026-08-01

**Why it needs a name:** every serious failure in the Abraxas legal session came from corpus defects,
not model defects. A corpus that triple-weights a document, that silently drops six pleadings, or
that feeds our own conclusions back to us produces confident, well-cited, wrong answers. **The prompt
is the fix, but only after the corpus is.**

---

## THE SEVEN STAGES, IN ORDER. THE ORDER IS THE METHOD.

### 1. INVENTORY — know what you have before you touch it
Count files, bytes, and **distinct documents**. These are three different numbers.
> **Measured 2026-08-01:** the legal corpus held **141 files = 105 distinct documents**. The text
> messages appeared **four times**. Feeding it raw would have weighted A1 4×.

### 2. EXTRACT + OCR — before anything else, and verify the extraction
Text extraction silently produces *near-empty* output on scans. **A file that extracts to 13
characters across 14 pages is not a short document; it is a failed extraction.**
> **Measured:** six core pleadings fell out of the legal corpus this way and **every prior analysis
> ran on a record missing its own pleadings.** OCR closed it: 220 files, 4,573 pages, 10.3M chars.
- **Control:** chars-per-page. Anything under ~200 is a failed extract, not a short document.
- OCR is **stage 2, not stage 5.** Dedupe before OCR compares garbage to garbage.

### 3. CANONICALISE — one file per distinct document
Path-prefixed duplicates (`Abraxas Case__X.txt` and `X.txt`) are the same document. **Byte-identical
dedupe does not catch them.** Normalise the name, group, keep the **largest** (most complete OCR).
⚠ **Near-duplicate detection by cosine similarity is a trap.** At 0.80 it called six different tax
years duplicates of each other — 95% boilerplate. **Group by document identity, not by text
similarity.**

### 4. 🔴 SEPARATE EVIDENCE FROM WORK PRODUCT — the stage everyone skips
**Our own memos, timelines, analyses and draft pleadings must never enter a corpus given to a node.**
A model fed our conclusions returns them as findings. That is a **confirmation loop wearing the
costume of independent review.**
> **Measured 2026-08-01:** 18 of 105 documents were our own work product. Excluding them is what made
> the four-agent fan-out worth running — and the agents then found things in the primary record that
> every prior pass had missed.
- Also exclude **vendor manuals and reference material** from evidence bundles (~680 KB of Agilent
  manuals). Keep them for *technical* questions; keep them out of *factual* ones.
- ⚠ And exclude AI-generated OSINT reconstructions **entirely**. Two "Shift Abraxas to Jasper"
  documents were LinkedIn/Tracxn summaries whose own text conceded no transfer was found. **In a
  corpus they read as evidence. They are not.**

### 5. ORDER — chronological, not alphabetical
**A record is a sequence.** Filesystem order destroys the one property that makes a document set
intelligible. Sort by document date, not filename, not size.
> This is what makes *"he wrote X on 9 July and told the other party Y on 14 July"* visible at all.
Where a document has no single date (a manual, an SOP), put it in a **reference appendix**, not in
the timeline.

### 6. BUNDLE — to the *executor's* limit, with a truncation control on every read
Bundle by **document class**, sized to the runtime that will carry it.
> **Measured 2026-08-01:** the Cowork sandbox caps a call at **45 s**. A 29 KB slice to
> gemini-2.5-pro took **32.2 s**; 119 KB and 165 KB slices **both timed out**. Real work runs
> natively.
- **Truncation control, non-negotiable:** for every file, compare **bytes consumed** against **bytes
  declared by stat**. A short read is a hard failure that aborts the build.
- **Never let a partial corpus reach a model.** It cannot tell you it received less than you sent.

### 7. FAN OUT ACROSS MODEL FAMILIES — then read for DISAGREEMENT
Four agents of one family share one set of priors. **The value is in where independent readers
diverge.** Never average the returns; that hides the only signal worth having.
> **Measured:** grok-4.5, gemini-2.5-pro, and four Claude agents agreed on the ¶41 finding — which
> raised confidence. One confidently asserted a second HPLC that never existed — which is why
> nothing enters a document without a host-side verification pass.

---

## THE FOUR CONTROLS THAT MAKE IT REAL
A stage without a control is a hope.

| control | catches | how it fails loudly |
|---|---|---|
| **chars-per-page** | failed extraction / unOCR'd scans | flags files under ~200 chars/page |
| **bytes consumed vs declared** | silent truncation, the mount's signature | aborts the bundle build |
| **distinct-document count vs file count** | duplicate weighting | prints both numbers, always |
| **work-product exclusion list, printed** | the confirmation loop | names every excluded file at build time |

**And the meta-control: a verifier that has never been shown to fail is not a verifier.**
Every control above should be provable against a planted defect before it is trusted.

---

## THE RULES, SHORT

1. **Extract and OCR first. Dedupe second.** Reversing them compares garbage to garbage.
2. **Count distinct documents, never files.**
3. **Never feed a model your own conclusions.** Exclude work product, and print the exclusion list.
4. **Order chronologically.** A record is a sequence.
5. **Measure the executor's ceiling before sizing the bundles**, not after.
6. **Put a truncation control on every read.** Silence is the failure mode.
7. **Fan out across families, and read for disagreement.**
8. **Nothing a model returns is evidence until it is verified against the source, host-side.**
9. **A document that describes an act is not proof the act occurred** — the corpus records what was
   *written*, not what was *done*. *(Learned twice in one hour, 2026-08-01.)*
10. **Print what was dropped.** Every stage that removes something must say what and why.

---

## STATUS
**Implemented:** `BTS_MESH\sweep_corpus.py` (stages 1, 3, 4, 6 + truncation control) ·
`BTS_MESH\ocr_backlog.py` (stage 2) · `BTS_MESH\dedupe_corpus.py` (partial stage 3) ·
`BTS_MESH\mesh_fanout.py` (stage 7).
**Owed:** stage 5 (chronological ordering) is not implemented anywhere — it is currently done by hand.
That is the next tool to write, and Keith identified the need before the gap was noticed:
> *"list the relevant documents, run the stripper on them and feed them chronologically."*
