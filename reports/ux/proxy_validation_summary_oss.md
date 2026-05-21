# UX Proxy Validation (Summary)

| dataset | records | avg_rating | pos_rate | neg_rate | jaccard | weighted_jaccard | alignment_method | embedding_model | weights_domain |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proxy_validation_grafana_bge | 50 | n/a | 0.02 | 0.04 | 0.429 | 0.271 | embedding | bge-m3 | app_reviews |
| proxy_validation_grafana_lex | 50 | n/a | 0.02 | 0.04 | 0.25 | 0.105 | lexical | n/a | app_reviews |
| proxy_validation_prometheus_bge | 50 | n/a | 0 | 0.08 | 0.429 | 0.24 | embedding | bge-m3 | app_reviews |
| proxy_validation_prometheus_lex | 50 | n/a | 0 | 0.08 | 0.429 | 0.112 | lexical | n/a | app_reviews |

## Top friction categories by dataset
- proxy_validation_grafana_bge: errors (15), search (9), configuration (4.9), navigation (3), latency (2.2)
- proxy_validation_grafana_lex: errors (15), search (9), configuration (4.9), navigation (3), latency (2.2)
- proxy_validation_prometheus_bge: errors (17), search (12), latency (5.5), comparison (5.4), configuration (4.9)
- proxy_validation_prometheus_lex: errors (17), search (12), latency (5.5), comparison (5.4), configuration (4.9)