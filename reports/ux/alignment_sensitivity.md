# UX Alignment Sensitivity (Amazon annotated)

| run | method | top_k | tfidf_threshold | embedding_threshold | jaccard | weighted_jaccard |
| --- | --- | --- | --- | --- | --- | --- |
| proxy_validation_amazon_low_rated_annotated_lex_k6 | lexical | 6 | n/a | n/a | 0.333 | 0.017 |
| proxy_validation_amazon_low_rated_annotated_lex_k10 | lexical | 10 | n/a | n/a | 1.000 | 0.017 |
| proxy_validation_amazon_low_rated_annotated_tfidf_t005 | tfidf | 8 | 0.05 | n/a | 0.778 | 0.003 |
| proxy_validation_amazon_low_rated_annotated_tfidf_t020 | tfidf | 8 | 0.2 | n/a | 0.778 | 0.002 |
| proxy_validation_amazon_low_rated_annotated_embed_t025 | embedding | 8 | n/a | 0.25 | 0.778 | 0.061 |
| proxy_validation_amazon_low_rated_annotated_embed_t045 | embedding | 8 | n/a | 0.45 | 0.778 | 0.049 |