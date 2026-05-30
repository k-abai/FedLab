import Link from "next/link";
import { MODELS, DOMAIN_LABELS, statusLabel } from "../lib/registryData";

export default function Home() {
  return (
    <div className="container">
      <section className="hero">
        <h1>Verified AI models for real-world domains.</h1>
        <p>
          FedLab tracks models that pass standardized validation packets across
          software engineering, tabular prediction, and financial forecasting.
        </p>
        <div style={{ marginTop: 24 }}>
          <Link className="btn" href="/registry">
            View Model Registry
          </Link>
        </div>
      </section>

      <div className="card">
        <h2>Verified tracks</h2>
        <div className="steps">
          {MODELS.map((m) => (
            <div className="step" key={m.id}>
              <div className="num">{DOMAIN_LABELS[m.domain] || m.domain}</div>
              <h3>{m.name}</h3>
              <p>
                {m.benchmark} · {m.score}
                <br />
                <span className={`badge badge-${m.status}`}>
                  {statusLabel(m.status)}
                </span>
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>How verification works</h2>
        <div className="steps">
          <div className="step">
            <div className="num">01</div>
            <h3>Submit</h3>
            <p>A contributor submits a model to the registry for a domain.</p>
          </div>
          <div className="step">
            <div className="num">02</div>
            <h3>Validate</h3>
            <p>
              The model runs the domain&apos;s validation packet — a held-out
              benchmark with leakage checks.
            </p>
          </div>
          <div className="step">
            <div className="num">03</div>
            <h3>Verify</h3>
            <p>
              A passing result is recorded with a validation hash, ready to be
              anchored on-chain.
            </p>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Bags + Web3 integration hooks</h2>
        <p className="muted">
          The backend is wired with seams for Bags API project/token stats and a
          Solana proof-of-validation path. Live credentials and on-chain
          contracts are <strong>not</strong> included in this build — the
          integration modules return clearly-labeled mock/not-configured status
          until env vars are set.
        </p>
        <ul className="muted" style={{ marginTop: 8 }}>
          <li>
            Bags: <code>get_project_stats()</code>,{" "}
            <code>get_token_stats()</code>, <code>get_integration_status()</code>
          </li>
          <li>
            Solana: <code>build_validation_proof()</code>,{" "}
            <code>check_onchain_proof()</code> (no token mint/transfer, no
            contract)
          </li>
        </ul>
      </div>
    </div>
  );
}
