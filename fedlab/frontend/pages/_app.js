import "../styles/globals.css";
import Head from "next/head";
import Link from "next/link";
import WalletConnect from "../components/WalletConnect";

export default function App({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>FedLab</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </Head>
      <nav className="nav">
        <Link href="/" className="brand">FedLab</Link>
        <div className="links row-flex">
          <Link href="/">Home</Link>
          <Link href="/leaderboard">Leaderboard</Link>
          <WalletConnect />
        </div>
      </nav>
      <Component {...pageProps} />
    </>
  );
}
