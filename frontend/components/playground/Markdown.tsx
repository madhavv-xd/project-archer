"use client";

import ReactMarkdown from "react-markdown";

// Minimal markdown for chat replies: code fences, inline code, lists, headings,
// bold, links. No GFM/tables until a response actually needs them.
export function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed [&_a]:text-primary [&_a]:underline [&_h1]:font-display [&_h1]:text-base [&_h1]:font-semibold [&_h2]:font-display [&_h2]:text-base [&_h2]:font-semibold [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5">
      <ReactMarkdown
        components={{
          pre: ({ children }) => (
            <pre className="overflow-x-auto rounded-lg border border-border bg-background p-3 text-xs">
              {children}
            </pre>
          ),
          code: ({ className, children }) =>
            className ? (
              <code className={className}>{children}</code>
            ) : (
              <code className="rounded bg-background px-1 py-0.5 text-xs">{children}</code>
            ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
