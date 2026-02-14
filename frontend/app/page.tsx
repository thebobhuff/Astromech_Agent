"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import OnboardingWizard from "@/components/onboarding-wizard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { FeatureInfoIcon } from "@/components/feature-info-icon";
import { 
  Cpu, HardDrive, Terminal, ListTodo, Plus, 
  CheckCircle2, Clock, AlertCircle, RefreshCw, Play,
  PanelLeft, PanelRight, X, CalendarClock, Pencil, Trash2, UserRound, Bot, Paperclip
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Vortex } from "@/components/ui/vortex";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import LogViewer from "@/components/log-viewer";
import RunStatusIndicator from "@/components/run-status-indicator";
import MemoryMesh from "@/components/memory-mesh";
import RelationshipMemoryPanel from "@/components/relationship-memory-panel";
import ProtocolHUD from "@/components/protocol-hud";
import ReasoningTraceCard, { TraceEvent } from "@/components/reasoning-trace-card";

type Message = {
  role: "user" | "assistant";
  content: string;
  metadata?: {
    intent?: string;
    tools_used?: string[];
    trace_events?: TraceEvent[];
    [key: string]: unknown;
  };
};

type UploadedChatFile = {
  filename: string;
  original_filename: string;
  path: string;
  size: number;
  mime_type: string;
  pinned_to_context: boolean;
  uploaded_at: string;
};

type AgentTask = {
  id: string;
  title: string;
  description: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  priority: number;
  created_at: string;
  updated_at?: string;
  result?: string;
};

type TaskHistory = {
  cron_runs: AgentTask[];
  heartbeat_completed: AgentTask[];
};

type ScheduledJob = {
  id: string;
  name: string;
  cron_expression: string;
  task_prompt: string;
  enabled: boolean;
  next_run_at?: string | null;
};

const formatCountdown = (totalSeconds: number) => {
  const safeSeconds = Math.max(0, totalSeconds);
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
};

type Memory = {
  path: string;
  content: string;
  memory_type: "long-term" | "short-term" | "core";
};

const normalizeMemoryType = (value: unknown): Memory["memory_type"] => {
  if (value === "core" || value === "short-term" || value === "long-term") {
    return value;
  }
  return "long-term";
};

const normalizeMemoriesPayload = (payload: unknown): Memory[] => {
  if (!payload || typeof payload !== "object") return [];

  const source = (payload as { memories?: unknown }).memories ?? payload;

  if (Array.isArray(source)) {
    return source
      .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
      .map((item) => ({
        path: String(item.path ?? ""),
        content: String(item.content ?? ""),
        memory_type: normalizeMemoryType(item.memory_type ?? item.type),
      }))
      .filter((item) => item.path.length > 0);
  }

  if (source && typeof source === "object") {
    return Object.entries(source as Record<string, unknown>)
      .map(([path, value]) => {
        const memory = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
        return {
          path,
          content: String(memory.content ?? ""),
          memory_type: normalizeMemoryType(memory.memory_type ?? memory.type),
        };
      })
      .filter((item) => item.path.length > 0);
  }

  return [];
};

const markdownSanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...(defaultSchema.attributes || {}),
    a: [...((defaultSchema.attributes?.a as string[]) || []), "target", "rel"],
  },
};

