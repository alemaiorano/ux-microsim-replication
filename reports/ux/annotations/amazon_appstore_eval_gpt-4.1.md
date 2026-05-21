# Amazon Appstore Annotation Eval

- records_total: 500
- records_used: 500
- skipped_empty: 0
- unknown_gold: 0
- invalid_json: 1
- accuracy: 0.556
- macro_f1: 0.4375
- model: gpt-4.1

## Per-label metrics

| label | support | precision | recall | f1 |
| --- | --- | --- | --- | --- |
| compatibility_device | 51 | 0.471 | 0.314 | 0.376 |
| functionality_features | 216 | 0.608 | 0.676 | 0.640 |
| performance_stability | 136 | 0.744 | 0.662 | 0.700 |
| security_privacy | 8 | 0.400 | 0.250 | 0.308 |
| support_responsiveness | 35 | 0.385 | 0.143 | 0.208 |
| ui_ux | 54 | 0.442 | 0.352 | 0.392 |
| other | 0 | 0.000 | 0.000 | 0.000 |

## Confusion matrix (rows=gold, cols=pred)

| gold \ pred | compatibility_device | functionality_features | performance_stability | security_privacy | support_responsiveness | ui_ux | other |
| --- | --- | --- | --- | --- | --- | --- | --- |
| compatibility_device | 16 | 20 | 8 | 2 | 0 | 3 | 2 |
| functionality_features | 8 | 146 | 16 | 1 | 6 | 12 | 27 |
| performance_stability | 2 | 30 | 90 | 0 | 2 | 8 | 4 |
| security_privacy | 0 | 4 | 0 | 2 | 0 | 0 | 2 |
| support_responsiveness | 6 | 17 | 4 | 0 | 5 | 1 | 2 |
| ui_ux | 2 | 23 | 3 | 0 | 0 | 19 | 7 |
| other | 0 | 0 | 0 | 0 | 0 | 0 | 0 |