import { useState } from "react";

export default function WalletConnect() {
  const [wallet, setWallet] = useState(null);

  async function connect() {
    if (typeof window === "undefined") return;
    const provider = window.solana;
    if (!provider) {
      alert("No Solana wallet detected. Install Phantom or another Solana wallet.");
      return;
    }
    try {
      const resp = await provider.connect();
      setWallet(resp.publicKey.toString());
    } catch (e) {
      console.error(e);
    }
  }

  if (wallet) {
    return (
      <button className="btn secondary" onClick={() => setWallet(null)}>
        {wallet.slice(0, 4)}...{wallet.slice(-4)}
      </button>
    );
  }
  return (
    <button className="btn" onClick={connect}>
      Connect Wallet
    </button>
  );
}
