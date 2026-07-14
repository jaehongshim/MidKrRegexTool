"""bilstm.py

BiLSTM 기반 형태소 분석 후보 disambiguation을 위한 모듈.

tagger.py의 tag_tokens()가 규칙 기반으로 생성한 여러 분석 후보(Token.tagged_candidates)와, training-mode로 문맥 순서를 보존해 태깅한 골드 데이터(training_{period}c.jsonl의 source_id/token_index 기반 항목)를 짝지어 학습 예시를 만들고, 이를 바탕으로 문맥을 보고 올바른 후보를 고르는 BiLSTM 모델을 학습/적용한다.

주의: 주어진 토큰의 위치 정보 없이 표면형만으로 태깅을 시도하는 것은 **절대** 지양한다.

"""

from __future__ import annotations

from .model import Token


def build_training_examples(
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

        gold_lookup: training_{period}c.jsonl을 미리 읽어서 만든
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

    training_examples = []

    if tokens is None:
        return training_examples

    for token in tokens:

        gold_morph = gold_lookup.get((token.source_id, token.token_index))

        if gold_morph is None:
            continue

        candidates = token.tagged_candidates or []
        if gold_morph not in candidates:
            continue

        gold_idx = token.tagged_candidates.index(gold_morph)

        training_example = dict()

        training_example["source_id"] = token.source_id
        training_example["token_index"] = token.token_index
        training_example["surface"] = token.unicode_form
        training_example["candidates"] = token.tagged_candidates
        training_example["gold_index"] = gold_idx

        training_examples.append(training_example)

    return training_examples


def build_char_vocab(training_examples: list[dict]) -> dict[str, int]:
    """
    입력:
        training_examples: build_training_examples()가 만든 딕셔너리 리스트.
            각 원소는 "candidates" 키에 문자열 리스트(후보 tagged_form들)를
            담고 있다.

            예) 아래 두 개짜리 training_examples가 있다고 하자:
                [
                    {"candidates": ["ho/V/LEM", "hon/V/LEM"], ...},
                    {"candidates": ["al/V/LEM-a/CONN"], ...},
                ]

    출력:
        모든 training_example의 모든 candidates 문자열에 등장하는 글자를
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

        주의: 이 사전은 training_examples 전체를 한 번에 훑어서 만드는
        "하나의" 사전이다. 이후 encode_string()이 이 사전을 그대로 재사용
        해야, 같은 글자가 항상 같은 번호로 일관되게 인코딩된다.
    """

    chars = []

    for training_example in training_examples:

        candidates = training_example.get("candidates")

        for candidate in candidates:
            for c in candidate:
                chars.append(c)

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
    vocab: dict[str, int],
    string: str | None = None,
) -> list[int]:
    """
    입력:
        string: 인코딩할 문자열 하나 (예: 후보 tagged_form 문자열
            "ho/V/LEM"). None이 들어올 수도 있다 (예: 해당 후보가 없는 경우).
        vocab: build_char_vocab()이 만든 {글자: 번호} 사전.
            예) {"<PAD>": 0, "<UNK>": 1, "h": 2, "o": 3, "/": 5, ...}

    출력:
        string의 각 글자를 vocab에서 찾은 번호로 치환한 정수 리스트.
        vocab에 없는 글자는 "<UNK>" 번호로 대체한다 (에러를 내지 않는다).
        string이 None이면 빈 리스트를 반환한다.

        예) string = "ho/V/LEM", vocab이 위 예시와 같다면:
            encode_string("ho/V/LEM", vocab)
            -> [2, 3, 5, 6, 5, 7, 8, 9]
            (h=2, o=3, /=5, V=6, /=5, L=7, E=8, M=9)
    """

    char_ids = []

    if string is None:
        return []

    unk_id = vocab.get("<UNK>")

    for s in string:

        id = vocab.get(s, unk_id)

        char_ids.append(id)

    return encode_string
