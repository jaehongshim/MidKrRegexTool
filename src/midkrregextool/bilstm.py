"""bilstm.py

BiLSTM 기반 형태소 분석 후보 disambiguation을 위한 모듈.

tagger.py의 tag_tokens()가 규칙 기반으로 생성한 여러 분석 후보(Token.tagged_candidates)와, annotation-mode로 문맥 순서를 보존해 태깅한 골드 데이터(annotation_{period}c.jsonl의 source_id/token_index 기반 항목)를 짝지어 학습 예시를 만들고, 이를 바탕으로 문맥을 보고 올바른 후보를 고르는 BiLSTM 모델을 학습/적용한다.

"""

from __future__ import annotations

import torch
from torch import nn
from torch.utils.data import Dataset

from .model import Token


def build_annotated_examples(
    tokens: list[Token],
    gold_lookup: dict[tuple[str, int], str],
) -> list[dict]:
    """
    입력:
        tokens: source_id, token_index, tagged_candidates가 채워진
            Token 객체의 리스트. parser.py -> yale.py -> tagger.py의
            tag_tokens()를 실제로 거쳐서 나온 결과여야 한다 (그래야
            source_id/token_index가 원본 코퍼스 상의 정확한 위치를
            가리킨다).

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

        gold_lookup: annotation_{period}c.jsonl을 미리 읽어서 만든
            {(source_id, token_index): gold_morph} 사전.

            예) 위 골드 라인으로부터 만들어지는 항목:
                {
                    ("1447_석보상절6:28b:2:kor", 6): "kwo(h)/N/LEM-khwa/COM",
                    ...
                }

    출력:
        각 토큰마다, gold_lookup에 정답이 있고 그 정답이 tagged_candidates
        안에서 실제로 발견된 경우에만 아래 형태의 딕셔너리를 만들어 리스트로
        반환한다. (gold_lookup에 없거나, 있어도 tagged_candidates 안에서
        못 찾으면 그 토큰은 결과에서 제외한다.)

        위 예시에 대한 실제 출력:
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
                },
                ...
            ]
    """

    annotated_examples = []

    if tokens is None:
        return annotated_examples

    for token in tokens:

        gold_morph = gold_lookup.get((token.source_id, token.token_index))

        if gold_morph is None:
            continue

        candidates = token.tagged_candidates or []
        if gold_morph not in candidates:
            continue

        gold_idx = token.tagged_candidates.index(gold_morph)

        annotated_example = dict()

        annotated_example["source_id"] = token.source_id
        annotated_example["token_index"] = token.token_index
        annotated_example["surface"] = token.unicode_form
        annotated_example["candidates"] = token.tagged_candidates
        annotated_example["gold_index"] = gold_idx
        # annotated_example[]

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
    }
    idx = 2

    for c in unique_chars:
        c_dict[c] = idx
        idx += 1

    return c_dict


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

        encoded_candidates = []

        for candidate in candidates:
            encoded_candidates.append(
                encode_string(self.vocab, candidate, self.model_parameter)
            )

        gold_index = annotated_example["gold_index"]

        return {
            "candidates": encoded_candidates,
            "gold_index": gold_index,
        }


class CandidateScorer(nn.Module):
    def __init__(self, vocab_size: int, embed_dim: int = 16, hidden_dim: int = 32):
        super().__init__()

        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embed_dim,
            padding_idx=0,
        )

        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            bidirectional=True,
            batch_first=True,
        )

        self.fc = nn.Linear(hidden_dim * 2, 1)

    def forward(self, char_ids: torch.Tensor) -> torch.Tensor:
        embedded = self.embedding(char_ids)

        lstm_out, (h_n, c_n) = self.lstm(embedded)

        final_hidden = torch.cat([h_n[0], h_n[1]], dim=-1)

        score = self.fc(final_hidden)

        return score


