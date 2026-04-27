# Post Structure Templates

블로그 작성 시 사용자가 선택한 템플릿을 적용. 3개 중 하나 선택 (Phase 0 에서 결정).

## 1. Default Structure (PAS / PAR-based)

특정 문제를 정의하고 해결하는 글에 적합.

```markdown
# [Title]

## Problem - [구체 시나리오 + 수치]
[독자가 "나도 겪어본 문제다" 라 느끼게 만드는 도입]

## Analysis - [원인 구조 분석]
[근본 원인의 메커니즘. Steel Man 으로 반론도 세우기]

## Action - [해결 메커니즘]
[Claim → Grounds → Qualifier → Rebuttal 구조 자연스럽게]
[코드·설정·다이어그램]

## Result - [수치 검증]
[Before/After 표, 측정값]

## Trade-offs
[한계와 대안. Intellectual honesty 의 핵심]

## 요약
[3~5 bullet, 미래 시제 예고 금지. 권장 구성:
 1. 구조적 본질
 2. 핵심 메커니즘
 3. 검증 수치
 4. 의도적 한계
 5. 글 안의 짝(주변 패턴) 연결]
```

## 2. Development Journal / Adoption Story

프로젝트 경험을 시간순으로 풀어내는 글에 적합.

```markdown
# [Title]

## 배경
[처음에 우리는 _____ 였다 - 초기 상황]

## 문제 발견
[그러던 어느 날 _____ 문제가 나타났다 - inciting incident]

## 탐색
[그래서 _____ 를 시도했다 - 검토한 대안과 장단점]

## 결정과 구현
[결국 _____ 로 풀었다 - 최종 선택의 근거 + 구현]

## 결과
[Before/After. 구체적 수치]

## 회고
[잘된 것, 부족했던 것, 다시 한다면]
```

## 3. General Article (Topic-based)

넓은 주제를 여러 소주제로 나눠 설명하는 글. "X 가지 방법", "Deep dive" 류.

```markdown
# [Title]

[Opening hook - 구체 시나리오 또는 통계]
[이 글이 다루는 범위 한 줄 안내]

---

## 1. [First Topic]
### Context / Problem
### How It Works / Solution
### Pitfalls (선택)

---

## 2. [Second Topic]
[같은 패턴]

---

## 요약
[Before/After 비교 표 또는 핵심 수치]
[번호 매긴 takeaway 리스트]

---

> References
```

## 선택 기준

| Template | 적합한 글 | 신호 문구 |
|----------|----------|-----------|
| 1. PAS/PAR | 특정 문제 해결 | "왜 X 가 터지는가", "Y 해결법" |
| 2. Development Journal | 프로젝트 경험 공유 | "X 마이그레이션 후기", "Y 도입기" |
| 3. General Article | 다각도 주제 설명 | "N 가지 방법", "Deep dive into Z" |
