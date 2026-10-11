"use client";

import { cn } from "@/lib/utils";
import { forwardRef } from "react";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "danger" | "warning" | "success" | "info" | "neutral";
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "default", children, ...props }, ref) => {
    const variants = {
      default: "bg-surface-hover text-text-secondary border border-border",
      danger: "bg-danger-light text-danger border border-danger/20 font-medium",
      warning: "bg-warning-light text-warning border border-warning/20 font-medium",
      success: "bg-success-light text-success border border-success/20 font-medium",
      info: "bg-info-light text-info border border-info/20 font-medium",
      neutral: "bg-surface-hover text-text-secondary border border-border",
    };

    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
          variants[variant],
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";