"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

type Memory = {
  path: string;
  content: string;
  memory_type: "long-term" | "short-term" | "core";
};

type MemoryMeshProps = {
  memories: Memory[];
  onEdit: (memory: Memory) => void;
  onDelete: (memory: Memory) => void;
  getMemoryTypeColor: (type: Memory['memory_type']) => string;
};

export default function MemoryMesh({ memories, onEdit, onDelete, getMemoryTypeColor }: MemoryMeshProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const getTypeDotColor = (type: Memory["memory_type"]) => {
    switch (type) {
      case "long-term":
        return "hsl(43 92% 60%)";
      case "short-term":
        return "hsl(172 66% 50%)";
      case "core":
        return "hsl(275 70% 65%)";
      default:
        return "hsl(201 52% 58%)";
    }
  };
  const getTypeDotGlow = (type: Memory["memory_type"], alpha: number) => {
    switch (type) {
      case "long-term":
        return `hsla(43, 92%, 60%, ${alpha})`;
      case "short-term":
        return `hsla(172, 66%, 50%, ${alpha})`;
      case "core":
        return `hsla(275, 70%, 65%, ${alpha})`;
      default:
        return `hsla(201, 52%, 58%, ${alpha})`;
    }
  };

  // Generate stable hues per node
  const nodeHues = useMemo(() => {
    return memories.map((_, i) => ((i * 137) % 60) + 180);
  }, [memories]);

  if (memories.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 opacity-60">
        <div className="relative w-24 h-24">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="absolute inset-0 rounded-full border border-sky-reflection-700/30"
              animate={{
                scale: [1, 1.5 + i * 0.3, 1],
                opacity: [0.3, 0, 0.3],
              }}
              transition={{
                duration: 3,
                delay: i * 0.8,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          ))}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-sky-reflection-600/50" />
          </div>
        </div>
        <span className="text-[10px] text-slate-600 tracking-[0.2em] uppercase">
          No memories stored
        </span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col gap-3 min-h-0">
      {/* Utilization Ring */}
      <div className="flex items-center justify-center gap-4 py-2 shrink-0">
        <div className="relative w-16 h-16">
          <svg viewBox="0 0 64 64" className="w-full h-full -rotate-90">
            <circle
              cx="32" cy="32" r="26"
              fill="none"
              stroke="currentColor"
              className="text-charcoal-blue-800"
              strokeWidth="3"
            />
            <motion.circle
              cx="32" cy="32" r="26"
              fill="none"
              stroke="url(#memGrad)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={`${Math.min(memories.length * 8, 163)} 163`}
              initial={{ strokeDasharray: "0 163" }}
              animate={{ strokeDasharray: `${Math.min(memories.length * 8, 163)} 163` }}
              transition={{ duration: 1.5, ease: "easeOut" }}
            />
            <defs>
              <linearGradient id="memGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#3e93c1" />
                <stop offset="100%" stopColor="#65a9cd" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-bold text-sky-reflection-400 font-mono">
              {memories.length}
            </span>
          </div>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-[0.15em] text-slate-500">
            Records
          </span>
          <span className="text-xs text-sky-reflection-500 font-mono tracking-wider">
            VECTOR DB
          </span>
        </div>
      </div>

      {/* Neural Grid */}
      <div className="flex-1 overflow-auto min-h-0 relative">
        <div className="hud-grid-bg rounded-lg p-2">
          <div className="flex flex-wrap gap-1.5">
            {memories.map((mem, i) => (
              <motion.div
                key={i}
                className="relative"
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.02, duration: 0.3 }}
              >
                <motion.button
                  className={`
                    relative w-10 h-10 rounded-lg flex items-center justify-center
                    border cursor-pointer transition-colors duration-200 group
                    ${getMemoryTypeColor(mem.memory_type)}
                    border-sky-reflection-700/30 hover:border-sky-reflection-600/40
                    ${
                      selectedIndex === i
                        ? "ring-1 ring-sky-reflection-500/35 ring-offset-0"
                        : ""
                    }
                  `}
                  whileHover={{ scale: 1.12 }}
                  whileTap={{ scale: 0.92 }}
                  onClick={() =>
                    setSelectedIndex(selectedIndex === i ? null : i)
                  }
                  onMouseEnter={() => setHoveredIndex(i)}
                  onMouseLeave={() => setHoveredIndex(null)}
                  style={{
                    backgroundColor: `hsla(${nodeHues[i]}, 45%, 22%, 0.65)`,
                  }}
                >
                  {/* Glow dot */}
                  <motion.div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor: getTypeDotColor(mem.memory_type),
                    }}
                    animate={{
                      boxShadow: [
                        `0 0 3px ${getTypeDotGlow(mem.memory_type, 0.4)}`,
                        `0 0 10px ${getTypeDotGlow(mem.memory_type, 0.85)}`,
                        `0 0 3px ${getTypeDotGlow(mem.memory_type, 0.4)}`,
                      ],
                    }}
                    transition={{
                      duration: 2 + (i % 3),
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  />
                  {/* Index */}
                  <span className="absolute bottom-0.5 right-1 text-[7px] text-slate-600 font-mono select-none">
                    {String(i + 1).padStart(2, "0")}
                  </span>

                </motion.button>

                {/* Hover tooltip */}
                <AnimatePresence>
                  {hoveredIndex === i && selectedIndex !== i && (
                    <motion.div
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 4 }}
                      className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1
                        bg-charcoal-blue-950/95 border border-sky-reflection-700/40 rounded text-[10px] text-slate-300
                        max-w-[180px] truncate whitespace-nowrap shadow-lg pointer-events-none backdrop-blur-sm"
                    >
                      {mem.path}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Selected Memory Detail */}
        <AnimatePresence>
          {selectedIndex !== null && memories[selectedIndex] && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-2 overflow-hidden"
            >
              <div className="hud-bracket-box p-2.5 bg-charcoal-blue-800/70 rounded-lg border border-sky-reflection-700/25 backdrop-blur-sm relative">
                {/* HUD corner brackets */}
                <div className="absolute top-0 left-0 w-3 h-3 border-t border-l border-sky-reflection-600/40 rounded-tl" />
                <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-sky-reflection-600/40 rounded-tr" />
                <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-sky-reflection-600/40 rounded-bl" />
                <div className="absolute bottom-0 right-0 w-3 h-3 border-b border-r border-sky-reflection-600/40 rounded-br" />

                <div className="flex items-center gap-1.5 mb-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-sky-reflection-500 animate-pulse" />
                  <span className="text-[9px] uppercase tracking-[0.2em] text-sky-reflection-500 font-mono">
                    MEM#{String(selectedIndex + 1).padStart(3, "0")}
                  </span>
                  <div className="ml-auto flex items-center gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-6 w-6 text-slate-300 hover:text-sky-300"
                      onClick={() => onEdit(memories[selectedIndex])}
                      title="Edit Memory"
                    >
                      <Pencil className="w-3 h-3" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-6 w-6 text-red-400 hover:text-red-300"
                      onClick={() => onDelete(memories[selectedIndex])}
                      title="Delete Memory"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed break-words">
                  {memories[selectedIndex].content}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
