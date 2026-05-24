import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "inline-flex rounded-full bg-surface-elevated px-3 py-1 text-xs leading-5 text-body",
        className,
      )}
      {...props}
    />
  );
}

