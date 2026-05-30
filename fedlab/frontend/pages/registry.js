import Link from "next/link";
import {
  MODELS,
  DOMAIN_LABELS,
  statusLabel,
  truncateWallet,
} from "../lib/registryData";

export default function Registry() {
  return (
    <div className="container">
      <h1>Model Registry</h1>
      <p className="muted">
        Models tracked by FedLab, each tied to a domain validation packet. Demo
        and candidate rows are labeled honestly until live validation runs.
      </p>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Domain</th>
              <th>Benchmark</th>
              <th>Score</th>
              <th>Version</th>
              <th>Status</th>
              <th>Contributor</th>
            </tr>
          </thead>
          <tbody>
            {MODELS.map((m) => (
              <tr key={m.id}>
                <td>{m.name}</td>
                <td>{DOMAIN_LABELS[m.domain] || m.domain}</td>
                <td>{m.benchmark}</td>
                <td>{m.score}</td>
                <td>{m.version}</td>
                <td>
                  <span className={`badge badge-${m.status}`}>
                    {statusLabel(m.status)}
                  </span>
                </td>
                <td>
                  <code>{truncateWallet(m.contributor_wallet)}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="muted">
        Want to see how a model is verified?{" "}
        <Link href="/packets">Browse the validation packets →</Link>
      </p>
    </div>
  );
}
