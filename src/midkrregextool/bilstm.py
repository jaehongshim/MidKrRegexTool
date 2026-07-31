"""bilstm.py

BiLSTM 기반 형태소 분석 후보 disambiguation을 위한 모듈.

tagger.py의 tag_tokens()가 규칙 기반으로 생성한 여러 분석 후보(Token.tagged_candidates)와, annotation-mode로 문맥 순서를 보존해 태깅한 골드 데이터(annotation_{period}c.jsonl의 source_id/token_index 기반 항목)를 짝지어 학습 예시를 만들고, 이를 바탕으로 문맥을 보고 올바른 후보를 고르는 BiLSTM 모델을 학습/적용한다.

"""

from __future__ import annotations

import random

import torch
from torch import nn
from torch.utils.data import Dataset

from .model import Token


def build_annotated_examples(
    tokens: list[Token],
    gold_lookup: dict[tuple[str, int], str],
    n: int,
) -> list[dict]:
    """
    입력:
        tokens: source_id, token_index, tagged_candidates가 채워진
            Token 객체의 리스트. parser.py -> yale.py -> tagger.py의
            tag_tokens()를 실제로 거쳐서 나온 결과여야 한다 (그래야
            source_id/token_index가 원본 코퍼스 상의 정확한 위치를
            가리킨다). 또한 문서 전체가 원래 순서 그대로 들어있어야
            한다 (get_adjacent_words()가 리스트 안 위치(i)로 좌우
            이웃을 찾기 때문에, 일부만 걸러낸 리스트를 넘기면 안 된다).

            예) 아래 골드 라인 하나가 있다고 하자:
                {"period": "15c", "source_id": "1447_석보상절6:28b:2:kor",
                 "token_index": 6, "token": "고콰",
                 "gold_morph": "kwo(h)/N/LEM-khwa/COM"}

            이 라인이 가리키는 실제 토큰은 tokens 안에 이런 Token
            객체로 들어있을 것이다:
                Token(
                    ...,
                    source_id="1447_석보상절6:28b:2:kor",
                    token_index=6,
                    unicode_form="고콰",
                    tagged_candidates=[
                        "kwo(h)/N/LEM-khwa/COM",   # 실제 정답 (아래 예의 후보 0)
                        "kwokh/N/LEM-wa/COM",       # 규칙 기반이 잘못 낸 다른 후보
                    ],
                )

            그리고 tokens 리스트 안에서 이 토큰의 바로 앞뒤에는 이런
            이웃 토큰들이 있다고 하자 (같은 sent_type, 같은 출전):
                tokens[i-1].tagged_candidates == ["nim/N/LEM"]
                tokens[i+1].tagged_candidates == ["is/V/LEM-i.ni/INFL"]

        gold_lookup: annotation_{period}c.jsonl을 미리 읽어서 만든
            {(source_id, token_index): gold_morph} 사전.

            예) 위 골드 라인으로부터 만들어지는 항목:
                {
                    ("1447_석보상절6:28b:2:kor", 6): "kwo(h)/N/LEM-khwa/COM",
                    ...
                }

        n: 좌우로 몇 개의 이웃 토큰을 문맥으로 가져올지 (get_adjacent_words()에
            그대로 전달됨). 이웃이 문서/문장 경계에 부딪혀 부족하면 "<BOS>"나
            "<EOS>"로 채워져서, 항상 길이 n짜리 리스트로 나온다.

    출력:
        각 토큰마다, gold_lookup에 정답이 있고 그 정답이 tagged_candidates
        안에서 실제로 발견된 경우에만 아래 형태의 딕셔너리를 만들어 리스트로
        반환한다. (gold_lookup에 없거나, 있어도 tagged_candidates 안에서
        못 찾으면 그 토큰은 결과에서 제외한다.)

        위 예시에 대한 실제 출력 (n=1인 경우):
            [
                {
                    "source_id": "1447_석보상절6:28b:2:kor",
                    "token_index": 6,
                    "surface": "고콰",
                    "candidates": [
                        "kwo(h)/N/LEM-khwa/COM",
                        "kwokh/N/LEM-wa/COM",
                    ],
                    "gold_index": 0,   # candidates[0]이 gold_morph와 일치
                    "left_context": ["nim/N/LEM"],           # 이웃(앞)의 규칙 기반 1순위 후보
                    "right_context": ["is/V/LEM-i.ni/INFL"], # 이웃(뒤)의 규칙 기반 1순위 후보
                },
                ...
            ]
    """

    annotated_examples = []

    if tokens is None:
        return annotated_examples

    for i, token in enumerate(tokens):

        gold_morph = gold_lookup.get((token.source_id, token.token_index))

        if gold_morph is None:
            continue

        candidates = token.tagged_candidates or []
        if gold_morph not in candidates:
            continue

        gold_idx = token.tagged_candidates.index(gold_morph)

        left_context, right_context = get_adjacent_words(tokens, i, n)

        annotated_example = dict()

        annotated_example["source_id"] = token.source_id
        annotated_example["token_index"] = token.token_index
        annotated_example["surface"] = token.unicode_form
        annotated_example["candidates"] = token.tagged_candidates
        annotated_example["gold_index"] = gold_idx
        annotated_example["left_context"] = left_context
        annotated_example["right_context"] = right_context

        annotated_examples.append(annotated_example)

    return annotated_examples


