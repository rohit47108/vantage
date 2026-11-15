/** Original Vantage identity, shared across workspaces. */
export function Brand({ context }: { context?: string }) {
  return (
    <a className="brand" href="/" aria-label="Vantage home">
      <svg width="24" height="24" viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="9" fill="none" stroke="#89d7e7" strokeWidth="2"/><circle cx="16" cy="16" r="3" fill="#ecf3f7"/></svg>
      <strong>Vantage</strong>
      {context && <span className="brand-context">/ {context}</span>}
    </a>
  );
}
