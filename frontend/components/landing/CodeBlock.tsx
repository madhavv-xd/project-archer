"use client";

import { useState, type ReactNode } from "react";

export function CodeBlock({
  file,
  copyText,
  children,
}: {
  file: string;
  copyText: string;
  children: ReactNode;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked — no-op */
    }
  }

  return (
    <div className="lp-code">
      <div className="lp-code-bar">
        <span className="lp-dot" />
        <span className="lp-dot" />
        <span className="lp-dot" />
        <span className="lp-code-file lp-mono">{file}</span>
        <button
          className={`lp-copy ${copied ? "is-copied" : ""}`}
          onClick={copy}
          type="button"
        >
          {copied ? "copied ✓" : "copy"}
        </button>
      </div>
      <pre>
        <code>{children}</code>
      </pre>
    </div>
  );
}