def build_morph_vocab(annotated_examples: list[dict]) -> dict[str, int]:
    """
    입력:
        annotated_examples: build_annotated_examples()가 만든 딕셔너리 리스트.
            각 원소는 "candidates" 키에 문자열 리스트(후보 tagged_form들)를
            담고 있다.

            예) 아래 두 개짜리 annotated_examples가 있다고 하자:
                [
                    {"candidates": ["ho/V/LEM", "hon/NUM/LEM"], ...},
                    {"candidates": ["al/V/LEM-a/CONN"], ...},
                ]

    출력:
        모든 annotated_example의 모든 candidates 문자열에 등장하는 형태 + 태그 짝을 전부 모아 중복 제거한 뒤, 각 짝에 고유 번호를 매긴 사전.
        "<PAD>"(0번)와 "<UNK>"(1번)는 실제 글자가 아니라 다음 단계
        (길이 맞추기, 미등록 글자 처리)에서 쓸 예약된 특수 기호이며,
        항상 고정된 번호를 갖는다.

        위 예시에 대한 실제 출력 예시:
            {
                "<PAD>": 0,
                "<UNK>": 1,
                "ho/V/LEM": 2,
                "hon/NUM/LEM": 3,
                "al/V/LEM": 4,
                "a/CONN": 5,
                ...
            }
    """

    morphs = []

    for annotated_example in annotated_examples:

        candidates = annotated_example.get("candidates")

        for candidate in candidates:
            # Polymorphemic token
            if "-" in candidate:
                chunks = candidate.split("-")
                morphs.extend(chunks)
            else:
                morphs.append(candidate)

        unique_morphs = set(morphs)

    m_dict = {
        "<PAD>": 0,
        "<UNK>": 1,
        "<BOS>": 2,
        "<EOS>": 3,
        "<SEP>": 4,
    }
    idx = 2

    for m in unique_morphs:
        m_dict[m] = idx
        idx += 1

    return m_dict


