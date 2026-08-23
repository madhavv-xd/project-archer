"use client";

/* A native <select>'s option list is painted by the OS, so it lands as
   white-on-blue over the dark theme no matter what CSS says. Radix renders the
   list as real DOM, which is the only way to theme it. */

import * as React from "react";
import { CaretDown, Check } from "@phosphor-icons/react";
import { Select as SelectPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";

const Select = SelectPrimitive.Root;
const SelectValue = SelectPrimitive.Value;

function SelectTrigger({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      data-slot="select-trigger"
      className={cn(
        // Handoff §Colour: accent tint + accent border, never a solid fill.
        "flex h-8 items-center justify-between gap-2 rounded-full border border-(--accent-800) bg-primary/10 px-3 font-mono text-caption text-(--accent-300) transition-colors outline-none",
        "hover:bg-primary/20 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/15",
        "disabled:cursor-not-allowed disabled:opacity-50 [&>span]:truncate",
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <CaretDown size={12} className="shrink-0 opacity-70" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}

function SelectContent({
  className,
  children,
  position = "popper",
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        data-slot="select-content"
        position={position}
        className={cn(
          "z-50 max-h-72 min-w-(--radix-select-trigger-width) overflow-hidden rounded-lg border border-(--neutral-800) bg-card p-1 shadow-[0_0_0_1px_var(--neutral-600),0_6px_18px_rgba(0,0,0,.55)]",
          position === "popper" && "translate-y-1",
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport className="p-0">{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

function SelectItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      data-slot="select-item"
      className={cn(
        "relative flex cursor-pointer items-center gap-2 rounded-[6px] py-1.5 pr-2 pl-7 font-mono text-caption text-foreground outline-none select-none",
        "data-highlighted:bg-primary/15 data-highlighted:text-(--accent-200)",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className,
      )}
      {...props}
    >
      <span className="absolute left-2 flex items-center">
        <SelectPrimitive.ItemIndicator>
          <Check size={12} weight="bold" className="text-primary" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}

export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue };
