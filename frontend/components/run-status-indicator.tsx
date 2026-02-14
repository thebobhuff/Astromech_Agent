"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import {
  Loader2,
  Square,
  Wrench,
  Brain,
  Zap,
  MessageSquarePlus,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type RunStatus = {
  status: "running" | "completed" | "aborted" | "timed_out" | "idle";
  session_id: string;
  current_turn?: number;
  max_turns?: number;
  started_at?: string;
  cancel_reason?: string;
};

interface RunStatusIndicatorProps {
  sessionId?: string;
  /** Whether a chat request is currently in flight */
  isLoading: boolean;
  /** Called when the user aborts the run */
  onAbort?: () => void;
}

export default function RunStatusIndicator({
  sessionId = "default",
  isLoading,
  onAbort,
}: RunStatusIndicatorProps) {
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [steerInput, setSteerInput] = useState("");
  const [showSteer, setShowSteer] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isActive = runStatus?.status === "running";

  // Poll run status while loading or run is active
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/agent/runs/${sessionId}/status`, {
        cache: "no-store",
      });
      if (res.ok) {
        const data: RunStatus = await res.json();
        setRunStatus(data);
      }
    } catch {
      // Silently ignore polling errors
    }
  }, [sessionId]);

  useEffect(() => {
    // Start polling when loading begins
    if (isLoading || isActive) {
      fetchStatus();
      pollRef.current = setInterval(fetchStatus, 1000);
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [isLoading, isActive, fetchStatus]);

  // Elapsed time counter
  useEffect(() => {
    if (isActive && runStatus?.started_at) {
      const startTime = new Date(runStatus.started_at).getTime();
      const tick = () => {
        setElapsed(Math.floor((Date.now() - startTime) / 1000));
      };
      tick();
      timerRef.current = setInterval(tick, 1000);
    } else {
      setElapsed(0);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isActive, runStatus?.started_at]);

  // Clear stale status once run completes and loading finishes
  useEffect(() => {
    if (!isLoading && !isActive) {
      const timeout = setTimeout(() => setRunStatus(null), 2000);
      return () => clearTimeout(timeout);
    }
  }, [isLoading, isActive]);

  const handleAbort = async () => {
    try {
      await fetch(`/api/v1/agent/runs/${sessionId}/abort`, {
        method: "POST",
      });
      onAbort?.();
    } catch (e) {
      console.error("Failed to abort run:", e);
    }
  };

  const handleSteer = async () => {
    if (!steerInput.trim()) return;
    try {
      await fetch(`/api/v1/agent/runs/${sessionId}/steer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: steerInput }),
      });
      setSteerInput("");
      setShowSteer(false);
    } catch (e) {
      console.error("Failed to steer run:", e);
    }
  };

  const formatElapsed = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  // Don't render anything if idle and not loading
  if (!isLoading && !isActive) return null;

  const turn = runStatus?.current_turn ?? 0;
  const maxTurns = runStatus?.max_turns ?? 30;
  const progress = maxTurns > 0 ? (turn / maxTurns) * 100 : 0;

  // Determine the phase label
  const getPhaseLabel = () => {
    if (!isActive && isLoading) return "Connecting...";
    if (turn === 0) return "Evaluating prompt...";
    if (turn <= 2) return "Routing & planning...";
    return "Executing tools...";
  };

  const getPhaseIcon = () => {
    if (!isActive && isLoading)
      return <Loader2 className="w-4 h-4 animate-spin text-sky-400" />;
    if (turn === 0)
      return <Brain className="w-4 h-4 text-violet-400 animate-pulse" />;
    if (turn <= 2)
      return <Zap className="w-4 h-4 text-amber-400 animate-pulse" />;
    return <Wrench className="w-4 h-4 text-sky-400 animate-spin" />;
  };

  return (
    <div className="flex justify-start">
      <div className="bg-charcoal-blue-900 border border-charcoal-blue-800 rounded-lg p-4 max-w-[80%] w-full sm:w-auto sm:min-w-[340px] shadow-xl">
        {/* Main status row */}
        <div className="flex items-center gap-3">
          {getPhaseIcon()}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-slate-200 truncate">
                {getPhaseLabel()}
              </span>
              <span className="text-xs text-slate-500 tabular-nums shrink-0">
                {formatElapsed(elapsed)}
              </span>
            </div>

            {/* Progress bar */}
            {isActive && (
              <div className="mt-2">
                <div className="h-1.5 bg-charcoal-blue-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out bg-gradient-to-r from-sky-500 to-baltic-blue-500"
                    style={{ width: `${Math.max(progress, 3)}%` }}
                  />
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                    Turn {turn}/{maxTurns}
                  </span>
                  <span className="text-[10px] text-slate-600">
                    {Math.round(progress)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Action buttons */}
        {isActive && (
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-charcoal-blue-800">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 text-red-400 hover:text-red-300 hover:bg-red-950/30"
                    onClick={handleAbort}
                  >
                    <Square className="w-3 h-3 mr-1.5" />
                    <span className="text-xs">Stop</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="bg-charcoal-blue-800 text-slate-200 border-charcoal-blue-700">
                  Cancel the current run
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 text-sky-400 hover:text-sky-300 hover:bg-sky-950/30"
                    onClick={() => setShowSteer(!showSteer)}
                  >
                    <MessageSquarePlus className="w-3 h-3 mr-1.5" />
                    <span className="text-xs">Steer</span>
                    {showSteer ? (
                      <ChevronUp className="w-3 h-3 ml-1" />
                    ) : (
                      <ChevronDown className="w-3 h-3 ml-1" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="bg-charcoal-blue-800 text-slate-200 border-charcoal-blue-700">
                  Send a course-correction to the running agent
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}

        {/* Steer input */}
        {showSteer && isActive && (
          <div className="mt-2 flex gap-2">
            <input
              type="text"
              value={steerInput}
              onChange={(e) => setSteerInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSteer();
              }}
              placeholder="Redirect the agent..."
              className="flex-1 text-xs bg-charcoal-blue-950 border border-charcoal-blue-700 rounded px-2 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-sky-800"
            />
            <Button
              size="sm"
              className="h-7 px-2 bg-sky-700 hover:bg-sky-600 text-xs"
              onClick={handleSteer}
            >
              Send
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
