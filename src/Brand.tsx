/** The supplied Vantage wordmark, shared by every workspace header. */
export function Brand({ context }: { context?: string }) {
  return (
    <a className="brand" href="/" aria-label="Vantage home">
      <span className="brand-logo">
        <img
          src="/vantage-logo.png?v=66ba6ce6"
          alt="Vantage"
          width="1254"
          height="1254"
        />
      </span>
      {context && <span className="brand-context">/ {context}</span>}
    </a>
  );
}
