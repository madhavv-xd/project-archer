"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

// Chat replies come from different models with different markdown habits
// (GFM tables, single-newline paragraphs). remark-gfm covers tables/strikethrough/
// task lists; remark-breaks turns single newlines into <br> so a model that
// skips blank lines between lines doesn't render as one run-on paragraph.
export function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed [&_a]:text-primary [&_a]:underline [&_h1]:font-display [&_h1]:text-base [&_h1]:font-semibold [&_h2]:font-display [&_h2]:text-base [&_h2]:font-semibold [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5 [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
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
