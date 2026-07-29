import json
from pathlib import Path

import torch

from src.midkrregextool.annotation import (
    load_infl_decomp_from_annotation,
    load_pos_to_allowed_morphemes_inventory_from_annotation,
)
from src.midkrregextool.bilstm import (
    CandidateScorer,
    DisambiguationDataset,
    build_annotated_examples,
    build_char_vocab,
    build_morph_vocab,
    evaluate_model,
    split_train_test,
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

    # 4-0. train/text 분리 (반드시 vocab 만들기 전에!)
    train_examples, test_examples = split_train_test(examples, test_ratio=0.2, seed=123)
    print(f"[INFO] train:{len(train_examples)} / test: {len(test_examples)}")

    # 4-1. 자소 단위 vocab
    # (test에만 등장하는 글자/형태소는 <UNK>로 인코딩)
    c_vocab = build_char_vocab(examples)
    c_dataset = DisambiguationDataset(examples, c_vocab, "c")
    c_model = CandidateScorer(vocab_size=len(c_vocab))

    m_vocab = build_morph_vocab(examples)
    m_dataset = DisambiguationDataset(examples, m_vocab, "m")
    m_model = CandidateScorer(vocab_size=len(m_vocab))

    # 5. 학습 한 바퀴 (에러 없이 도는지 확인이 목표)

    # 5-0. repo root
    repo_root = Path(__file__).parents[0].resolve()
    model_dir = (repo_root / "data" / "model").resolve()
    model_dir.mkdir(parents=True, exist_ok=True)

    # 5-1. 자소 단위
    train_bilstm(c_dataset, c_model, epochs=3)
    torch.save(c_model.state_dict(), model_dir / "bilstm_c_model.pt")

    with open(model_dir / "bilstm_c_vocab.json", "w", encoding="utf-8") as f:
        json.dump(c_vocab, f, ensure_ascii=False)

    print(f"[INFO] Character-based model/vocab saved to: {model_dir}")
    print(f"\t- {model_dir / 'bilstm_c_model.pt'}")
    print(f"\t- {model_dir / 'bilstm_c_vocab.json'}")

    # 5-2. 형태소 단위
    train_bilstm(m_dataset, m_model, epochs=3)
    torch.save(m_model.state_dict(), model_dir / "bilstm_m_model.pt")

    with open(model_dir / "bilstm_m_vocab.json", "w", encoding="utf-8") as f:
        json.dump(m_vocab, f, ensure_ascii=False)

    print(f"[INFO] Morpheme-based model/vocab saved to: {model_dir}")
    print(f"\t- {model_dir / 'bilstm_m_model.pt'}")
    print(f"\t- {model_dir / 'bilstm_m_vocab.json'}")

    # 6. 성능 비교: baseline / c_model / m_model을 같은 test_examples로 채점
    baseline_result = evaluate_model(test_examples, None, None)
    c_result = evaluate_model(test_examples, c_vocab, c_model, "c")
    m_result = evaluate_model(test_examples, m_vocab, m_model, "m")

    print("[RESULT] Accuracy compared based on the test set")
    print(
        f"\tbaseline (rule-based):\t{baseline_result['correct']}/{baseline_result['total']} ({baseline_result['accuracy']:.1%})"
    )
    print(
        f"\tc_model (character-based):\t{c_result['correct']}/{c_result['total']} ({c_result['accuracy']:.1%})"
    )
    print(
        f"\tm_model (morpheme-based):\t{m_result['correct']}/{m_result['total']} ({m_result['accuracy']:.1%})"
    )

    print("[INFO] Done. Pipeline ran end to end.")
