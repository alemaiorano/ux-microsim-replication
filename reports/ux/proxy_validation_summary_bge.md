# UX Proxy Validation (Summary)

| dataset | records | avg_rating | pos_rate | neg_rate | jaccard | weighted_jaccard | alignment_method | embedding_model | weights_domain |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proxy_validation_gojek_bge | 10000 | 3.659 | 0.038 | 0.009 | 0.25 | 0.128 | embedding | bge-m3 | app_reviews |
| proxy_validation_tinder_bge | 10000 | 2.517 | 0.203 | 0.041 | 0.111 | 0.087 | embedding | bge-m3 | app_reviews |
| proxy_validation_twitter_bge | 10000 | n/a | 0.057 | 0.023 | 0.429 | 0.123 | embedding | bge-m3 | support_tweets |

## Top friction categories by dataset
- proxy_validation_gojek_bge: latency (810.7), search (183), errors (96), navigation (40), policy_gate (39.2)
- proxy_validation_tinder_bge: errors (103), latency (95.7), policy_gate (76.8), search (72), configuration (38.5)
- proxy_validation_twitter_bge: errors (146), latency (125), comparison (116.9), configuration (52), policy_gate (25.2)