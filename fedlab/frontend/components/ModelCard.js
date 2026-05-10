const BASELINE_BRIER = 0.25;
const IPFS_GATEWAY = process.env.NEXT_PUBLIC_IPFS_GATEWAY || "https://ipfs.io/ipfs";

export default function ModelCard({ model }) {
  if (!model) {
    return (
      <div className="card">
        <h2>Latest Model</h2>
        <p className="muted">Loading model metadata...</p>
      </div>
    );
  }

  const score = typeof model.score === "number" ? model.score : null;
  const improvement = score != null ? BASELINE_BRIER - score : null;
  const cid = model.ipfs_cid;

  return (
    <div className="card">
      <h2>Latest Model</h2>
      <div className="metric-label">Brier score</div>
      <div className="metric">{score != null ? score.toFixed(4) : "—"}</div>
      <div className="muted">
        Baseline (always-0.5): {BASELINE_BRIER.toFixed(2)} ·{" "}
        {improvement != null ? `${(improvement * 100).toFixed(1)}% better` : "—"}
      </div>
      <div style={{ marginTop: 16 }}>
        {cid ? (
          <a className="btn" href={`${IPFS_GATEWAY}/${cid}`} target="_blank" rel="noreferrer">
            Download Latest Model
          </a>
        ) : (
          <button className="btn" disabled>
            No model published yet
          </button>
        )}
        {cid ? (
          <div className="muted" style={{ marginTop: 8, fontSize: 13 }}>
            CID: <code>{cid}</code>
          </div>
        ) : null}
      </div>
    </div>
  );
}
