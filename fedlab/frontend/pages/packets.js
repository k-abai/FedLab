import { PACKETS, DOMAIN_LABELS, statusLabel } from "../lib/registryData";

export default function Packets() {
  return (
    <div className="container">
      <h1>Validation Packets</h1>
      <p className="muted">
        A validation packet defines how a model in a domain gets verified: the
        dataset, the metric, the evaluation script, the current best score, and
        the leakage checks that keep the score honest.
      </p>

      {PACKETS.map((p) => (
        <div className="card" key={p.id}>
          <h2>{p.benchmark}</h2>
          <div className="metric-label">
            {DOMAIN_LABELS[p.domain] || p.domain} ·{" "}
            <span className={`badge badge-${p.status}`}>
              {statusLabel(p.status)}
            </span>
          </div>

          <p style={{ marginTop: 12 }}>{p.dataset_summary}</p>

          <div className="packet-grid">
            <div>
              <div className="metric-label">Metric</div>
              <div>{p.metric}</div>
            </div>
            <div>
              <div className="metric-label">Current best score</div>
              <div>{p.current_best_score}</div>
            </div>
            <div>
              <div className="metric-label">Latest validation hash</div>
              <div>
                <code>{p.validation_hash || "— (not yet anchored)"}</code>
              </div>
            </div>
          </div>

          <div className="metric-label" style={{ marginTop: 16 }}>
            Evaluation script
          </div>
          <pre className="code-block">{p.evaluation_command}</pre>

          <div className="metric-label" style={{ marginTop: 12 }}>
            Leakage checks
          </div>
          <ul className="muted">
            {p.leakage_checks.map((c) => (
              <li key={c}>
                <code>{c}</code>
              </li>
            ))}
          </ul>

          <button className="btn" style={{ marginTop: 12 }} disabled>
            Submit model (coming soon)
          </button>
        </div>
      ))}
    </div>
  );
}
