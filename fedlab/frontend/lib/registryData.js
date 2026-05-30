// Static mirror of fedlab/registry/models.json and validation_packets/*/packet.json.
// Used so the frontend builds and renders without a live backend. When the
// aggregator is running, pages can swap these for fetch() calls to
// NEXT_PUBLIC_AGGREGATOR_URL.

export const MODELS = [
  {
    id: "swe-model-v0",
    name: "SWE-Agent-LoRA-v0",
    domain: "software_engineering",
    benchmark: "SWE-bench++",
    score: "18.4% pass",
    metric: "resolved_rate",
    version: "0.1.0",
    status: "demo_verified",
    contributor_wallet: "FZiQDemoWa11etSWE000000000000000000000000000",
    validation_date: "2026-05-29",
    notes:
      "Seed/demo row. Score is an illustrative target, not a live result.",
  },
  {
    id: "tabpfn-fedlab-v0",
    name: "TabPFN-FedLab-v0",
    domain: "tabular",
    benchmark: "TabPFN validation packet",
    score: "0.91 ROC-AUC",
    metric: "roc_auc",
    version: "0.1.0",
    status: "candidate",
    contributor_wallet: "FZiQDemoWa11etTAB000000000000000000000000000",
    validation_date: "2026-05-29",
    notes: "Demo seed row. Candidate pending validation packet run.",
  },
  {
    id: "reservoir-fin-v0",
    name: "Reservoir-Fin-v0",
    domain: "finance",
    benchmark: "Financial reservoir validation packet",
    score: "0.037 RMSE",
    metric: "rmse",
    version: "0.1.0",
    status: "candidate",
    contributor_wallet: "FZiQDemoWa11etFIN000000000000000000000000000",
    validation_date: "2026-05-29",
    notes: "Demo seed row. Candidate pending validation packet run.",
  },
];

export const PACKETS = [
  {
    id: "swe_bench_plus_plus",
    domain: "software_engineering",
    benchmark: "SWE-bench++",
    dataset_summary:
      "Held-out real GitHub issues + repo snapshots. A model must produce a patch that makes failing tests pass without breaking existing tests.",
    metric: "resolved_rate",
    current_best_score: "18.4% pass",
    evaluation_command:
      "python -m validation_packets.swe_bench_plus_plus.evaluate --predictions <predictions.jsonl>",
    leakage_checks: [
      "held_out_split_not_in_pretraining",
      "issue_hash_blocklist",
      "patch_must_modify_only_in_repo_files",
    ],
    validation_hash: null,
    status: "demo",
  },
  {
    id: "tabpfn",
    domain: "tabular",
    benchmark: "TabPFN validation packet",
    dataset_summary:
      "Suite of small/medium tabular classification tasks (held-out). Scored on probabilistic predictions for the target.",
    metric: "roc_auc",
    current_best_score: "0.91 ROC-AUC",
    evaluation_command:
      "python -m validation_packets.tabpfn.evaluate --predictions <predictions.json>",
    leakage_checks: [
      "held_out_rows_not_in_fit_set",
      "no_target_column_in_features",
      "row_ids_disjoint_train_test",
    ],
    validation_hash: null,
    status: "candidate",
  },
  {
    id: "reservoir_finance",
    domain: "finance",
    benchmark: "Financial reservoir validation packet",
    dataset_summary:
      "Held-out financial time-series. One-step-ahead forecasts over a fixed eval window, scored on RMSE/MAE and directional accuracy with strict leakage controls.",
    metric: "rmse",
    current_best_score: "0.037 RMSE",
    evaluation_command:
      "python -m validation_packets.reservoir_finance.evaluate --predictions <predictions.json>",
    leakage_checks: [
      "no_future_leakage_in_features",
      "evaluation_window_is_strictly_out_of_sample",
      "no_overlap_between_warmup_and_eval",
      "timestamps_monotonic_increasing",
    ],
    validation_hash: null,
    status: "candidate",
  },
];

export const DOMAIN_LABELS = {
  software_engineering: "Software Engineering",
  tabular: "Tabular Prediction",
  finance: "Financial Forecasting",
};

export function statusLabel(status) {
  return {
    verified: "Verified",
    demo_verified: "Demo verified",
    candidate_verified: "Candidate verified",
    candidate: "Candidate",
    demo: "Demo",
  }[status] || status;
}

export function truncateWallet(addr) {
  if (!addr) return "—";
  if (addr.length <= 10) return addr;
  return `${addr.slice(0, 4)}…${addr.slice(-4)}`;
}
