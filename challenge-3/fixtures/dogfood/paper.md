# 비용 인지형 검색 증강 생성

## Abstract

Retrieval-augmented generation(RAG) 시스템은 검색 문서 수 k와 생성 모델 크기 선택에 따라 token 비용이 선형으로 증가한다. 본 연구는 쿼리 난이도를 사전 추정하여 모델과 k를 동적으로 할당하는 router를 제안한다. BERT-base 분류기로 쿼리를 3단계 난이도로 분류하고, Haiku/Sonnet/Opus 모델 계층과 k∈{2,5,8}을 매핑했다. 실험 결과 정확도 89.2%를 유지하면서 평균 비용을 32% 절감했으며, 비용-정확도 Pareto frontier에서 기존 고정 구성 대비 우월점을 달성했다.

## Introduction

RAG 시스템의 운영 비용은 두 변수의 함수다. 검색 단계에서 반환하는 문서 수 k는 context window token 수를 결정하고, 생성 단계에서 선택하는 모델은 token당 단가를 결정한다. 단순한 쿼리에도 k=10, Opus 모델을 일률 적용하면 비용이 과다 지출되고, 어려운 쿼리에 k=2, Haiku를 할당하면 정확도가 무너진다. 기존 연구는 retrieval 품질이나 모델 성능 중 하나만 최적화했으나, 두 축을 동시에 제어하는 router 설계는 다루지 않았다. 본 논문은 쿼리 난이도 추정을 통해 필요 최소 자원만 할당하는 전략을 제시한다.

## Method

난이도 분류기는 BERT-base를 fine-tuning하여 구현했다. 훈련 데이터는 쿼리-답변 쌍 1,200건에 human annotation으로 easy/medium/hard 라벨을 부여했다. 분류 결과에 따라 다음과 같이 자원을 할당한다:

- Easy: Haiku + k=2 (단순 사실 질의, 검색 문서 최소화)
- Medium: Sonnet + k=5 (추론 1단계 필요, 중간 context)
- Hard: Opus + k=8 (다단계 추론, 최대 context)

Router는 inference time에 BERT 분류 결과를 받아 해당 tier의 모델 API endpoint와 retrieval k를 동적으로 설정한다. 모든 tier는 동일한 벡터 DB에서 검색하며, re-ranking은 생략했다.

## Results

테스트 셋 500건에서 제안 시스템은 정확도 89.2%를 기록했다. 고정 구성(Opus + k=10 baseline)은 정확도 91.1%로 1.9%p 높았으나 평균 비용은 제안 시스템 대비 47% 더 컸다. Haiku + k=2 고정 구성은 비용이 68% 절감되었으나 정확도가 72.3%로 급락했다. Pareto frontier 분석 결과, 제안 router는 정확도 85~90% 구간에서 기존 고정 구성 대비 평균 32% 비용 절감을 달성했다. 분류기가 hard로 판정한 쿼리 중 78%가 Opus + k=8이 필요한 다단계 추론 문제였다.

## Discussion

Router 자체가 BERT-base inference 비용(쿼리당 ~0.02 토큰 상당)을 발생시키지만, 이는 Opus 호출 1회 절감으로 20배 이상 amortize된다. 분류 정확도가 85% 이상이면 전체 비용 절감 효과가 유지되며, 오분류로 인한 정확도 손실은 ensemble voting으로 완화 가능하다. 비용 절감이 가장 큰 구간은 easy 쿼리 비율이 40% 이상인 도메인이다. Router는 batch inference로 분류 latency를 3ms 이하로 유지할 수 있어 실시간 서비스에 적용 가능하다.

## Limitations

난이도 라벨링은 domain expert가 수작업으로 수행해야 하며, 1,200건 annotation에 약 40시간이 소요되었다. 새 도메인 적용 시 재학습이 필요하다. Haiku/Sonnet/Opus 모델의 가격 정책이 변동하면 tier 경계를 재조정해야 하며, 현재 구현은 가격 table을 하드코딩했다. 또한 retrieval k 설정이 문서 길이 분포에 민감하여, 평균 문서 길이가 2배 증가하면 k=5 tier의 비용 절감 효과가 반감될 수 있다.

## Conclusion

본 연구는 쿼리 난이도 기반 router를 통해 RAG 시스템의 비용-정확도 Pareto frontier에서 우월점을 달성했다. BERT-base 분류기와 3-tier 모델 할당 전략으로 정확도 손실 2%p 이내에서 평균 비용 32% 절감을 입증했다. 향후 모델 가격 변동과 도메인 drift를 자동 감지하여 tier 경계를 재조정하는 online learning 메커니즘이 필요하다. 지속적인 비용 모니터링과 분류기 재학습 파이프라인 구축이 프로덕션 안정성의 전제 조건이다.

## 요약

- BERT-base 난이도 분류기로 쿼리를 easy/medium/hard 3단계로 분류하고, Haiku/Sonnet/Opus 모델과 retrieval k∈{2,5,8}을 매핑했다.
- 테스트 셋 500건에서 정확도 89.2%를 유지하면서 baseline 대비 평균 비용을 32% 절감했다.
- Pareto frontier 분석 결과, 정확도 85~90% 구간에서 기존 고정 구성 대비 우월점을 달성했다.
- Router inference 비용은 Opus 호출 절감으로 20배 이상 amortize되며, batch 처리로 latency 3ms 이하 유지가 가능하다.
- 난이도 라벨링 비용과 모델 가격 변동에 대한 재조정 메커니즘이 프로덕션 적용의 과제로 남는다.