def train_bilstm(
    dataset: DisambiguationDataset,
    model: CandidateScorer,
    epochs: int = 3,
) -> None:

    # "손실을 보고 모델을 실제로 고쳐주는 도구"를 준비한다.
    # model.parameters()는 이 모델 안에 있는, 고칠 수 있는 모든 숫자를
    # 자동으로 다 긁어모아 준다. Adam은 그 숫자들을 어떻게 조금씩
    # 고쳐나갈지 계산해주는 알고리즘 이름이다.
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    # "여러 개의 점수와 정답 인덱스를 비교해서, 얼마나 틀렸는지"를
    # 숫자 하나로 계산해주는 도구를 준비한다.
    loss_fn = nn.CrossEntropyLoss()

    print(f"[INFO] dataset: {dataset} / model: {model}")

    # 전체 데이터를 처음부터 끝까지 몇 번 반복해서 공부시킬지 정한다.
    # (한 번 다 보는 것을 "1 epoch"라고 부른다.)
    for epoch in range(epochs):

        # 이번 한 바퀴(epoch) 동안 얼마나 틀렸는지 합계를 저장할 변수.
        # 나중에 이 값이 점점 줄어드는지 보려고 만든다.
        total_loss = 0.0

        # 데이터(토큰들)를 하나씩 순서대로 꺼낸다.
        for i in range(len(dataset)):

            # i번째 토큰 하나를 꺼낸다.
            # (안에는 후보들 candidates, 그리고 정답 번호 gold_index가 들어있다)
            example = dataset[i]
            candidates = example["candidates"]
            gold_index = example["gold_index"]

            # 이 토큰의 각 후보마다 점수를 매겨서 담아둘 빈 상자.
            scores = []

            # 후보를 하나씩 꺼내서, 모델에게 "이거 몇 점이야?"라고 물어본다.
            for candidate_ids in candidates:

                # 후보 하나(숫자 리스트)를, 모델이 알아먹는 정확한
                # 텐서 모양으로 바꾼다. (이 모양 맞추는 절차는 PyTorch가
                # 항상 요구하는 정해진 형식이라, 그냥 이렇게 쓴다고
                # 생각해도 된다)
                char_tensor = torch.tensor(candidate_ids, dtype=torch.long).unsqueeze(0)

                # 모델에게 이 후보를 보여주고 점수를 하나 받는다.
                score = model(char_tensor)

                # 받은 점수를 상자에 담아둔다.
                scores.append(score)

            # 후보별 점수들을 한 줄로 나란히 이어붙인다.
            # (CrossEntropyLoss가 "후보들의 점수 한 줄"이라는 모양을
            # 원하기 때문에 모양을 맞춰주는 것이다)
            scores_tensor = torch.cat(scores, dim=0).view(1, -1)

            # 정답 번호도 같은 방식(텐서)으로 바꿔준다.
            gold_tensor = torch.tensor([gold_index], dtype=torch.long)

            # "이 점수들 중에서, 정답이 몇 번째였는데 실제로 얼마나
            # 잘 맞혔는지(혹은 못 맞혔는지)"를 숫자 하나(loss)로 계산한다.
            loss = loss_fn(scores_tensor, gold_tensor)

            # 아래 세 줄은 "모델을 실제로 조금 더 똑똑하게 고치는 절차"다.
            # 항상 이 순서, 이 세 줄로 쓴다고 생각하면 된다.

            # 1) 이전에 계산해뒀던 "고칠 방향" 기록을 깨끗이 지운다.
            optimizer.zero_grad()

            # 2) "이번엔 어느 방향으로, 얼마나 고쳐야 덜 틀리는지" 계산한다.
            loss.backward()

            # 3) 계산된 방향대로 모델의 숫자들을 실제로 아주 조금 고친다.
            optimizer.step()

            # 이번 토큰에서 얼마나 틀렸는지를 누적 합계에 더한다.
            # (.item()은 "텐서 안에 든 숫자 하나만 순수하게 꺼내라"는 뜻)
            total_loss += loss.item()

        # 이번 한 바퀴(epoch)가 끝날 때마다, 전체적으로 얼마나
        # 틀렸는지 화면에 찍어서 확인한다. 이 숫자가 뒤로 갈수록
        # 점점 작아지면 "모델이 배우고 있다"는 뜻이다.
        print(f"[Epoch {epoch+1}/{epochs}] total_loss = {total_loss:.4f}")
