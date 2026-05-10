import { useEffect, useState } from "react";
import ModelCard from "../components/ModelCard";

const AGGREGATOR = process.env.NEXT_PUBLIC_AGGREGATOR_URL || "http://localhost:8000";

export default function Home() {
  const [model, setModel] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    fetch(`${AGGREGATOR}/model/latest`)
      .then((r) => r.json())
      .then((j) => {
        if (alive) setModel(j);
      })
      .catch((e) => {
        if (alive) setError(String(e));
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="container">
      <section className="hero">
        <h1>Community-trained AI models. Free forever.</h1>
        <p>
          FedLab is a federated training network. Anyone can fine-tune the model on
          their own hardware, contribute a LoRA adapter, and earn rewards when their
          contribution improves the benchmark.
        </p>
      </section>

      <ModelCard model={model} />
      {error ? <div className="muted">Aggregator offline: {error}</div> : null}

      <div className="card">
        <h2>How it works</h2>
        <div className="steps">
          <div className="step">
            <div className="num">01</div>
            <h3>Download</h3>
            <p>Pull the latest base model and community-merged adapter via IPFS.</p>
          </div>
          <div className="step">
            <div className="num">02</div>
            <h3>Train</h3>
            <p>Fine-tune on your local data. Raw data never leaves your machine.</p>
          </div>
          <div className="step">
            <div className="num">03</div>
            <h3>Contribute</h3>
            <p>Submit your LoRA adapter. Pass the benchmark, earn $FZIQ.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
