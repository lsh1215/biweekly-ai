# Argumentation Structure

blog-writer 와 blog-critic 이 모두 참조. 논증 강도 평가의 공통 기준.

## Toulmin Model

기술 주장마다 의식적으로 적용:

```
Claim     : "Kafka producer 의 acks 는 all 로 설정해야 한다."
Grounds   : "acks=1 일 때 leader 장애 시 데이터 손실이 발생한다."
Warrant   : "금융 도메인에서 메시지 손실은 자산 손실이다."
Qualifier : "단, 일부 손실이 허용되는 경우 - 로그 수집 - 에는 acks=1 도 합리적."
Rebuttal  : "acks=all 은 latency 를 늘린다. throughput 이 중요한 시스템에선 trade-off 검토 필요."
```

## Steel Man

반대 입장을 다룰 때, **가장 강한 형태로 재구성한 뒤** 반박한다.

- ❌ "어떤 사람들은 잘 모르고 acks=0 을 쓴다"
- ✅ "acks=0 을 선택하는 가장 강력한 근거는 latency 최소화다. 실시간 센서 데이터처럼 개별 메시지 손실보다 전체 throughput 이 더 중요한 시스템에선 합당한 선택이다. 다만 이 글의 결제 시스템 맥락에선 ..."

## Skeptical Stance

- **과신 회피.** "X 는 항상 ~ 해야 한다" 보다 "현재 아키텍처에선 X 가 ~ 로 판단된다" 가 낫다.
- **반증 가능성.** 주장할 때, 어떤 조건에서 그 주장이 틀릴 수 있는지 안다.
- **근거 출처 명시.** 독자가 검증할 수 있게.

## blog-critic 의 평가 체크리스트

- [ ] 모든 claim 에 grounds 가 있는가?
- [ ] Qualifier 가 적절한가? (과신은 없는가)
- [ ] 반대 입장은 Steel Man 으로 다뤘는가?
- [ ] Trade-off 가 명시적인가?
- [ ] 수치·고유명사 없는 "주장 문단" 이 있는가?
- [ ] 첫 문장이 일반론으로 시작하는가? (예: "최근 MSA 가 각광받고 있습니다") → 구체 시나리오로 교체 권고

Verdict: `APPROVE` / `ITERATE [구체적 개선 항목 3~5개]` / `REJECT [근본 결함]`
