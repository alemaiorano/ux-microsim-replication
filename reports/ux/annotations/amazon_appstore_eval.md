# Amazon Appstore Annotation Eval

- records_total: 500
- records_used: 500
- skipped_empty: 0
- unknown_gold: 0
- invalid_json: 0
- accuracy: 0.518
- macro_f1: 0.4252
- model: llama3.1:8b-instruct-q4_K_M

## Per-label metrics

| label | support | precision | recall | f1 |
| --- | --- | --- | --- | --- |
| compatibility_device | 51 | 0.600 | 0.294 | 0.395 |
| functionality_features | 216 | 0.592 | 0.537 | 0.563 |
| performance_stability | 136 | 0.757 | 0.640 | 0.693 |
| security_privacy | 8 | 0.250 | 0.250 | 0.250 |
| support_responsiveness | 35 | 0.450 | 0.257 | 0.327 |
| ui_ux | 54 | 0.227 | 0.556 | 0.323 |
| other | 0 | 0.000 | 0.000 | 0.000 |

## Confusion matrix (rows=gold, cols=pred)

| gold \ pred | compatibility_device | functionality_features | performance_stability | security_privacy | support_responsiveness | ui_ux | other |
| --- | --- | --- | --- | --- | --- | --- | --- |
| compatibility_device | 15 | 19 | 5 | 2 | 0 | 10 | 0 |
| functionality_features | 3 | 116 | 18 | 3 | 7 | 68 | 1 |
| performance_stability | 2 | 26 | 87 | 1 | 2 | 17 | 1 |
| security_privacy | 0 | 3 | 0 | 2 | 1 | 2 | 0 |
| support_responsiveness | 4 | 14 | 2 | 0 | 9 | 5 | 1 |
| ui_ux | 1 | 18 | 3 | 0 | 1 | 30 | 1 |
| other | 0 | 0 | 0 | 0 | 0 | 0 | 0 |