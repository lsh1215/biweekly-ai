# Kafka Exactly-Once Semantics: 중복 0.03%를 0%로 만든 여정

지난 분기 결제 시스템에서 환불 이벤트가 중복 처리되어 같은 금액을 두 번 환불한 사례가 발생했다. 일 평균 1만 건의 이벤트 중 0.03%가 중복되었고, 이는 월 9건의 고객 불만으로 이어졌다. at-least-once 전달 보장만으로는 consumer 측에서 별도의 중복 제거 로직이 필수였고, 이 시점에서 Kafka의 exactly-once semantics(EOS)가 구조적 해결책이 될 수 있었다.

## EOS의 본질

EOS는 단일 설정이 아니라 세 가지 메커니즘의 조합이다. producer idempotence(`enable.idempotence=true`)는 재전송 시 broker가 sequence number로 중복을 감지하고 폐기한다. transactional id를 지정하면 producer가 여러 partition에 쓴 메시지를 원자적 단위로 묶는다. consumer 측에서 `isolation.level=read_committed`를 설정하면 commit된 transaction만 읽는다.

## 적용 과정

producer 설정에 `enable.idempotence=true`와 `transactional.id=payment-refund-processor`를 추가했다. consumer는 `isolation.level=read_committed`로 변경하고, transaction API(`beginTransaction()`, `commitTransaction()`)를 감싸 3개 downstream topic에 쓰는 로직을 하나의 transaction으로 묶었다. 기존 at-least-once 코드에서는 중간 실패 시 일부 메시지만 쓰여지는 상황이 발생했으나, EOS 적용 후 all-or-nothing이 보장되었다.

## 측정 결과

중복률은 0.03%에서 0%로 떨어졌다(4주간 모니터링). p99 latency는 47ms에서 62ms로 증가했고, throughput은 약 15% 감소했다. transaction coordinator가 commit 요청을 조정하는 과정에서 추가 RTT가 발생했고, broker 측 CPU 사용률이 8%p 상승했다. 이는 예상된 비용이며, 중복 제거 로직을 별도로 유지하는 것보다 운영 복잡도가 낮았다.

## 의도적 한계

EOS는 Kafka 내부 전달만 보장한다. consumer가 메시지를 읽고 외부 DB에 쓰는 과정은 여전히 at-least-once이므로, DB 쓰기 자체를 멱등하게 설계해야 한다(unique constraint, conditional update). producer → Kafka → consumer read까지만 exactly-once이고, 그 이후는 application 책임이다. 또한 transaction coordinator가 SPOF가 될 수 있어, `transaction.state.log.replication.factor=3` 이상 유지가 필요하다.

## 요약

- EOS는 `enable.idempotence` + transactional id + `isolation.level=read_committed` 조합이다.
- 중복률 0.03% → 0%, p99 latency 47ms → 62ms, throughput -15% trade-off가 있다.
- transaction coordinator 복제 계수와 monitoring이 운영 요건에 추가된다.