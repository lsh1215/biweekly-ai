# Paper Templates

paper-writer 가 로드. 학술 논문 / 기술 리포트 작성 시 적용.

## 7 섹션 구조 (default)

```markdown
# [Title - 한 줄에 핵심 발견 포함]

## Abstract
[250-400자. 4 요소: 문제 / 방법 / 핵심 결과 (수치) / 시사점.
 미래 시제 금지, 발견 위주.]

## 1. Introduction
[문제 정의. 기존 연구의 gap. 본 연구의 contribution 3가지 이내.]

## 2. Method
[재현 가능 수준의 상세. 데이터셋 / 모델 / 환경 / hyperparameter.
 Toulmin Method 단계 명시 (Claim → Grounds 의 Grounds 가 여기).]

## 3. Results
[표 + 수치 위주. 단언 + 통계 신뢰도 (p-value, CI, std) 명시.
 cherry-picking 금지. 모든 조건 다 보고.]

## 4. Discussion
[Why - 왜 그런 결과가 나왔는가. 메커니즘 가설.
 Steel Man 으로 반대 해석도 다룸.]

## 5. Limitations
[Mandatory. 4가지 카테고리:
 - 데이터셋 한계 (size / bias / 도메인)
 - 방법론 한계 (가정 / 단순화)
 - 외부 타당성 한계 (일반화)
 - 후속 연구 필요 항목]

## 6. Conclusion
[Abstract 의 결론을 다른 표현으로. 다음 연구 방향 1-2 줄.
 미래 시제 예고 ("다음 연구에서 다룰 것이다") 금지 - "추가 연구 영역" 으로 단언.]

## References
[BibTeX 가능, 일반 list 도 가능. 본문 인용 형식: [Author Year] 또는 (Author, Year).]
```

## Abstract 작성 규칙

좋은 Abstract 4 요소:

1. **문제** (1-2 문장): "X 가 Y 환경에서 Z 한계를 보인다"
2. **방법** (1-2 문장): "본 연구는 W 를 통해 X 를 분석한다 - 데이터/모델 한 줄"
3. **핵심 결과** (1-2 문장): "수치. 비교 baseline 대비 상승/하락 %p"
4. **시사점** (1 문장): "결과의 의미. 향후 활용 영역."

피할 abstract 패턴:

- 일반론 시작: "최근 ~ 분야는 ~ 로 인해 ~" - 1번째 문장이 통계/문제로 직진해야 함.
- 모호한 결과: "유의미한 향상" - 정확한 수치로.
- 미래 시제: "본 연구에서는 ~ 를 다룬다" - 과거형/현재형으로 발견 위주.

## Method 재현성 체크리스트

- [ ] 데이터셋 출처 + 버전 + 분할 비율 명시?
- [ ] 모델 종류 + 파라미터 수 + base 모델 (있다면) 명시?
- [ ] hyperparameter 명시 (learning rate, batch size, epoch, optimizer)?
- [ ] 학습/추론 환경 (GPU, framework version) 명시?
- [ ] random seed 명시 (재현용)?
- [ ] 평가 지표 정의 (metric formula 또는 reference) 명시?

## Results 보고 원칙

- **모든 조건 다 보고**: cherry-picking 금지. 좋은 결과만 골라서 보고하면 reviewer 가 잡아냄.
- **통계 신뢰도 동반**: p-value, 신뢰구간, 표준편차. 단일 seed 만으로는 약함.
- **Baseline 명시**: 비교 대상 명확히. 같은 데이터셋, 같은 평가 방식.
- **시각화는 선택, 표는 필수**: 표가 reviewer 가 가장 빨리 읽는 단위.

## Steel Man in Discussion

Discussion 섹션에서 **반대 해석을 가장 강한 형태로 재구성한 뒤 반박**:

```markdown
한 가지 해석은 "관찰된 향상은 dataset bias 때문" 이라는 것이다. 실제로
[데이터셋 X] 에는 [패턴 Y] 가 편중되어 있고, 이것이 결과를 부풀릴 수 있다.
그러나 [추가 분석 Z] 에서 이 가설은 기각된다 - [데이터/수치].
```

## Limitations 작성 원칙

좋은 Limitations 는 4 카테고리 균형:

1. **데이터 한계**: "200 task 는 통계적 한계, 5 모델 only"
2. **방법 한계**: "prompt 표준화 부족, single seed"
3. **외부 타당성**: "code generation 에 한정, 일반 NLP task 미검증"
4. **후속 연구**: "RAG retrieval failure 의 정량 분류는 미해결"

피할 패턴:

- "한계는 거의 없다" - 약점 못 찾는 paper 는 reviewer 가 더 의심.
- 일반론 ("향후 더 많은 연구가 필요하다") - 어떤 연구인지 구체적으로.

## 톤

- 한국어 paper 기본: `~다` 체.
- 영어 약어 첫 등장 시 풀이 1회 (예: "Retrieval-Augmented Generation (RAG)").
- 인용은 `[Smith 2024]` 또는 `(Smith, 2024)` 한 가지 스타일로 일관.
- 주석 (footnote) 은 본문 흐름을 끊으므로 가급적 회피.

## 검증 체크리스트 (writer 가 마지막에 self-check)

- [ ] Abstract 250-400자, 4 요소 모두 포함?
- [ ] Method 재현성 6개 항목 충족?
- [ ] Results 가 cherry-picking 회피?
- [ ] Discussion 에 Steel Man 1회 이상?
- [ ] Limitations 4 카테고리 모두 다룸?
- [ ] 미래 시제 0회 (Conclusion 포함)?
- [ ] em-dash/en-dash 본문 0회?
- [ ] 영어 약어 모두 첫 등장 풀이?
