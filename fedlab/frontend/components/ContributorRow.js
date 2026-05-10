function truncate(addr) {
  if (!addr) return "—";
  if (addr.length <= 10) return addr;
  return `${addr.slice(0, 4)}...${addr.slice(-4)}`;
}

export default function ContributorRow({ rank, contributor }) {
  return (
    <tr>
      <td>{rank}</td>
      <td><code>{truncate(contributor.wallet)}</code></td>
      <td>{contributor.contributions ?? 0}</td>
      <td>{(contributor.improvement ?? 0).toFixed(4)}</td>
      <td>{(contributor.tokens ?? 0).toFixed(2)} $FZIQ</td>
    </tr>
  );
}
