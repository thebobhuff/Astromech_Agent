"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";

type AgentTask = {
  id: string;
  title: string;
  description: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  priority: number;
  created_at: string;
};

type ProtocolHUDProps = {
  tasks: AgentTask[];
};

const STATUS_CONFIG = {
  in_progress: {
    color: "#3e93c1",
    label: "ACTIVE",
    glow: "rgba(62,147,193,0.5)",
  },
  pending: {
    color: "#f5a30a",
    label: "QUEUED",
    glow: "rgba(245,163,10,0.5)",
  },
  completed: {
    color: "#22c55e",
    label: "DONE",
    glow: "rgba(34,197,94,0.4)",
  },
  failed: {
    color: "#ef4444",
    label: "FAIL",
    glow: "rgba(239,68,68,0.5)",
  },
} as const;

type StatusKey = keyof typeof STATUS_CONFIG;

export default function ProtocolHUD({ tasks }: ProtocolHUDProps) {
  const stats = useMemo(() => {
    const counts = { in_progress: 0, pending: 0, completed: 0, failed: 0 };
    tasks.forEach((t) => {
      if (t.status in counts) counts[t.status as StatusKey]++;
    });
    return counts;
  }, [tasks]);

  return (
    <div className="flex flex-col gap-3 w-full max-w-full min-w-0 overflow-x-hidden">
      {/* Stat Pills */}
      <div className="grid grid-cols-2 gap-1.5 px-1 w-full max-w-full min-w-0">
        {(
          Object.entries(STATUS_CONFIG) as [StatusKey, (typeof STATUS_CONFIG)[StatusKey]][]
        ).map(([status, config]) => (
          <motion.div
            key={status}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-charcoal-blue-800/30 border border-charcoal-blue-700/25 min-w-0 max-w-full"
            whileHover={{
              borderColor:
                stats[status] > 0 ? config.color + "40" : undefined,
            }}
          >
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={{
                backgroundColor: config.color,
                boxShadow:
                  stats[status] > 0 ? `0 0 6px ${config.glow}` : "none",
                opacity: stats[status] > 0 ? 1 : 0.3,
              }}
            />
            <span className="text-[9px] uppercase tracking-wider text-slate-500 flex-1 min-w-0 truncate">
              {config.label}
            </span>
            <span
              className="text-xs font-mono font-bold"
              style={{
                color: stats[status] > 0 ? config.color : "#334155",
              }}
            >
              {stats[status]}
            </span>
          </motion.div>
        ))}
      </div>

      {/* Task List - compact HUD entries */}
      <div className="flex flex-col gap-1.5 mt-1 w-full max-w-full min-w-0">
        {tasks.slice(0, 10).map((task, i) => {
          const cfg = STATUS_CONFIG[task.status] || STATUS_CONFIG.pending;
          return (
            <motion.div
              key={task.id}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04, duration: 0.25 }}
            className="group relative pl-3 pr-2 py-1.5 rounded-md bg-charcoal-blue-800/25 overflow-hidden w-full max-w-full min-w-0
                border border-charcoal-blue-700/20 hover:border-sky-reflection-700/30 transition-all"
            >
              {/* Left status bar */}
              <div
                className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full"
                style={{ backgroundColor: cfg.color, opacity: 0.7 }}
              />

              <div className="flex items-center justify-between gap-2 min-w-0">
                <span
                  className={`text-xs truncate min-w-0 flex-1 ${
                    task.status === "completed"
                      ? "line-through text-slate-600"
                      : "text-slate-300"
                  }`}
                >
                  {task.title}
                </span>

                {/* Priority bars */}
                <div className="flex gap-px shrink-0">
                  {Array.from({ length: Math.min(task.priority, 5) }).map(
                    (_, j) => (
                      <div
                        key={j}
                        className="w-[3px] h-2.5 rounded-sm"
                        style={{
                          backgroundColor:
                            task.priority >= 5
                              ? "#ef4444"
                              : task.priority >= 3
                                ? "#f5a30a"
                                : "#475569",
                          opacity: 0.5 + j * 0.12,
                        }}
                      />
                    )
                  )}
                </div>
              </div>

              {/* Animated progress bar for in-progress */}
              {task.status === "in_progress" && (
                <div className="mt-1 h-[2px] bg-charcoal-blue-800/60 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: cfg.color }}
                    animate={{
                      width: ["10%", "65%", "35%", "80%", "50%", "10%"],
                    }}
                    transition={{
                      duration: 5,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  />
                </div>
              )}
            </motion.div>
          );
        })}

        {tasks.length > 10 && (
          <div className="text-center text-[10px] text-slate-600 font-mono py-1 tracking-wider">
            +{tasks.length - 10} MORE
          </div>
        )}
      </div>

      {/* Empty state */}
      {tasks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 gap-3 opacity-40">
          <div className="relative w-16 h-16">
            <motion.div
              className="absolute inset-0 rounded-full border border-dashed border-charcoal-blue-700"
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-charcoal-blue-600" />
            </div>
          </div>
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-600">
            No active protocols
          </span>
        </div>
      )}
    </div>
  );
}
