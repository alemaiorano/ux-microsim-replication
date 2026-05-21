# UX Proxy Validation (Summary)

| dataset | records | avg_rating | pos_rate | neg_rate | jaccard | weighted_jaccard | alignment_method | embedding_model | weights_domain |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proxy_validation_amazon_low_rated | 79531 | 3.37 | 0.322 | 0.032 | 0.6 | 0.009 | lexical | n/a | app_reviews |
| proxy_validation_amazon_low_rated_annotated | 8971 | 1.237 | 0.157 | 0.083 | 0.6 | 0.013 | lexical | n/a | app_reviews |
| proxy_validation_gojek | 1670237 | 4.112 | 0.061 | 0.007 | 0.6 | 0 | lexical | n/a | app_reviews |
| proxy_validation_tinder | 664222 | 2.854 | 0.209 | 0.045 | 0.6 | 0.001 | lexical | n/a | app_reviews |
| proxy_validation_twitter | 2811774 | n/a | 0.058 | 0.027 | 0.6 | 0 | lexical | n/a | support_tweets |

## Top friction categories by dataset
- proxy_validation_amazon_low_rated: latency (1755.6), errors (828), copy_clarity (266), navigation (242), configuration (144.2)
- proxy_validation_amazon_low_rated_annotated: latency (826.1), errors (488), configuration (368.9), copy_clarity (231), navigation (108)
- proxy_validation_gojek: latency (49673.8), errors (11141), search (8892), navigation (4200), copy_clarity (3043)
- proxy_validation_tinder: errors (14206), latency (8278.6), policy_gate (3565.6), search (1981), configuration (1739.5)
- proxy_validation_twitter: errors (44412), latency (39267), comparison (34596.1), policy_gate (12726), configuration (12375)