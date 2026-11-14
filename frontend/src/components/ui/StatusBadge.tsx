import React from "react";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: "healthy" | "connected" | "degraded" | "disconnected" | "not_configured" | "error" | string;
  label?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label }) => {
  const normalizedStatus = status.toLowerCase();

  const getStyle = () => {
    switch (normalizedStatus) {
      case "healthy":
      case "connected":
        return "bg-emerald-950 text-emerald-400 border-emerald-800";
      case "degraded":
      case "not_configured":
        return "bg-amber-950 text-amber-400 border-amber-800";
      case "disconnected":
      case "error":
      case "auth_error":
        return "bg-rose-950 text-rose-400 border-rose-800";
      default:
        return "bg-slate-900 text-slate-400 border-slate-700";
    }
  };

  const getDotStyle = () => {
    switch (normalizedStatus) {
      case "healthy":
      case "connected":
        return "bg-emerald-400";
      case "degraded":
      case "not_configured":
        return "bg-amber-400";
      case "disconnected":
      case "error":
      case "auth_error":
        return "bg-rose-400";
      default:
        return "bg-slate-400";
    }
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border",
        getStyle()
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full animate-pulse", getDotStyle())} />
      {label || status.toUpperCase()}
    </span>
  );
};

