"use client";

import { cn } from "@/lib/utils";
import { forwardRef } from "react";

interface SeparatorProps extends React.HTMLAttributes<HTMLHRElement> {
  orientation?: "horizontal" | "vertical";
  decorative?: boolean;
}

export const Separator = forwardRef<HTMLHRElement, SeparatorProps>(
  ({ className, orientation = "horizontal", decorative = true, ...props }, ref) => (
    <hr
      ref={ref}
      aria-orientation={orientation}
      aria-hidden={decorative}
      className={cn(
        "border-border",
        orientation === "horizontal" ? "w-full" : "h-full",
        className
      )}
      {...props}
    />
  )
);

Separator.displayName = "Separator";