def build_char_vocab(annotated_examples: list[dict]) -> dict[str, int]:
    """
    입력:
        annotated_examples: build_annotated_examples()가 만든 딕셔너리 리스트.
            각 원소는 "candidates" 키에 문자열 리스트(후보 tagged_form들)를
            담고 있다.

            예) 아래 두 개짜리 annotated_examples가 있다고 하자:
                [
                    {"candidates": ["ho/V/LEM", "hon/V/LEM"], ...},
                    {"candidates": ["al/V/LEM-a/CONN"], ...},
                ]

    출력:
        모든 annotated_example의 모든 candidates 문자열에 등장하는 글자를
        전부 모아 중복 제거한 뒤, 각 글자에 고유 번호를 매긴 사전.
        "<PAD>"(0번)와 "<UNK>"(1번)는 실제 글자가 아니라 다음 단계
        (길이 맞추기, 미등록 글자 처리)에서 쓸 예약된 특수 기호이며,
        항상 고정된 번호를 갖는다.

        위 예시에 대한 실제 출력 (등장한 글자: h,o,n,/,V,L,E,M,a,l,-,C,O,N —
        set이라 순서는 실행마다 달라질 수 있으므로 번호 배정 순서는
        예시일 뿐이다):
            {
                "<PAD>": 0,
                "<UNK>": 1,
                "h": 2,
                "o": 3,
                "n": 4,
                "/": 5,
                "V": 6,
                "L": 7,
                "E": 8,
                "M": 9,
                "a": 10,
                "l": 11,
                "-": 12,
                "C": 13,
                "N": 14,
            }

        주의: 이 사전은 annotated_examples 전체를 한 번에 훑어서 만드는
        "하나의" 사전이다. 이후 encode_string()이 이 사전을 그대로 재사용
        해야, 같은 글자가 항상 같은 번호로 일관되게 인코딩된다.
    """

    chars = []

    for annotated_example in annotated_examples:

        candidates = annotated_example.get("candidates")

        for candidate in candidates:
            chars.extend(candidate)

    unique_chars = set(chars)

    c_dict = {
        "<PAD>": 0,
        "<UNK>": 1,
        "<BOS>": 2,
        "<EOS>": 3,
        "<SEP>": 4,
    }
    idx = 2

    for c in unique_chars:
        c_dict[c] = idx
        idx += 1

    return c_dict


def get_adjacent_words(
    tokens: list[Token],
    i: int,
    n: int,
) -> tuple[list[str], list[str]]:
    current = tokens[i]

    def _same_source(t) -> bool:
        return t.source_id.split(":", 1)[0] == current.source_id.split(":", 1)[0]

    def _walk(step: int) -> list[Token]:
        found = []
        idx = i + step
        while 0 <= idx < len(tokens) and len(found) < n:
            candidate = tokens[idx]
            if not _same_source(candidate):
                break

            if current.sent_type == "anno":
                if candidate.sent_type == "anno":
                    found.append(candidate)
                    idx += step
                else:
                    break
            else:
                if candidate.sent_type == current.sent_type:
                    found.append(candidate)
                    idx += step
                elif candidate.sent_type == "anno":
                    idx += step
                else:
                    break
        return found

    left_found = list(reversed(_walk(-1)))
    right_found = _walk(1)

    left_context = ["<BOS>"] * (n - len(left_found)) + [
        t.tagged_candidates[0] if t.tagged_candidates else "<BOS>" for t in left_found
    ]
    right_context = [
        t.tagged_candidates[0] if t.tagged_candidates else "<EOS>" for t in right_found
    ] + ["<EOS>"] * (n - len(right_found))

    return left_context, right_context


