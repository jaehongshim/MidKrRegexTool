---
title: "To-do list"
author: "Jaehong Shim"
date: "(as of June 11, 2026)"
geometry: margin=1in
---

# Universal Dependencies Integration — Task List

Working branch: `universal-dependencies` · Created: 2026-06-11

## Phase 0 — Preliminary cleanup (legacy removal)

- [x] Delete `src/midkrregextool/candidate_mining_legacy.py` (broken import: references nonexistent `split_lem_infl`)
- [x] Delete `src/midkrregextool/test_candidate_generator.py`, or move it to `tests/`
- [x] Update `CLAUDE.md`: document the `run_corpus_list` mode
- [x] Commit and push the cleanup

## Phase 1 — CoNLL-U converter implementation (UD step 4)

- [x] **morphs filler**: function parsing the `tagged_form` string into `Token.morphs` (`list[tuple[str, str]]`)
- [ ] **Create `data/ud_mapping.json` skeleton**: project tags → `{upos, feats, deprel}` lookup table (undecided entries as placeholder `_`)
- [ ] **Write the `conllu.py` module**: list of `Token` + mapping → CoNLL-U string
  - Assign sequential morpheme IDs within each sentence
  - Emit a multiword-token (MWT) range line for any word containing 2+ morphemes
  - Assemble FEATS with feature names sorted alphabetically (`sorted()`)
  - Record `Yale=` in MISC
  - `# sent_id` = source_id (page/section unit, standing in for sentence segmentation)
  - `# text` = analytically spaced version / `# text_pua` = original PUA text preserved
- [ ] **Add an `--export-conllu` mode to `cli.py`** (same tier as run_search etc.)
- [ ] Commit per step

## Phase 2 — Finalize design decisions (UD step 3, agenda items 2 & 3)

- [ ] Close reading of Chen et al. (2022), *Yet Another Format of Universal Dependencies for Korean* — reference for UPOS/DEPREL decisions on bound morphemes
- [ ] Fix UPOS for bound morphemes (particles ADP, endings PART/AUX, etc.)
- [ ] Fix DEPREL labels (particles `case`, conjunctive endings `mark`, prefinal endings `aux`, etc.)
- [ ] Fix FEATS mapping
  - *-(u)si* → `Polite=Elev`, *-sOp-* → `Polite=Humb`, addressee honorific → `Polite=Form`
  - Decide feature bundles for *-te-*, *-e is-* (resultative), *-uli-*
  - Decide whether to keep *-wO-* and *-ke-* deferred (excluded from FEATS, preserved in XPOS only)
- [ ] Extend `ud_mapping.json` to the full tagset

## Phase 3 — Validation (UD step 5)

- [ ] Install the official UD validator locally (`validate.py` from the `tools` repo)
- [ ] Validate output → fix errors → revalidate loop

## Phase 4 — Deferred / long-term

- [ ] Strategy for attaching DEPREL (and HEAD) — UD step 6 (rule-based vs. trained tools)
- [ ] Introduce sentence segmentation (currently using source_id spans as sentence stand-ins)
- [ ] Migrate training data from JSONL to gold CoNLL-U (only possible after `conllu.py` is complete)

## Notes

- Keep the mapping in data (`ud_mapping.json`), not in code — a changed decision propagates to the whole corpus by simply rerunning the converter.
- Treat generated `.conllu` files as derived artifacts; never edit them by hand.
- Keep `training.py` — it corresponds to the standard UD ecosystem's "manual annotation → gold data" stage.