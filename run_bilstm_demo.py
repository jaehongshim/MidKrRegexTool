import json
from pathlib import Path

from src.midkrregextool.annotation import (
    load_infl_decomp_from_annotation,
    load_pos_to_allowed_morphemes_inventory_from_annotation,
)
from src.midkrregextool.bilstm import (
    CandidateScorer,
    DisambiguationDataset,
    build_annotated_examples,
    build_char_vocab,
    train_bilstm,
)
from src.midkrregextool.parser import parse_file
from src.midkrregextool.tagger import (
    load_lemma_lexicon,
    tag_tokens,
)
from src.midkrregextool.yale import attach_yale

# ---- 설정: 실제 본인 경로/기간에 맞게 고치세요 ----
PERIOD = 15
ANNOTATION_DATA = Path("data/annotation")
CORPUS_FILE = Path(
    "D:/Corpus/NIKL/NIKL_Historical Korean Corpus 2023_v2.0/HXRW2320000612.xml"
)
# --------------------------------------------------

annotation_file = ANNOTATION_DATA / f"annotation_{PERIOD}c.jsonl"

# 1. annotation jsonl -> gold_lookup 만들기
gold_lookup = {}
with open(annotation_file, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        sid = obj.get("source_id")
        tidx = obj.get("token_index")
        gm = obj.get("gold_morph")
        if sid is not None and isinstance(tidx, int) and gm:
            gold_lookup[(sid, tidx)] = gm

print(f"[INFO] gold_lookup entries: {len(gold_lookup)}")

# 2. 코퍼스 파싱 + 태깅
lexicon = load_lemma_lexicon(PERIOD, annotation_data=ANNOTATION_DATA)
infl_decomp = load_infl_decomp_from_annotation(annotation_file)
pos_to_allowed_morphemes = load_pos_to_allowed_morphemes_inventory_from_annotation(
    ANNOTATION_DATA, PERIOD
)

tokens = attach_yale(parse_file(CORPUS_FILE, encoding="utf-16"), False, False)
tokens = tag_tokens(
    tokens,
    lexicon=lexicon,
    infl_decomp=infl_decomp,
    pos_to_allowed_morphemes=pos_to_allowed_morphemes,
)

# 3. 학습 예시 만들기
examples = build_annotated_examples(tokens, gold_lookup)
print(f"[INFO] annotation examples: {len(examples)}")

if not examples:
    print(
        "[ERROR] No annotation examples found. Check gold_lookup / candidates matching."
    )
else:
    # 4. vocab, Dataset, 모델 준비
    vocab = build_char_vocab(examples)
    dataset = DisambiguationDataset(examples, vocab)
    model = CandidateScorer(vocab_size=len(vocab))

    # 5. 학습 한 바퀴 (에러 없이 도는지 확인이 목표)
    train_bilstm(dataset, model, epochs=3)

    print("[INFO] Done. Pipeline ran end to end.")
