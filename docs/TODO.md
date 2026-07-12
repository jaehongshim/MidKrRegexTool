---
title: "To-do list"
author: "Jaehong Shim"
date: "(as of July 12, 2026)"
geometry: margin=1in
---

# Universal Dependencies Integration — Task List

Working branch: `universal-dependencies` · Created: 2026-06-11

## ⚠️ Cross-branch dependency (read before resuming Phase 1)

This branch's remaining work (Phase 1 completion onward) is currently **blocked on
an upstream refactor**, not on anything in this branch itself:

1. `tagger-candidates` branch (new, short-lived) refactors `tagger.py` so it exposes
   *all* candidate analyses per token instead of committing to a single one.
   Needed for `bilstm-disambiguation` (context-based re-ranking over candidates).
2. `tagger-candidates` → merged into `main`.
3. **This branch must then run `git merge origin/main`** to pick up the refactored
   `tagger.py` before further UPOS/FEATS/DEPREL work assumes a stable `Token.tagged_form`
   contract.
4. `bilstm-disambiguation` branch starts from the updated `main`.
5. Once both branches are based on the refactored `tagger.py`, `universal-dependencies`
   and `bilstm-disambiguation` proceed independently — they do not block each other
   (the only shared contract is the `tagged_form` string format, e.g.
   `"nilu/V/LEM-si/SUBJ/HON-ni/CONN"`).

**Do not start Phase 2 (UPOS/FEATS/DEPREL finalization) until step 3 above is done** —
finalizing the mapping against a `tagged_form` shape that's about to change wastes effort.

## Phase 0 — Preliminary cleanup (legacy removal)

- [x] Delete `src/midkrregextool/candidate_mining_legacy.py` (broken import: references nonexistent `split_lem_infl`)
- [x] Delete `src/midkrregextool/test_candidate_generator.py`, or move it to `tests/`
- [x] Update `CLAUDE.md`: document the `run_corpus_list` mode
- [x] Commit and push the cleanup

## Phase 1 — CoNLL-U converter implementation (UD step 4)

- [x] **morphs filler**: function parsing the `tagged_form` string into `Token.morphs` (`list[tuple[str, str]]`)
- [x] **Create `data/ud_mapping.json` skeleton**: project tags → `{upos, feats, deprel}` lookup table (undecided entries as placeholder `_`)
- [x] **Write the `conllu.py` module** (drafted; see known bug below) — list of `Token` + mapping → CoNLL-U string
  - Assign sequential morpheme IDs within each sentence
  - Emit a multiword-token (MWT) range line for any word containing 2+ morphemes
  - Assemble FEATS with feature names sorted alphabetically (`sorted()`)
  - Record `Yale=` in MISC
  - `# sent_id` = source_id (page/section unit, standing in for sentence segmentation)
  - `# text` = analytically spaced version / `# text_pua` = original PUA text preserved
- [x] **Add an `--export-conllu` mode to `cli.py`** (same tier as run_search etc.)
- [ ] **KNOWN BUG (parked, not currently being worked on):** `token_to_conllu()`,
  multi-morpheme branch — `return` sits inside the `for` loop and the morpheme
  offset is hardcoded (`start_id + 1` instead of `start_id + i`), so only the
  first morpheme of any 2+-morpheme token is ever emitted. Fix is a two-line
  change (dedent the `return`, `+1` → `+i`) but is intentionally deferred —
  do not pick this back up until explicitly revisited.
- [ ] Commit per step

## Phase 2 — Finalize design decisions (UD step 3, agenda items 2 & 3)

**Blocked until the tagger-candidates → main → merge sequence above is complete.**

- [ ] Close reading of Chen et al. (2022), *Yet Another Format of Universal Dependencies for Korean* — reference for UPOS/DEPREL decisions on bound morphemes
- [ ] Fix UPOS for bound morphemes (particles ADP, endings PART/AUX, etc.)
- [ ] Fix DEPREL labels (particles `case`, conjunctive endings `mark`, prefinal endings `aux`, etc.)
- [ ] Fix FEATS mapping
  - *-(u)si* → `Polite=Elev`, *-sOp-* → `Polite=Humb`, addressee honorific → `Polite=Form`
  - Decide feature bundles for *-te-*, *-e is-* (resultative), *-uli-*
  - Decide whether to keep *-wO-* and *-ke-* deferred (excluded from FEATS, preserved in XPOS only)
- [ ] Extend `ud_mapping.json` to the full tagset
- [ ] Revisit `_morph_to_row()`: LEMMA column currently duplicates the surface form
  (`form`) rather than the actual lemma already available in `tagged_form`
  (e.g. `nilu` in `nilu/V/LEM-si/...`) — decide whether this is intentional
  for now or should be fixed alongside the FEATS work

## Phase 3 — Validation (UD step 5)

- [ ] Fix the parked Phase 1 bug (`token_to_conllu` multi-morpheme case) before running the validator —
  otherwise every multi-morpheme token will fail validation for missing rows
- [ ] Install the official UD validator locally (`validate.py` from the `tools` repo)
- [ ] Validate output → fix errors → revalidate loop

## Phase 4 — Deferred / long-term

- [ ] Strategy for attaching DEPREL (and HEAD) — UD step 6 (rule-based vs. trained tools)
- [ ] Introduce sentence segmentation (currently using source_id spans as sentence stand-ins)
- [ ] Migrate training data from JSONL to gold CoNLL-U (only possible after `conllu.py` is complete)
- [ ] Consider extending `training_{period}c.jsonl` schema with optional `head`/`deprel`
  fields now, so future UD gold annotation can reuse the same manual-annotation pass
  instead of re-tagging the same sentences twice

## Notes

- Keep the mapping in data (`ud_mapping.json`), not in code — a changed decision propagates to the whole corpus by simply rerunning the converter.
- Treat generated `.conllu` files as derived artifacts; never edit them by hand.
- Keep `training.py` — it corresponds to the standard UD ecosystem's "manual annotation → gold data" stage.
- This branch does not block, and is not blocked by, `bilstm-disambiguation` once both
  are rebased on the post-`tagger-candidates` `main`. The only shared contract between
  the two efforts is the `tagged_form` string format.
