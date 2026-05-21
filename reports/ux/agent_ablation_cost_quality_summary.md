| run_id | agent | prompt_path | n | candidate_n | success_rate | avg_time_s | avg_sus | avg_friction_count | rule_words_ok_rate | friction_prefix_ok_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ablation_ux_cq_rerun_gpt41_v2_hybrid_n2_t07_20260515_083706 | hybrid | configs/prompts/ux_simulation_v2.md | 60 | 0.6333 | 0.6 | 118.5 | 45.5833 | 0.6 | 1.0 | 0.6 |
| ablation_ux_cq_rerun_gpt41_v3_hybrid_sts_auto_n2_t07_20260515_083706 | hybrid | configs/prompts/ux_simulation_v2.md | 60 | 0.65 | 0.6 | 121.5 | 45.375 | 0.6 | 1.0 | 0.6 |
| ablation_ux_cq_rerun_gpt41_v2_single_20260515_083706 | single_pass | configs/prompts/ux_simulation_v2.md | 60 | 0.2333 | 0.2333 | 147.5 | 48.0833 | 0.2333 | 1.0 | 0.2333 |
| ablation_ux_cq_rerun_gpt41_v2_wts_n2_t07_20260515_083706 | write_then_score | configs/prompts/ux_simulation_v2.md | 60 | 0.75 | 0.5667 | 119.0 | 45.875 | 0.5667 | 1.0 | 0.5667 |
| ablation_ux_cq_rerun_gpt41_v3_wts_auto_n2_t07_20260515_083706 | write_then_score | configs/prompts/ux_simulation_v2.md | 60 | 0.8167 | 0.6 | 124.0 | 46.125 | 0.6 | 1.0 | 0.6 |
