# UX Proxy Validation (Summary)

| dataset | records | avg_rating | pos_rate | neg_rate | jaccard | weighted_jaccard | alignment_method | embedding_model | weights_domain |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proxy_validation_getsentry__sentry_lex | 50 | n/a | 0.02 | 0.08 | 0.25 | 0.099 | lexical | n/a | app_reviews |
| proxy_validation_grafana_lex | 50 | n/a | 0.02 | 0.04 | 0.25 | 0.105 | lexical | n/a | app_reviews |
| proxy_validation_jaegertracing__jaeger_lex | 50 | n/a | 0 | 0.04 | 0.25 | 0.138 | lexical | n/a | app_reviews |
| proxy_validation_open-telemetry__opentelemetry-collector_lex | 50 | n/a | 0 | 0.04 | 0.429 | 0.102 | lexical | n/a | app_reviews |
| proxy_validation_open-telemetry__opentelemetry-js_lex | 50 | n/a | 0.02 | 0.02 | 0.25 | 0.118 | lexical | n/a | app_reviews |
| proxy_validation_openzipkin__zipkin_lex | 50 | n/a | 0 | 0.16 | 0.25 | 0.024 | lexical | n/a | app_reviews |
| proxy_validation_prometheus_lex | 50 | n/a | 0 | 0.08 | 0.429 | 0.112 | lexical | n/a | app_reviews |

## Top friction categories by dataset
- proxy_validation_getsentry__sentry_lex: errors (15), search (13), policy_gate (7.2), latency (6.6), configuration (6.3)
- proxy_validation_grafana_lex: errors (15), search (9), configuration (4.9), navigation (3), latency (2.2)
- proxy_validation_jaegertracing__jaeger_lex: errors (18), search (13), configuration (11.9), traceability (5.6), latency (4.4)
- proxy_validation_open-telemetry__opentelemetry-collector_lex: errors (19), configuration (8.4), latency (7.7), export (2), comparison (1.8)
- proxy_validation_open-telemetry__opentelemetry-js_lex: errors (15), configuration (8.4), export (6.5), traceability (5.6), latency (5.5)
- proxy_validation_openzipkin__zipkin_lex: errors (22), latency (3.3), policy_gate (1.6), configuration (1.4), export (1)
- proxy_validation_prometheus_lex: errors (17), search (12), latency (5.5), comparison (5.4), configuration (4.9)