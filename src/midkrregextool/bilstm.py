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
