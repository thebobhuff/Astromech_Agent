"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, X } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

const MAX_LOG_ENTRIES = 30;
const MAX_LOG_CHARS_PER_ENTRY = 2000;
const MAX_LOG_CHARS_TOTAL = 250000;
const RECONNECT_DELAY_MS = 3000;

function truncateLogEntry(entry: string): string {
  if (entry.length <= MAX_LOG_CHARS_PER_ENTRY) {
    return entry;
  }
  return `${entry.slice(0, MAX_LOG_CHARS_PER_ENTRY)} ... [truncated]`;
}

function pruneLogBuffer(logs: string[]): string[] {
  if (logs.length > MAX_LOG_ENTRIES) {
    logs = logs.slice(-MAX_LOG_ENTRIES);
  }

  let totalChars = 0;
  for (let i = logs.length - 1; i >= 0; i -= 1) {
    totalChars += logs[i].length;
    if (totalChars > MAX_LOG_CHARS_TOTAL) {
      return logs.slice(i + 1);
    }
  }

  return logs;
}

export default function LogViewer({ onClose, className }: { onClose?: () => void, className?: string }) {
  const [logs, setLogs] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const isUnmounting = useRef(false);

  function connect() {
    if (isUnmounting.current) return;
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) return;

    // Determine WebSocket URL
    let wsUrl = "";
    if (typeof window !== "undefined") {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        
        // Development fallback: If on localhost:24680, hit backend port 13579 directly.
        if (window.location.hostname === "localhost" && window.location.port === "24680") {
             wsUrl = "ws://127.0.0.1:13579/api/v1/system/logs";
        } else {
             // Production/Proxied: Use relative path (upgraded to WS)
             wsUrl = `${protocol}//${window.location.host}/api/v1/system/logs`;
        }
    }

    if (!wsUrl) return;

    // console.log("Connecting to logs at:", wsUrl);
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setIsConnected(true);
      setLogs((prev) => pruneLogBuffer([...prev, `>>> Connection established to ${wsUrl}`]));
    };

    ws.onmessage = (event) => {
      setLogs((prev) => pruneLogBuffer([...prev, truncateLogEntry(String(event.data))]));
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      if (!isUnmounting.current) {
         setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = (err) => {
      console.warn("WS Error (Backend likely offline or restarting). Retrying...", err);
      // Do not manually close here, let browser handle it or it will trigger onclose naturally
    };

    wsRef.current = ws;
  }

  useEffect(() => {
    isUnmounting.current = false;
    connect();
    return () => {
      isUnmounting.current = true;
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
        // Find the viewport provided by ScrollArea to scroll it
        const viewport = scrollRef.current.closest('[data-slot="scroll-area-viewport"]') as HTMLElement;
        if (viewport) {
             viewport.scrollTop = viewport.scrollHeight;
        } else {
             scrollRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
        }
    }
  }, [logs]);

  return (
    <div className={`flex flex-col bg-black font-mono text-xs md:text-sm border-t border-charcoal-blue-800 shadow-2xl ${className || ""}`}>
      <div className="flex items-center justify-between px-4 py-2 bg-charcoal-blue-900 border-b border-charcoal-blue-800 shrink-0">
        <div className="flex items-center gap-2 text-slate-300">
          <Terminal className="w-4 h-4" />
          <span className="font-semibold">Live Backend Logs</span>
          <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
        </div>
        <div className="flex items-center gap-1">
             <Button variant="ghost" size="sm" className="h-6 text-slate-400 hover:text-white" onClick={() => setLogs([])}>
                Clear
             </Button>
             {onClose && (
                <Button variant="ghost" size="icon" className="h-6 w-6 text-slate-400 hover:text-white" onClick={onClose}>
                    <X className="w-4 h-4" />
                </Button>
             )}
        </div>
      </div>
      <ScrollArea className="flex-1 bg-[#0c0c0c] text-green-400 p-4 h-full">
        <div className="space-y-1">
          {logs.map((log, i) => (
            <div key={i} className="break-all whitespace-pre-wrap font-mono leading-tight">
              {log}
            </div>
          ))}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