def split_train_test(
    annotated_examples: list[dict],
    test_ratio: float = 0.2,
    seed: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    source_id 단위로 문서를 먼저 나눈 뒤, 각 문서에 속한 예시를 통째로 train 또는 test로 보낸다. (같은 문서가 train/test에 걸쳐 섞이는 것을 방지)
    """
    source_ids = sorted({ex["source_id"] for ex in annotated_examples})

    rng = random.Random(seed)
    rng.shuffle(source_ids)

    n_test = max(1, int(len(source_ids) * test_ratio))
    test_ids = set(source_ids[:n_test])

    train_examples = [
        ex for ex in annotated_examples if ex["source_id"] not in test_ids
    ]
    test_examples = [ex for ex in annotated_examples if ex["source_id"] in test_ids]

    return train_examples, test_examples


def encode_string(
    vocab: dict[str, int], string: str | None = None, model_parameter: str | None = None
) -> list[int]:
    """
    입력:
        string: 인코딩할 문자열 하나 (예: 후보 tagged_form 문자열
            "ho/V/LEM"). None이 들어올 수도 있다 (예: 해당 후보가 없는 경우).
        vocab: model_parameter에 따라 build_char_vocab() 또는 build_morph_vocab()이 만든 {글자: 번호} 사전.
            예) model_parameter == "c" / {"<PAD>": 0, "<UNK>": 1, "h": 2, "o": 3, "/": 5, ...}
            model_parameter == "m" / {"<PAD>": 0, "<UNK>": 1, "ho/V/LEM": 2, ...}
        model_parameter: 자소 기반 모델 "c" 또는 형태소 기반 모델 "m" 인자. 이후 분기 결정 파라미터로 사용.

    출력:
        model_parameter에 따라 결정된 string의 각 단위를 vocab에서 찾은 번호로 치환한 정수 리스트.
        vocab에 없는 글자는 "<UNK>" 번호로 대체한다 (에러를 내지 않는다).
        string이 None이면 빈 리스트를 반환한다.

        예) string = "ho/V/LEM", vocab이 위 예시와 같고 model_parameter가 "c"이라면:
            encode_string("ho/V/LEM", vocab)
            -> [2, 3, 5, 6, 5, 7, 8, 9]
            (h=2, o=3, /=5, V=6, /=5, L=7, E=8, M=9)
    """

    if string is None:
        return []

    if model_parameter not in ("c", "m"):
        raise ValueError(f"model_parameter must be 'c' or 'm', got {model_parameter!r}")

    encoded_ids = []

    if string is None:
        return []

    unk_id = vocab.get("<UNK>")

    # 자소 기반 모델 분기
    if model_parameter == "c":

        for s in string:

            id = vocab.get(s, unk_id)

            encoded_ids.append(id)

    elif model_parameter == "m":

        for m in string.split("-"):
            id = vocab.get(m, unk_id)

            encoded_ids.append(id)

    return encoded_ids


def encode_forward_sequence(vocab, left_context, candidate, model_parameter):
    sep_id = vocab["<SEP>"]
    ids = []
    for lc in left_context:
        ids.extend(encode_string(vocab, lc, model_parameter))
        ids.append(sep_id)
    ids.extend(encode_string(vocab, candidate, model_parameter))
    return ids


def encode_backward_sequence(vocab, right_context, candidate, model_parameter):
    sep_id = vocab["<SEP>"]
    ids = []
    for rc in reversed(right_context):
        ids.extend(encode_string(vocab, rc, model_parameter))
        ids.append(sep_id)
    ids.extend(encode_string(vocab, candidate, model_parameter))
    return ids


def predict_best_candidate(
    candidates: list[str],
    vocab: dict[str, int],
    model: CandidateScorer,
    model_parameter: str | None = None,
    left_context: list[str] | None = None,
    right_context: list[str] | None = None,
) -> str:
    left_context = left_context or []
    right_context = right_context or []

    scores = []
    for c in candidates:
        fwd_ids = encode_forward_sequence(vocab, left_context, c, model_parameter)
        bwd_ids = encode_backward_sequence(vocab, right_context, c, model_parameter)
        fwd_tensor = torch.tensor(fwd_ids, dtype=torch.long).unsqueeze(0)
        bwd_tensor = torch.tensor(bwd_ids, dtype=torch.long).unsqueeze(0)
        score = model(fwd_tensor, bwd_tensor)
        scores.append(score.item())

    best_idx = scores.index(max(scores))
    return candidates[best_idx]


class DisambiguationDataset(Dataset):
    def __init__(
        self,
        annotated_examples: list[dict],
        vocab: dict[str, int],
        model_parameter: str,
    ):
        self.annotated_examples = annotated_examples
        self.vocab = vocab
        self.model_parameter = model_parameter

    def __len__(self) -> int:
        return len(self.annotated_examples)

    def __getitem__(self, idx: int) -> dict:

        annotated_example = self.annotated_examples[idx]

        candidates = annotated_example["candidates"]

        left_context = annotated_example["left_context"]
        right_context = annotated_example["right_context"]

        encoded_forward = []
        encoded_backward = []

        for candidate in candidates:
            encoded_forward.append(
                encode_forward_sequence(
                    self.vocab, left_context, candidate, self.model_parameter
                )
            )
            encoded_backward.append(
                encode_backward_sequence(
                    self.vocab, right_context, candidate, self.model_parameter
                )
            )

        return {
            "forward": encoded_forward,
            "backward": encoded_backward,
            "gold_index": annotated_example["gold_index"],
        }


class CandidateScorer(nn.Module):
    def __init__(self, vocab_size: int, embed_dim: int = 16, hidden_dim: int = 32):
        super().__init__()

        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embed_dim,
            padding_idx=0,
        )

        self.forward_lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True)
        self.backward_lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim * 2, 1)

    def forward(
        self, forward_ids: torch.Tensor, backward_ids: torch.Tensor
    ) -> torch.Tensor:
        _, (fwd_h, _) = self.forward_lstm(self.embedding(forward_ids))
        _, (bwd_h, _) = self.backward_lstm(self.embedding(backward_ids))
        combined = torch.cat([fwd_h[0], bwd_h[0]], dim=-1)
        return self.fc(combined)


def train_bilstm(dataset, model, epochs=3):
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.CrossEntropyLoss()

    print(f"[INFO] dataset: {dataset} / model: {model}")

    for epoch in range(epochs):
        total_loss = 0.0

        for i in range(len(dataset)):
            example = dataset[i]
            gold_index = example["gold_index"]

            scores = []
            for fwd_ids, bwd_ids in zip(example["forward"], example["backward"]):
                fwd_tensor = torch.tensor(fwd_ids, dtype=torch.long).unsqueeze(0)
                bwd_tensor = torch.tensor(bwd_ids, dtype=torch.long).unsqueeze(0)
                score = model(fwd_tensor, bwd_tensor)
                scores.append(score)

            scores_tensor = torch.cat(scores, dim=0).view(1, -1)
            gold_tensor = torch.tensor([gold_index], dtype=torch.long)
            loss = loss_fn(scores_tensor, gold_tensor)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        print(f"[Epoch {epoch+1}/{epochs}] total_loss = {total_loss:.4f}")


def evaluate_model(
    examples: list[dict],
    vocab: dict[str, int] | None,
    model: CandidateScorer | None,
    model_parameter: str | None = None,
) -> dict:
    """
    examples: build_annotated_examples()가 만든 test 예시 리스트
        (split_train_test()로 나눈 test_examples를 넣는다).
    vocab, model: c_model/c_vocab 또는 m_model/m_vocab.
        model이 None이면 baseline(candidates[0])으로 채점한다.
    model_parameter: "c" 또는 "m". model이 None이면 안 쓰인다.

    반환: {"correct": int, "total": int, "accuracy": float}
        total은 candidates가 2개 이상인 예시만 센다
        (후보가 1개뿐이면 disambiguation 자체가 필요 없는 자명한
        케이스라, 정확도를 희석시키지 않기 위해 제외한다).
    """
    correct = 0
    total = 0

    for example in examples:
        candidates = example["candidates"]

        # 분석형 후보가 하나 뿐이면 제외
        if len(candidates) <= 1:
            continue

        total += 1

        if model is not None:
            predicted = predict_best_candidate(
                candidates, vocab, model, model_parameter
            )
            predicted_index = candidates.index(predicted)
        else:
            predicted_index = 0  # rule-based fallback

        if predicted_index == example["gold_index"]:
            correct += 1

    accuracy = correct / total if total > 0 else 0.0

    return {"correct": correct, "total": total, "accuracy": accuracy}
