import { useEffect, useState } from "react";
import ContributorRow from "../components/ContributorRow";

const AGGREGATOR = process.env.NEXT_PUBLIC_AGGREGATOR_URL || "http://localhost:8000";
const REFRESH_MS = 60_000;

export default function Leaderboard() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const r = await fetch(`${AGGREGATOR}/leaderboard`);
        const j = await r.json();
        if (alive) setRows(j.contributors || []);
      } catch (e) {
        if (alive) setError(String(e));
      }
    }
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="container">
      <h1>Leaderboard</h1>
      <p className="muted">Top contributors by cumulative score improvement. Refreshes every 60s.</p>

      {error ? <div className="card">Aggregator offline: {error}</div> : null}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Wallet</th>
              <th>Contributions</th>
              <th>Score Improvement</th>
              <th>Tokens Earned</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="muted">No contributions yet.</td>
              </tr>
            ) : (
              rows.map((c, i) => (
                <ContributorRow key={c.wallet} rank={i + 1} contributor={c} />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
