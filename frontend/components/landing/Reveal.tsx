"use client";

import { useEffect, useRef, useState, type ElementType, type ReactNode } from "react";

/** Adds `is-in` once the element scrolls into view (one-shot). Pair with the
    `.lp-reveal` / `.is-in` CSS, or any class that keys off `.is-in`. */
export function Reveal({
  children,
  as: Tag = "div",
  className = "",
  base = "lp-reveal",
  style,
}: {
  children: ReactNode;
  as?: ElementType;
  className?: string;
  base?: string;
  style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          io.disconnect();
        }
      },
      { threshold: 0.18, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <Tag
      ref={ref}
      className={`${base} ${className} ${shown ? "is-in" : ""}`.trim()}
      style={style}
    >
      {children}
    </Tag>
  );
}
