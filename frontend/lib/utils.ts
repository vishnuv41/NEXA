import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatDateTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

export function getDecisionColor(decision: string): string {
  switch (decision) {
    case "block":
    case "would_block":
      return "text-danger bg-danger-light";
    case "challenge":
      return "text-warning bg-warning-light";
    case "rate_limit":
      return "text-warning bg-warning-light";
    case "monitor":
      return "text-info bg-info-light";
    case "allow":
      return "text-success bg-success-light";
    default:
      return "text-text-secondary bg-surface-hover";
  }
}

export function getDecisionIcon(decision: string): string {
  switch (decision) {
    case "block":
    case "would_block":
      return "X";
    case "challenge":
      return "ShieldAlert";
    case "rate_limit":
      return "Gauge";
    case "monitor":
      return "Eye";
    case "allow":
      return "Check";
    default:
      return "HelpCircle";
  }
}

export function getThreatTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    benign: "Benign",
    sql_injection: "SQL Injection",
    xss: "XSS",
    path_traversal: "Path Traversal",
    command_injection: "Command Injection",
    other_malicious: "Other Malicious",
  };
  return labels[type] || type;
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case "critical":
      return "text-danger bg-danger-light";
    case "high":
      return "text-danger bg-danger-light";
    case "medium":
      return "text-warning bg-warning-light";
    case "low":
      return "text-info bg-info-light";
    default:
      return "text-text-secondary bg-surface-hover";
  }
}

export function getRiskColor(score: number): string {
  if (score >= 0.8) return "text-danger";
  if (score >= 0.6) return "text-warning";
  if (score >= 0.4) return "text-warning";
  if (score >= 0.2) return "text-info";
  return "text-success";
}

export function getRiskBg(score: number): string {
  if (score >= 0.8) return "bg-danger-light";
  if (score >= 0.6) return "bg-warning-light";
  if (score >= 0.4) return "bg-warning-light";
  if (score >= 0.2) return "bg-info-light";
  return "bg-success-light";
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + "...";
}

export function parseSSEEvent(data: string): { type: string; data: any } | null {
  try {
    const parsed = JSON.parse(data);
    return { type: parsed.type || "event", data: parsed };
  } catch {
    return null;
  }
}

export function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}