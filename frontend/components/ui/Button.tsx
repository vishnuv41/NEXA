"use client";

import { cn } from "@/lib/utils";
import { forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost" | "outline";
type ButtonSize = "sm" | "default" | "lg" | "icon";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "default", children, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center gap-2 rounded-lg font-medium btn-mode-shadow transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]";

    const variants: Record<ButtonVariant, string> = {
      primary: "bg-primary text-white hover:bg-primary-hover focus-visible:ring-primary",
      secondary: "bg-surface text-text hover:bg-surface-hover focus-visible:ring-border-strong border border-border",
      danger: "bg-danger text-white hover:bg-danger-hover focus-visible:ring-danger",
      ghost: "bg-transparent hover:bg-surface-hover text-text-secondary hover:text-text focus-visible:ring-border-strong",
      outline: "border border-border bg-surface text-text hover:bg-surface-hover focus-visible:ring-border-strong",
    };

    const sizes: Record<ButtonSize, string> = {
      sm: "px-2 py-1 text-xs gap-1.5",
      default: "px-3 py-1.5 text-sm gap-2",
      lg: "px-4 py-2 text-base gap-2",
      icon: "p-1.5",
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";