const hasMarkdownSyntax = (value: string): boolean => {
  return /[#*_`>\[\]\(\)|~-]|^\d+\./m.test(value);
};

export default function Dashboard() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [relationshipRefreshToken, setRelationshipRefreshToken] = useState(0);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [history, setHistory] = useState<TaskHistory>({ cron_runs: [], heartbeat_completed: [] });
  const [cronJobs, setCronJobs] = useState<ScheduledJob[]>([]);
  const [nextHeartbeatTasks, setNextHeartbeatTasks] = useState<AgentTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [heartbeatRunning, setHeartbeatRunning] = useState(false);
  const [nextHeartbeatAt, setNextHeartbeatAt] = useState<number | null>(null);
  const [heartbeatCountdown, setHeartbeatCountdown] = useState("--:--");
  const [sessionId, setSessionId] = useState(() => `web_${Date.now().toString(36)}`);
  
  // App State
  const [isChecking, setIsChecking] = useState(true);
  const [isConfigured, setIsConfigured] = useState(true);
  const [isTaskDialogOpen, setIsTaskDialogOpen] = useState(false);
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('queue');
  
  // New Task Form
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskDesc, setNewTaskDesc] = useState("");
  const [newTaskPriority, setNewTaskPriority] = useState("3");
  const [isCronDialogOpen, setIsCronDialogOpen] = useState(false);
  const [editingCronJobId, setEditingCronJobId] = useState<string | null>(null);
  const [cronName, setCronName] = useState("");
  const [cronExpression, setCronExpression] = useState("");
  const [cronPrompt, setCronPrompt] = useState("");
  const [cronEnabled, setCronEnabled] = useState(true);
  const [runningCronJobId, setRunningCronJobId] = useState<string | null>(null);

  const [mobileMenuOpen, setMobileMenuOpen] = useState<'none' | 'left' | 'right'>('none');
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [isDraggingFiles, setIsDraggingFiles] = useState(false);
  const vortexPalette = useMemo(
    () => [
      "hsl(198 57% 50%)",
      "hsl(201 52% 58%)",
      "hsl(40 92% 50%)",
      "hsl(43 92% 60%)",
    ],
    []
  );
  const chatInputPlaceholders = useMemo(
    () => [
      "Command the Astromech...",
      "Ask for a system check...",
      "Describe the protocol you want to run...",
      "Drop files, then ask for analysis...",
    ],
    []
  );

  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Robust scroll-to-bottom for Radix ScrollArea
    const scrollToBottom = () => {
      if (bottomRef.current) {
        // Try finding the verify scrollable viewport from Radix 
        const viewport = bottomRef.current.closest('[data-slot="scroll-area-viewport"]') as HTMLElement;
        
        if (viewport) {
          // Direct scroll manipulation is often more reliable than scrollIntoView for custom scroll containers
          const isNearBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 100;
          
          // Force scroll if loading or new message, otherwise only if near bottom
          // Actually for a chat app, we almost always want to force scroll on new messages
          viewport.scrollTo({ 
            top: viewport.scrollHeight, 
            behavior: 'smooth' 
          });
        } else {
          // Fallback
          bottomRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
        }
      }
    };

    // Immediate scroll (for instant feedback)
    scrollToBottom();

    // Delayed scroll (for layout settlement, images, etc)
    const timeout = setTimeout(scrollToBottom, 100);
    
    return () => clearTimeout(timeout);
  }, [messages, loading]);

  useEffect(() => {
    const init = async () => {
      const configured = await checkConfiguration();
      if (configured) {
        await Promise.all([
          fetchMemories(),
          fetchTasks(),
          fetchHeartbeatStatus(),
          fetchTaskHistory(),
          fetchCronJobs(),
          fetchNextHeartbeatTasks(),
        ]);
      }
    };
    init();
  }, []);

  useEffect(() => {
    if (isChecking || !isConfigured) return;

    // FE-013: make queue/active jobs feel real-time while preserving lighter polling on History.
    const fastMode = activeTab === "queue";
    const intervalMs = fastMode ? 1000 : 5000;

    const poll = () => {
      fetchTasks(1, 0);
      fetchHeartbeatStatus();
      if (fastMode) {
        fetchCronJobs();
        fetchNextHeartbeatTasks();
      } else {
        fetchTaskHistory();
      }
    };

    poll();
    const interval = setInterval(poll, intervalMs);
    return () => clearInterval(interval);
  }, [activeTab, isChecking, isConfigured]);

  useEffect(() => {
    const tick = () => {
      if (!heartbeatRunning || !nextHeartbeatAt) {
        setHeartbeatCountdown("--:--");
        return;
      }

      const remainingSeconds = Math.ceil((nextHeartbeatAt - Date.now()) / 1000);
      setHeartbeatCountdown(formatCountdown(remainingSeconds));
    };

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [heartbeatRunning, nextHeartbeatAt]);

  const checkConfiguration = async (retries = 5, delay = 1000): Promise<boolean> => {
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const res = await fetch("/api/v1/system/status", { cache: "no-store" });
        if (!res.ok) {
          // In dev, Next rewrite returns 500 when backend is down/unreachable.
          // Treat as transient connectivity issue and retry without noisy throw.
          if (attempt < retries - 1) {
            await new Promise((r) => setTimeout(r, delay));
            continue;
          }
          setIsChecking(false);
          setIsConnected(false);
          return false;
        }
        const data = await res.json();
        // If needs_onboarding is true, isConfigured is false
        setIsConfigured(!data.needs_onboarding);
        setIsChecking(false);
        setIsConnected(true);
        return !data.needs_onboarding;
      } catch (e) {
        if (attempt < retries - 1) {
          await new Promise((r) => setTimeout(r, delay));
        } else {
          console.warn("Failed to reach backend status endpoint after retries", e);
          setIsChecking(false);
          setIsConnected(false);
        }
      }
    }
    return false;
  };

  const fetchMemories = async (retries = 3, delay = 1000) => {
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const res = await fetch("/api/v1/memory/all", { cache: "no-store" });
        if (!res.ok) {
           throw new Error(await res.text());
        }
        const data = await res.json();
        setMemories(normalizeMemoriesPayload(data));
        setIsConnected(true);
        return;
      } catch (e) {
        if (attempt < retries - 1) {
          await new Promise((r) => setTimeout(r, delay));
        } else {
          if (retries > 1) {
             console.warn("Failed to fetch memories", e);
          }
          setIsConnected(false);
        }
      }
    }
  };

  const getMemoryTypeColor = (type: Memory['memory_type']) => {
    switch (type) {
      case "long-term": return "bg-yellow-600/20 text-yellow-300";
      case "short-term": return "bg-teal-600/20 text-teal-300";
      case "core": return "bg-purple-600/20 text-purple-300";
      default: return "bg-slate-600/20 text-slate-300";
    }
  };

  const handleEditMemory = async (memory: Memory) => {
    const newContent = prompt("Edit memory content:", memory.content);
    if (newContent === null) return; // User cancelled

    try {
      const res = await fetch("/api/v1/memory/", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: memory.path, content: newContent, memory_type: memory.memory_type }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      fetchMemories(); // Refresh memories after edit
    } catch (e) {
      console.error("Failed to edit memory", e);
      alert("Failed to edit memory: " + e);
    }
  };

  const handleDeleteMemory = async (memory: Memory) => {
    const confirmed = window.confirm(`Are you sure you want to delete memory: ${memory.path}?`);
    if (!confirmed) return;

    try {
      const res = await fetch(`/api/v1/memory/?path=${encodeURIComponent(memory.path)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      fetchMemories(); // Refresh memories after delete
    } catch (e) {
      console.error("Failed to delete memory", e);
      alert("Failed to delete memory: " + e);
    }
  };

  const fetchTasks = async (retries = 3, delay = 1000) => {
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const res = await fetch("/api/v1/tasks/", { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json();
        const sorted = data.sort((a: AgentTask, b: AgentTask) => {
          const scoreA = getStatusScore(a.status) + (a.priority * 10);
          const scoreB = getStatusScore(b.status) + (b.priority * 10);
          return scoreB - scoreA;
        });
        setTasks(sorted);
        setIsConnected(true);
        return;
      } catch (e) {
        if (attempt < retries - 1) {
          await new Promise((r) => setTimeout(r, delay));
        } else {
          // Suppress error if we are just polling (retries=1 means polling usually)
          if (retries > 1) {
             console.warn("Failed to fetch tasks", e);
          }
          setIsConnected(false);
        }
      }
    }
  };

  const fetchHeartbeatStatus = async () => {
    try {
      const res = await fetch("/api/v1/system/heartbeat/status", { cache: "no-store" });
      if (!res.ok) return;
      const data = await res.json();
      setHeartbeatRunning(Boolean(data.running));
      setNextHeartbeatAt(data.next_tick_at ? Math.floor(data.next_tick_at * 1000) : null);
    } catch (e) {
      console.warn("Failed to fetch heartbeat status", e);
      setHeartbeatRunning(false);
      setNextHeartbeatAt(null);
    }
  };

  const fetchTaskHistory = async () => {
    try {
      const res = await fetch("/api/v1/tasks/history", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setHistory({
          cron_runs: data.cron_runs || [],
          heartbeat_completed: data.heartbeat_completed || [],
        });
      }
    } catch (e) {
      console.warn("Failed to fetch task history", e);
    }
  };

  const fetchCronJobs = async () => {
    try {
      const res = await fetch("/api/v1/tasks/cron", { cache: "no-store" });
      if (!res.ok) return;
      const data = await res.json();
      const jobs = Array.isArray(data) ? data : [];
      const deduped = jobs.filter((job, index, arr) => {
        const fingerprint = `${String(job.name || "").trim()}||${String(job.cron_expression || "").replace(/\s+/g, " ").trim()}`;
        return (
          arr.findIndex((other) => {
            const otherFp = `${String(other.name || "").trim()}||${String(other.cron_expression || "").replace(/\s+/g, " ").trim()}`;
            return otherFp === fingerprint;
          }) === index
        );
      });
      setCronJobs(deduped);
    } catch (e) {
      console.warn("Failed to fetch cron jobs", e);
    }
  };

  const fetchNextHeartbeatTasks = async () => {
    try {
      const res = await fetch("/api/v1/tasks/next-heartbeat-tasks?limit=10", { cache: "no-store" });
      if (!res.ok) return;
      const data = await res.json();
      setNextHeartbeatTasks(Array.isArray(data) ? data : []);
    } catch (e) {
      console.warn("Failed to fetch next heartbeat tasks", e);
    }
  };

  const getStatusScore = (status: string) => {
    switch (status) {
      case 'in_progress': return 1000;
      case 'pending': return 500;
      case 'completed': return -100;
      case 'failed': return -200;
      default: return 0;
    }
  };

  const handleCreateTask = async () => {
    if (!newTaskTitle) return;
    try {
      await fetch("/api/v1/tasks/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newTaskTitle,
          description: newTaskDesc,
          priority: parseInt(newTaskPriority)
        })
      });
      fetchTasks();
      setIsTaskDialogOpen(false);
      setNewTaskTitle("");
      setNewTaskDesc("");
      setNewTaskPriority("3");
    } catch (e) {
      console.error("Failed to create task", e);
    }
  };

  const openCronEditDialog = (job: ScheduledJob) => {
    setEditingCronJobId(job.id);
    setCronName(job.name);
    setCronExpression(job.cron_expression);
    setCronPrompt(job.task_prompt);
    setCronEnabled(job.enabled);
    setIsCronDialogOpen(true);
  };

  const handleSaveCronJob = async () => {
    if (!editingCronJobId || !cronName.trim() || !cronExpression.trim() || !cronPrompt.trim()) return;
    try {
      const res = await fetch(`/api/v1/tasks/cron/${editingCronJobId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: cronName.trim(),
          cron_expression: cronExpression.trim(),
          task_prompt: cronPrompt.trim(),
          enabled: cronEnabled,
        }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      closeCronDialog();
      await fetchCronJobs();
    } catch (e) {
      console.error("Failed to update cron job", e);
    }
  };

  const handleDeleteCronJob = async (job: ScheduledJob) => {
    const confirmed = window.confirm(`Delete scheduled cron job "${job.name}"?`);
    if (!confirmed) return;
    try {
      const res = await fetch(`/api/v1/tasks/cron/${job.id}`, { method: "DELETE" });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      await fetchCronJobs();
    } catch (e) {
      console.error("Failed to delete cron job", e);
    }
  };

  const handleRunCronJobNow = async (job: ScheduledJob) => {
    const confirmed = window.confirm(`Run scheduled cron job "${job.name}" now?`);
    if (!confirmed) return;

    setRunningCronJobId(job.id);
    try {
      const res = await fetch(`/api/v1/tasks/cron/${job.id}/run-now`, { method: "POST" });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const data = await res.json();
      if (data.status === "skipped_active") {
        alert(`"${job.name}" is already queued/running.`);
      }
      await Promise.all([fetchTasks(), fetchNextHeartbeatTasks(), fetchTaskHistory()]);
    } catch (e) {
      console.error("Failed to run cron job now", e);
      alert(`Failed to run "${job.name}" now.`);
    } finally {
      setRunningCronJobId(null);
    }
  };

  const closeCronDialog = () => {
    setIsCronDialogOpen(false);
    setEditingCronJobId(null);
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const appendPendingFiles = (incoming: FileList | File[]) => {
    const nextFiles = Array.from(incoming);
    if (!nextFiles.length) return;

    setPendingFiles((prev) => {
      const seen = new Set(prev.map((f) => `${f.name}:${f.size}:${f.lastModified}`));
      const merged = [...prev];
      for (const file of nextFiles) {
        const key = `${file.name}:${file.size}:${file.lastModified}`;
        if (!seen.has(key)) {
          seen.add(key);
          merged.push(file);
        }
      }
      return merged;
    });
  };

  const removePendingFile = (idx: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const uploadFilesForSession = async (files: File[]): Promise<UploadedChatFile[]> => {
    const uploaded: UploadedChatFile[] = [];

    for (const file of files) {
      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("pin_to_context", "true");
      formData.append("file", file);

      const res = await fetch("/api/v1/agent/uploads", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      uploaded.push((await res.json()) as UploadedChatFile);
    }

    return uploaded;
  };

  const sendMessage = async () => {
    if (!input.trim() && pendingFiles.length === 0) return;

    const filesToUpload = [...pendingFiles];
    const basePrompt = input.trim() || "I uploaded files. Please inspect them and summarize what matters.";
    const uploadedListText = filesToUpload.length
      ? `\n\n[Attached files: ${filesToUpload.map((f) => f.name).join(", ")}]`
      : "";
    const userMsg: Message = { role: "user", content: `${basePrompt}${uploadedListText}` };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setPendingFiles([]);
    setIsDraggingFiles(false);
    setLoading(true);

    // We'll build a placeholder assistant message that gets updated as SSE events arrive
    const placeholderMsg: Message = { role: "assistant", content: "", metadata: undefined };
    setMessages((prev) => [...prev, placeholderMsg]);
    const msgIndex = messages.length + 1; // +1 because we already pushed userMsg

    try {
      let uploadedFiles: UploadedChatFile[] = [];
      if (filesToUpload.length > 0) {
        setMessages((prev) => {
          const updated = [...prev];
          if (updated[msgIndex]) {
            updated[msgIndex] = { ...updated[msgIndex], content: `⏳ Uploading ${filesToUpload.length} file(s)...` };
          }
          return updated;
        });
        uploadedFiles = await uploadFilesForSession(filesToUpload);
      }

      const imagePaths = uploadedFiles
        .filter((f) => f.mime_type.startsWith("image/"))
        .map((f) => f.path);
      const promptWithUploadContext = uploadedFiles.length
        ? `${basePrompt}\n\n[SYSTEM: User uploaded files already pinned to context: ${uploadedFiles.map((f) => f.original_filename).join(", ")}]`
        : basePrompt;

      const res = await fetch("/api/v1/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: promptWithUploadContext,
          session_id: sessionId,
          images: imagePaths.length ? imagePaths : undefined,
        }),
      });
      
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`API Error ${res.status}: ${errText}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";
      let finalResponse = "";
      let finalMetadata: Message["metadata"] | undefined = undefined;
      const traceEvents: TraceEvent[] = [];
      let streamedResponse = "";
      let sawResponseChunk = false;

      const pushTrace = (kind: TraceEvent["kind"], text: string) => {
        const stamp = new Date().toLocaleTimeString([], { hour12: false });
        traceEvents.push({ ts: stamp, kind, text });
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE frames from the buffer
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        let currentEvent = "";
        let currentData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            currentData = line.slice(6);
          } else if (line === "" && currentEvent && currentData) {
            // Process complete SSE frame
            try {
              const data = JSON.parse(currentData);

              if (currentEvent === "phase") {
                const phaseText = String(data.message || data.phase || "phase");
                const phaseKind: TraceEvent["kind"] = String(data.phase || "").toLowerCase() === "recovery" ? "recovery" : "phase";
                pushTrace(phaseKind, phaseText);
                setMessages((prev) => {
                  const updated = [...prev];
                  if (updated[msgIndex]) {
                    updated[msgIndex] = { ...updated[msgIndex], content: `⏳ ${phaseText}` };
                  }
                  return updated;
                });
              } else if (currentEvent === "intent") {
                pushTrace("intent", `Intent: ${String(data.intent || "")}`);
              } else if (currentEvent === "tool_start") {
                const toolList = (data.tools as string[])?.join(", ") || "tools";
                const statusLine = `🔧 Running: ${toolList} (turn ${data.turn})`;
                pushTrace("tool_start", statusLine);
                setMessages((prev) => {
                  const updated = [...prev];
                  if (updated[msgIndex]) {
                    updated[msgIndex] = { ...updated[msgIndex], content: statusLine };
                  }
                  return updated;
                });
              } else if (currentEvent === "tool_done") {
                const results = Array.isArray(data.results) ? data.results : [];
                const toolNames = results
                  .map((r: unknown) => (r && typeof r === "object" && "tool" in r ? String((r as { tool: unknown }).tool) : "tool"))
                  .join(", ") || "tools";
                const statusLine = `✅ Completed: ${toolNames} (turn ${data.turn})`;
                pushTrace("tool_done", statusLine);
                setMessages((prev) => {
                  const updated = [...prev];
                  if (updated[msgIndex]) {
                    updated[msgIndex] = { ...updated[msgIndex], content: statusLine };
                  }
                  return updated;
                });
              } else if (currentEvent === "response_chunk") {
                const chunk = String(data.text || "");
                if (chunk) {
                  sawResponseChunk = true;
                  streamedResponse += chunk;
                  setMessages((prev) => {
                    const updated = [...prev];
                    if (updated[msgIndex]) {
                      updated[msgIndex] = { ...updated[msgIndex], content: streamedResponse };
                    }
                    return updated;
                  });
                }
              } else if (currentEvent === "complete") {
                finalResponse = sawResponseChunk ? streamedResponse : (data.response || "");
                finalMetadata = data.metadata;
              } else if (currentEvent === "error") {
                finalResponse = `Error: ${data.message || "Unknown error"}`;
                pushTrace("error", finalResponse);
              }
            } catch {
              // Ignore malformed JSON
            }
            currentEvent = "";
            currentData = "";
          }
        }
      }

      // Replace placeholder with final response
      const aiMsg: Message = { 
        role: "assistant", 
        content: finalResponse || "No response received.",
        metadata: {
          ...(finalMetadata || {}),
          trace_events: traceEvents,
        },
      };
      setMessages((prev) => {
        const updated = [...prev];
        updated[msgIndex] = aiMsg;
        return updated;
      });

      // Refresh memories and tasks as the agent might have updated them
      fetchMemories();
      fetchTasks();
      setRelationshipRefreshToken((v) => v + 1);
    } catch (e) {
      console.error("Chat Error:", e);
      setMessages((prev) => {
        const updated = [...prev];
        if (updated[msgIndex]) {
          updated[msgIndex] = { role: "assistant", content: "Error communicating with Astromech core. Check console." };
        } else {
          return [...prev, { role: "assistant", content: "Error communicating with Astromech core. Check console." }];
        }
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'in_progress': return <RefreshCw className="w-4 h-4 text-sky-500 animate-spin" />;
      case 'failed': return <AlertCircle className="w-4 h-4 text-red-500" />;
      default: return <Clock className="w-4 h-4 text-slate-500" />;
    }
  };

  const getPriorityColor = (p: number) => {
    if (p >= 5) return "text-red-400";
    if (p >= 3) return "text-yellow-400";
    return "text-slate-400";
  };

  const activeQueueTasks = useMemo(
    () =>
      tasks.filter((task) => {
        const isScheduled = task.title.startsWith("[Scheduled] ");
        if (isScheduled) {
          // Scheduled jobs should appear in active queue only while actually executing.
          return task.status === "in_progress";
        }
        return task.status === "pending" || task.status === "in_progress";
      }),
    [tasks]
  );

  if (isChecking) {
    return <div className="h-screen bg-charcoal-blue-950 flex items-center justify-center text-sky-reflection-400">Booting System...</div>;
  }

  if (!isConfigured) {
    return <OnboardingWizard onComplete={() => window.location.reload()} />;
  }

  return (
    <div className="flex h-full bg-charcoal-blue-950 text-slate-100 font-sans overflow-hidden">
      {/* Left Sidebar - Memory Banks */}
      <div className={`
        fixed inset-y-0 left-0 z-[60] w-64 bg-charcoal-blue-900 border-r border-charcoal-blue-800/50 p-4 flex flex-col 
        transition-transform duration-300 ease-in-out shadow-2xl md:shadow-none
        hud-border-glow hud-border-glow-right hud-scanline
        ${mobileMenuOpen === 'left' ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        md:static md:flex
      `}>
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div className="flex items-center gap-2 text-sky-reflection-400">
            <HardDrive className="w-5 h-5" />
            <h1 className="font-bold text-sm tracking-[0.2em] uppercase neon-text">Memory Bank</h1>
          </div>
          <div className="flex items-center gap-1">
            <FeatureInfoIcon featureId="FE-001" />
            <Button variant="ghost" size="icon" className="md:hidden h-6 w-6" onClick={() => setMobileMenuOpen('none')}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <MemoryMesh
          memories={memories}
          onEdit={handleEditMemory}
          onDelete={handleDeleteMemory}
          getMemoryTypeColor={getMemoryTypeColor}
        />
        <RelationshipMemoryPanel refreshToken={relationshipRefreshToken} />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-charcoal-blue-950">
        {/* Header */}
        <header className="h-16 border-b border-charcoal-blue-800 flex items-center px-4 md:px-6 bg-charcoal-blue-900/50 backdrop-blur justify-between shrink-0">
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="icon" 
              className="md:hidden text-sky-reflection-400 -ml-2 mr-2"
              onClick={() => setMobileMenuOpen('left')}
            >
              <PanelLeft className="w-6 h-6" />
            </Button>
            
            <div className="flex items-center gap-2 text-sky-reflection-400">
              <Cpu className="w-6 h-6 hidden sm:block" />
              <span className="font-bold text-lg">ASTROMECH CORE</span>
              <FeatureInfoIcon featureId="FE-001" featureName="Command Center" />
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="ml-2 text-slate-400 hover:text-sky-300 hover:bg-charcoal-blue-800"
              onClick={() => {
                setMessages([]);
                setSessionId(`web_${Date.now().toString(36)}`);
              }}
              title="Start a new session"
            >
              <Plus className="w-4 h-4 mr-1" />
              <span className="text-xs hidden sm:inline">New Chat</span>
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-2 mr-4 bg-charcoal-blue-800 px-3 py-1 rounded-full border border-charcoal-blue-700">
               <div className={`w-2 h-2 rounded-full animate-pulse ${isConnected ? "bg-green-500" : "bg-red-500"}`}></div>
               <span className="text-xs text-slate-300 font-medium">{isConnected ? "ONLINE" : "OFFLINE"}</span>
               <Separator orientation="vertical" className="h-3 bg-charcoal-blue-600" />
               <span className="text-xs text-slate-400 font-mono">NEXT HB {heartbeatRunning ? heartbeatCountdown : "--:--"}</span>
            </div>
            
            <Button 
                variant="ghost" 
                size="icon" 
                className={`hidden sm:flex mr-2 ${isLogsOpen ? 'text-green-400 bg-charcoal-blue-800' : 'text-slate-500 hover:text-slate-300'}`}
                onClick={() => setIsLogsOpen(!isLogsOpen)}
                title="Toggle Live Logs"
            >
                <Terminal className="w-5 h-5" />
            </Button>

            <div className="text-slate-500 text-sm mr-2 hidden sm:block">v1.0.0</div>
            <Button 
                variant="ghost" 
                size="icon" 
                className="lg:hidden text-sky-reflection-400"
                onClick={() => setMobileMenuOpen('right')}
            >
                <PanelRight className="w-6 h-6" />
            </Button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 min-h-0">
          <Vortex
            backgroundColor="#0c1317"
            rangeY={820}
            particleCount={480}
            baseHue={206}
            colorPalette={vortexPalette}
            className="h-full w-full"
          >
            <ScrollArea className="h-full">
              <div className="max-w-4xl mx-auto space-y-6 p-6">
                {messages.length === 0 && (
                  <div className="text-center py-20 opacity-50">
                    <Terminal className="w-16 h-16 mx-auto mb-4 text-charcoal-blue-600" />
                    <h2 className="text-xl font-semibold mb-2">Awaiting Input</h2>
                    <p className="text-slate-400">Astromech is ready to assist.</p>
                  </div>
                )}
                
                {messages.map((msg, i) => {
                  const isEmptyPlaceholder =
                    msg.role === "assistant" &&
                    !msg.content.trim() &&
                    !msg.metadata;
                  if (isEmptyPlaceholder) return null;

                  const isUser = msg.role === "user";
                  const isStreamingAssistant = !isUser && loading && i === messages.length - 1;
                  const shouldUseTextEffect =
                    !isUser &&
                    !isStreamingAssistant &&
                    !hasMarkdownSyntax(msg.content);
                  return (
                    <div key={i} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                      <div className={`flex items-end gap-2 max-w-[90%] ${isUser ? "flex-row-reverse" : ""}`}>
                        <div
                          className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center border ${
                            isUser
                              ? "bg-baltic-blue-900/70 border-baltic-blue-700 text-sky-reflection-200"
                              : "bg-charcoal-blue-900 border-charcoal-blue-700 text-slate-300"
                          }`}
                        >
                          {isUser ? <UserRound className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                        </div>

                        <div
                          className={`max-w-[80%] rounded-lg p-4 ${
                            isUser
                              ? "bg-baltic-blue-900/40 border border-baltic-blue-800 text-sky-reflection-100"
                              : "bg-charcoal-blue-900 border border-charcoal-blue-800 text-slate-300 shadow-xl"
                          }`}
                        >
                          {isUser ? (
                            <div className="whitespace-pre-wrap">{msg.content}</div>
                          ) : shouldUseTextEffect ? (
                            <TextGenerateEffect
                              words={msg.content}
                              className="text-sm leading-6 break-words"
                            />
                          ) : (
                            <div className="text-sm leading-6 break-words [&_a]:text-sky-reflection-300 [&_a]:underline [&_a]:underline-offset-2 [&_a:hover]:text-sky-reflection-200 [&_blockquote]:border-l-2 [&_blockquote]:border-charcoal-blue-700 [&_blockquote]:pl-4 [&_blockquote]:italic [&_code]:rounded [&_code]:bg-charcoal-blue-950 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-charcoal-blue-950 [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:list-decimal [&_ol]:pl-6 [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:text-base [&_h2]:font-semibold [&_h3]:font-semibold [&_p]:my-2">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                rehypePlugins={[rehypeRaw, [rehypeSanitize, markdownSanitizeSchema]]}
                                components={{
                                  a: ({ ...props }) => (
                                    <a
                                      {...props}
                                      target="_blank"
                                      rel="noopener noreferrer nofollow"
                                    />
                                  ),
                                }}
                              >
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                          )}

                          {/* Metadata / Thought Process Display */}
                          {msg.metadata && (
                            <div className="mt-3 pt-3 border-t border-charcoal-blue-800/50 text-xs font-mono text-charcoal-blue-400">
                              <div className="flex gap-4">
                                {msg.metadata.intent && <span>Intent: {String(msg.metadata.intent)}</span>}
                                {msg.metadata.tools_used && <span>Tool: {JSON.stringify(msg.metadata.tools_used)}</span>}
                              </div>
                              <ReasoningTraceCard events={msg.metadata.trace_events || []} />
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                
                <RunStatusIndicator isLoading={loading} sessionId={sessionId} />
                <div ref={bottomRef} />
              </div>
            </ScrollArea>
          </Vortex>
        </div>

        {/* Input Area */}
        <div className="p-4 bg-charcoal-blue-900/50 border-t border-charcoal-blue-800 shrink-0 z-10">
          <div className="max-w-4xl mx-auto">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files) {
                  appendPendingFiles(e.target.files);
                }
                e.currentTarget.value = "";
              }}
            />

            <div
              className={`rounded-lg border p-2 transition-colors ${
                isDraggingFiles
                  ? "border-sky-reflection-500 bg-sky-reflection-900/20"
                  : "border-charcoal-blue-700 bg-charcoal-blue-950/60"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDraggingFiles(true);
              }}
              onDragEnter={(e) => {
                e.preventDefault();
                setIsDraggingFiles(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setIsDraggingFiles(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setIsDraggingFiles(false);
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                  appendPendingFiles(e.dataTransfer.files);
                }
              }}
            >
              {pendingFiles.length > 0 && (
                <div className="mb-2 flex flex-wrap gap-2">
                  {pendingFiles.map((file, idx) => (
                    <div
                      key={`${file.name}-${file.size}-${file.lastModified}`}
                      className="flex items-center gap-2 rounded-md border border-charcoal-blue-700 bg-charcoal-blue-900 px-2 py-1 text-xs"
                    >
                      <span className="max-w-56 truncate text-slate-200">{file.name}</span>
                      <span className="text-slate-500">{formatBytes(file.size)}</span>
                      <button
                        type="button"
                        className="text-slate-500 hover:text-red-400"
                        onClick={() => removePendingFile(idx)}
                        aria-label={`Remove ${file.name}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="h-auto border-charcoal-blue-700 bg-charcoal-blue-900 hover:bg-charcoal-blue-800"
                  onClick={() => fileInputRef.current?.click()}
                  title="Attach files"
                >
                  <Paperclip className="w-4 h-4" />
                </Button>
                <PlaceholdersAndVanishInput
                  placeholders={
                    isDraggingFiles
                      ? ["Drop files to upload..."]
                      : chatInputPlaceholders
                  }
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onSubmit={() => {
                    void sendMessage();
                  }}
                  disabled={loading}
                  allowEmptySubmit={pendingFiles.length > 0}
                  className="min-h-[50px] flex-1 border-charcoal-blue-700 bg-charcoal-blue-950"
                />
              </div>
            </div>
          </div>
        </div>
        
        {isLogsOpen && (
           <div className="h-64 shrink-0 border-t border-charcoal-blue-800 transition-all duration-300 ease-in-out">
              <LogViewer onClose={() => setIsLogsOpen(false)} />
           </div>
        )}
      </div>

      {/* Right Sidebar - Task Queue */}
      <div className={`
        fixed inset-y-0 right-0 z-[60] w-[min(22rem,calc(100vw-1rem))] lg:w-[24rem] xl:w-[26rem] shrink-0 min-w-0 max-w-[calc(100vw-1rem)] bg-charcoal-blue-900 border-l border-charcoal-blue-800/50 p-4 flex flex-col overflow-x-hidden
        transition-transform duration-300 ease-in-out shadow-2xl lg:shadow-none
        hud-border-glow hud-border-glow-left hud-scanline
        ${mobileMenuOpen === 'right' ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}
        lg:static lg:flex
      `}>
        <div className="flex items-center justify-between mb-4 text-sky-reflection-400 shrink-0">
          <div className="flex items-center gap-2">
            <ListTodo className="w-5 h-5" />
            <h1 className="font-bold text-sm tracking-[0.2em] uppercase neon-text">Protocols</h1>
            <FeatureInfoIcon featureId="FE-013" featureName="Protocol Queue & History" />
          </div>
          <div className="flex items-center">
             <Button variant="ghost" size="icon" className="lg:hidden mr-1" onClick={() => setMobileMenuOpen('none')}>
              <X className="w-5 h-5" />
            </Button>
            
            {activeTab === 'queue' ? (
                <Dialog open={isTaskDialogOpen} onOpenChange={setIsTaskDialogOpen}>
                    <DialogTrigger asChild>
                    <Button size="icon" variant="ghost" className="h-6 w-6 hover:bg-baltic-blue-800" title="Add One-off Task">
                        <Plus className="w-4 h-4" />
                    </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-charcoal-blue-900 border-charcoal-blue-700 text-slate-100">
                    <DialogHeader>
                        <DialogTitle>Add New Protocol</DialogTitle>
                        <DialogDescription className="text-slate-400">
                        Assign a new background task to the agent.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                        <Label htmlFor="task-title">Title</Label>
                        <Input 
                            id="task-title" 
                            value={newTaskTitle}
                            onChange={(e) => setNewTaskTitle(e.target.value)}
                            className="bg-charcoal-blue-950 border-charcoal-blue-700" 
                        />
                        </div>
                        <div className="grid gap-2">
                        <Label htmlFor="task-priority">Priority</Label>
                        <Select value={newTaskPriority} onValueChange={setNewTaskPriority}>
                            <SelectTrigger className="bg-charcoal-blue-950 border-charcoal-blue-700">
                            <SelectValue placeholder="Select priority" />
                            </SelectTrigger>
                            <SelectContent className="bg-charcoal-blue-900 border-charcoal-blue-700 text-slate-100">
                            <SelectItem value="1">Low</SelectItem>
                            <SelectItem value="3">Medium</SelectItem>
                            <SelectItem value="5">High</SelectItem>
                            </SelectContent>
                        </Select>
                        </div>
                        <div className="grid gap-2">
                        <Label htmlFor="task-desc">Description</Label>
                        <Textarea 
                            id="task-desc" 
                            value={newTaskDesc}
                            onChange={(e) => setNewTaskDesc(e.target.value)}
                            className="bg-charcoal-blue-950 border-charcoal-blue-700" 
                        />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={handleCreateTask} className="bg-baltic-blue-600 hover:bg-baltic-blue-500">Add Protocol</Button>
                    </DialogFooter>
                    </DialogContent>
                </Dialog>
            ) : (
                null
            )}
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col flex-1 min-h-0 min-w-0 max-w-full overflow-x-hidden">
             <TabsList className="grid w-full min-w-0 max-w-full grid-cols-2 bg-charcoal-blue-800 mb-2 border border-charcoal-blue-700">
                <TabsTrigger value="queue" className="min-w-0 truncate data-[state=active]:bg-charcoal-blue-600 data-[state=active]:text-slate-100">Active Queue</TabsTrigger>
                <TabsTrigger value="history" className="min-w-0 truncate data-[state=active]:bg-charcoal-blue-600 data-[state=active]:text-slate-100">History</TabsTrigger>
            </TabsList>

            <TabsContent value="queue" className="flex-1 min-h-0 min-w-0 max-w-full mt-0 data-[state=inactive]:hidden overflow-x-hidden">
                <ScrollArea className="h-full w-full min-w-0 max-w-full overflow-x-hidden">
                  <div className="space-y-5 pb-4 w-full max-w-full min-w-0">
                    <ProtocolHUD tasks={activeQueueTasks} />

                    <div className="space-y-2 min-w-0 max-w-full">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-400 mb-1">
                        Next Heartbeat Tasks
                      </h3>
                      {nextHeartbeatTasks.map((task) => (
                        <div
                          key={task.id}
                          className="w-full max-w-full min-w-0 p-3 bg-charcoal-blue-800/30 rounded-lg border border-charcoal-blue-700/50 overflow-hidden"
                        >
                          <div className="flex items-center justify-between gap-3 min-w-0">
                            <span className="text-sm text-slate-200 truncate min-w-0 flex-1">{task.title}</span>
                            <span className={`text-xs font-mono ${getPriorityColor(task.priority)}`}>P{task.priority}</span>
                          </div>
                          {task.description && (
                            <p className="text-xs text-slate-400 mt-2 line-clamp-2 break-words">{task.description}</p>
                          )}
                        </div>
                      ))}
                      {nextHeartbeatTasks.length === 0 && (
                        <div className="text-center py-4 text-slate-600 text-sm">
                          No pending tasks queued for the next heartbeat.
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-sky-reflection-500 mb-1 flex items-center gap-2 min-w-0 max-w-full">
                        <CalendarClock className="w-3.5 h-3.5" />
                        <span className="truncate">Scheduled Cron Jobs</span>
                      </h3>
                      {cronJobs.map((job) => (
                        <div
                          key={job.id}
                          className="w-full max-w-full min-w-0 p-3 bg-charcoal-blue-800/30 rounded-lg border border-charcoal-blue-700/50 overflow-hidden"
                        >
                          <div className="flex items-center justify-between gap-2 min-w-0">
                            <span className="text-sm text-slate-200 truncate min-w-0 flex-1">{job.name}</span>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-full border shrink-0 ${
                                job.enabled
                                  ? "text-emerald-300 border-emerald-700/50 bg-emerald-900/20"
                                  : "text-slate-400 border-charcoal-blue-600 bg-charcoal-blue-800/60"
                              }`}
                            >
                              {job.enabled ? "Enabled" : "Disabled"}
                            </span>
                          </div>
                          <div className="mt-2 text-[11px] text-slate-400 font-mono break-all">
                            CRON {job.cron_expression}
                          </div>
                          <div className="mt-1 text-[11px] text-slate-500 break-words">
                            Next run: {job.next_run_at ? new Date(job.next_run_at).toLocaleString() : "Not scheduled"}
                          </div>
                          <p className="text-xs text-slate-400 mt-2 line-clamp-3 break-words">{job.task_prompt}</p>
                          <div className="mt-2 grid grid-cols-1 gap-2 w-full min-w-0 max-w-full">
                            <Button
                              size="sm"
                              className="h-7 text-xs bg-emerald-700 hover:bg-emerald-600 text-white w-full min-w-0"
                              disabled={runningCronJobId === job.id}
                              onClick={() => handleRunCronJobNow(job)}
                            >
                              {runningCronJobId === job.id ? (
                                <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                              ) : (
                                <Play className="w-3 h-3 mr-1" />
                              )}
                              Run Now
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs border-charcoal-blue-600 bg-charcoal-blue-800 hover:bg-charcoal-blue-700 w-full min-w-0"
                              onClick={() => openCronEditDialog(job)}
                            >
                              <Pencil className="w-3 h-3 mr-1" />
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              className="h-7 text-xs w-full min-w-0"
                              onClick={() => handleDeleteCronJob(job)}
                            >
                              <Trash2 className="w-3 h-3 mr-1" />
                              Delete
                            </Button>
                          </div>
                        </div>
                      ))}
                      {cronJobs.length === 0 && (
                        <div className="text-center py-4 text-slate-600 text-sm">
                          No scheduled cron jobs configured.
                        </div>
                      )}
                    </div>
                  </div>
                </ScrollArea>
           </TabsContent>

           <TabsContent value="history" className="flex-1 min-h-0 min-w-0 max-w-full mt-0 data-[state=inactive]:hidden overflow-x-hidden">
                <ScrollArea className="h-full w-full min-w-0 max-w-full overflow-x-hidden">
                <div className="space-y-5 pb-4 w-full max-w-full min-w-0">
                    <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-sky-reflection-500 mb-2">Cron Job Runs</h3>
                        <div className="space-y-2">
                            {history.cron_runs.map((run) => (
                            <div key={run.id} className="w-full max-w-full min-w-0 p-3 bg-charcoal-blue-800/30 rounded-lg border border-charcoal-blue-700/50 overflow-hidden">
                                <div className="flex flex-wrap items-start justify-between gap-2 min-w-0 max-w-full">
                                    <span className="text-sm text-slate-200 truncate min-w-0 flex-1">{run.title}</span>
                                    <span className="text-[11px] text-slate-500 w-full sm:w-auto shrink min-w-0 text-left sm:text-right break-words">{new Date(run.updated_at || run.created_at).toLocaleString()}</span>
                                </div>
                                {run.result && <p className="text-xs text-slate-400 mt-2 line-clamp-3 break-words">{run.result}</p>}
                            </div>
                            ))}
                            {history.cron_runs.length === 0 && (
                            <div className="text-center py-4 text-slate-600 text-sm">No completed cron job runs yet.</div>
                            )}
                        </div>
                    </div>

                    <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-500 mb-2">Completed Heartbeat Tasks</h3>
                        <div className="space-y-2">
                            {history.heartbeat_completed.map((run) => (
                            <div key={run.id} className="w-full max-w-full min-w-0 p-3 bg-charcoal-blue-800/30 rounded-lg border border-charcoal-blue-700/50 overflow-hidden">
                                <div className="flex flex-wrap items-start justify-between gap-2 min-w-0 max-w-full">
                                    <span className="text-sm text-slate-200 truncate min-w-0 flex-1">{run.title}</span>
                                    <span className="text-[11px] text-slate-500 w-full sm:w-auto shrink min-w-0 text-left sm:text-right break-words">{new Date(run.updated_at || run.created_at).toLocaleString()}</span>
                                </div>
                                {run.result && <p className="text-xs text-slate-400 mt-2 line-clamp-3 break-words">{run.result}</p>}
                            </div>
                            ))}
                            {history.heartbeat_completed.length === 0 && (
                            <div className="text-center py-4 text-slate-600 text-sm">No completed heartbeat tasks yet.</div>
                            )}
                        </div>
                    </div>
                </div>
                </ScrollArea>
           </TabsContent>
        </Tabs>

        <Dialog
          open={isCronDialogOpen}
          onOpenChange={(open) => {
            if (!open) {
              closeCronDialog();
              return;
            }
            setIsCronDialogOpen(true);
          }}
        >
          <DialogContent className="bg-charcoal-blue-900 border-charcoal-blue-700 text-slate-100">
            <DialogHeader>
              <DialogTitle>Edit Scheduled Cron Job</DialogTitle>
              <DialogDescription className="text-slate-400">
                Update schedule and prompt for this recurring job.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="cron-name">Name</Label>
                <Input
                  id="cron-name"
                  value={cronName}
                  onChange={(e) => setCronName(e.target.value)}
                  className="bg-charcoal-blue-950 border-charcoal-blue-700"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="cron-expression">Cron Expression</Label>
                <Input
                  id="cron-expression"
                  value={cronExpression}
                  onChange={(e) => setCronExpression(e.target.value)}
                  placeholder="*/15 * * * *"
                  className="bg-charcoal-blue-950 border-charcoal-blue-700 font-mono"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="cron-prompt">Task Prompt</Label>
                <Textarea
                  id="cron-prompt"
                  value={cronPrompt}
                  onChange={(e) => setCronPrompt(e.target.value)}
                  className="bg-charcoal-blue-950 border-charcoal-blue-700"
                />
              </div>
              <div className="flex items-center justify-between rounded-md border border-charcoal-blue-700 bg-charcoal-blue-800/40 px-3 py-2">
                <span className="text-sm text-slate-300">Enabled</span>
                <Button
                  type="button"
                  size="sm"
                  variant={cronEnabled ? "default" : "outline"}
                  className={cronEnabled ? "bg-emerald-700 hover:bg-emerald-600" : "border-charcoal-blue-600"}
                  onClick={() => setCronEnabled((v) => !v)}
                >
                  {cronEnabled ? "On" : "Off"}
                </Button>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                className="border-charcoal-blue-600 bg-charcoal-blue-800 hover:bg-charcoal-blue-700"
                onClick={closeCronDialog}
              >
                Cancel
              </Button>
              <Button onClick={handleSaveCronJob} className="bg-baltic-blue-600 hover:bg-baltic-blue-500">
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Mobile Backdrop */}
      {mobileMenuOpen !== 'none' && (
        <div 
          className={`fixed inset-0 bg-black/50 backdrop-blur-sm z-[55] ${mobileMenuOpen === 'left' ? 'md:hidden' : 'lg:hidden'}`}
          onClick={() => setMobileMenuOpen('none')}
        />
      )}
    </div>
  );
}

