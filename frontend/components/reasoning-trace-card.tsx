"use client";

import { useMemo, useState } from "react";

export type TraceEvent = {
  ts: string;
  kind: "phase" | "intent" | "tool_start" | "tool_done" | "recovery" | "error";
  text: string;
};

type ReasoningTraceCardProps = {
  events: TraceEvent[];
};

const KIND_LABEL: Record<TraceEvent["kind"], string> = {
  phase: "Phase",
  intent: "Intent",
  tool_start: "Tool Start",
  tool_done: "Tool Done",
  recovery: "Recovery",
  error: "Error",
};

export default function ReasoningTraceCard({ events }: ReasoningTraceCardProps) {
  const [expanded, setExpanded] = useState(false);

  const visibleEvents = useMemo(() => {
    if (expanded) return events;
    return events.slice(-3);
  }, [events, expanded]);

  if (!events || events.length === 0) return null;

  return (
    <div className="mt-2 rounded-md border border-charcoal-blue-700/60 bg-charcoal-blue-900/40 p-2">
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wide text-slate-400">
          Reasoning Trace
        </span>
        <button
          type="button"
          className="text-[11px] text-sky-reflection-300 hover:text-sky-reflection-200"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Collapse" : "Expand"} {events.length} events
        </button>
      </div>

      <div className="mt-2 space-y-1">
        {visibleEvents.map((event, idx) => (
          <div key={`${event.ts}-${idx}`} className="text-[11px] text-slate-300">
            <span className="text-slate-500">[{event.ts}]</span>{" "}
            <span className="text-slate-400">{KIND_LABEL[event.kind]}:</span>{" "}
            <span>{event.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
