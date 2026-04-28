# ML Engineer 지원서

저는 졸업 프로젝트로 의료 가이드라인 검색을 위한 RAG 시스템을 설계하고 구현했습니다. 이 프로젝트에서 retrieval recall@10 지표를 0.78까지 끌어올리며, RAG 파이프라인의 핵심 병목인 retrieval 단계를 체계적으로 최적화한 경험을 쌓았습니다.

초기 baseline으로 BM25와 dense retrieval(BERT 기반)을 각각 구현하고 성능을 비교했습니다. BM25는 exact match에 강했지만 의료 용어의 동의어 처리가 약했고, dense retrieval은 그 반대였습니다. 두 방식을 hybrid로 결합한 후 recall이 0.62에 도달했지만, 사용자 쿼리가 짧고 애매할 때 정확도가 떨어지는 문제가 있었습니다. 이를 해결하기 위해 query rewriting 레이어를 추가하여 사용자 질문을 의료 용어로 확장했고, 최종적으로 recall@10을 0.78까지 개선했습니다. PyTorch와 HuggingFace Transformers로 모델을 fine-tuning하고, evaluation metric을 자동화하는 파이프라인을 직접 작성했습니다.

3개월 인턴 기간 동안에는 추천 모델의 A/B 테스트 파이프라인을 구축했습니다. 실험군과 대조군을 자동으로 분할하고, click-through rate를 실시간으로 집계하는 스크립트를 작성하여 모델 개선이 1.4% CTR 향상으로 이어졌음을 검증했습니다. 이 경험을 통해 모델 성능을 production 환경에서 측정하고 반복 개선하는 전체 사이클을 익혔습니다.

귀사의 RAG 제품에서는 retrieval 평가 자산과 실험 방법론을 그대로 이전할 수 있다고 생각합니다. 도메인별 retrieval 성능을 정량화하고, hybrid 전략으로 개선하는 과정을 경험했기 때문에, 신입이지만 빠르게 팀에 기여할 수 있습니다.

프로젝트 코드와 실험 노트북은 GitHub에 공개되어 있습니다. 면접 기회를 주시면 더 자세히 설명드리겠습니다.