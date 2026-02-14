"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { UserRound, Plus, RefreshCw, Trash2 } from "lucide-react";

type RelationshipFact = {
  fact: string;
  tags: string[];
  confidence: number;
  last_confirmed?: string;
};

const normalizeRelationshipFactsPayload = (payload: unknown): RelationshipFact[] => {
  if (!payload || typeof payload !== "object") return [];
  const source = (payload as { facts?: unknown }).facts ?? payload;
  if (!Array.isArray(source)) return [];

  return source
    .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
    .map((item) => ({
      fact: String(item.fact ?? ""),
      tags: Array.isArray(item.tags) ? item.tags.map((tag) => String(tag)).filter(Boolean) : [],
      confidence: Number(item.confidence ?? 0),
      last_confirmed: item.last_confirmed ? String(item.last_confirmed) : undefined,
    }))
    .filter((fact) => fact.fact.length > 0);
};

export default function RelationshipMemoryPanel({ refreshToken = 0 }: { refreshToken?: number }) {
  const [facts, setFacts] = useState<RelationshipFact[]>([]);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [tags, setTags] = useState("preference");
  const [confidence, setConfidence] = useState("0.75");
  const [busy, setBusy] = useState(false);

  const fetchFacts = async () => {
    try {
      const q = query.trim();
      if (!q) {
        const res = await fetch("/api/v1/memory/relationship", { cache: "no-store" });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        setFacts(normalizeRelationshipFactsPayload(data));
        return;
      }
      const res = await fetch("/api/v1/memory/relationship/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, k: 8 }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setFacts(normalizeRelationshipFactsPayload(data));
    } catch (e) {
      console.warn("Failed to fetch relationship memory", e);
    }
  };

  useEffect(() => {
    void fetchFacts();
  }, [refreshToken]);

  const addFact = async () => {
    const fact = draft.trim();
    if (!fact || busy) return;
    const numericConfidence = Number(confidence);
    const clamped = Number.isFinite(numericConfidence)
      ? Math.max(0.5, Math.min(0.99, numericConfidence))
      : 0.75;
    const parsedTags = tags
      .split(",")
      .map((tag) => tag.trim().toLowerCase())
      .filter(Boolean);

    try {
      setBusy(true);
      const res = await fetch("/api/v1/memory/relationship", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fact, tags: parsedTags, confidence: clamped }),
      });
      if (!res.ok) throw new Error(await res.text());
      setDraft("");
      await fetchFacts();
    } catch (e) {
      console.error("Failed to add relationship fact", e);
      alert("Failed to add relationship fact");
    } finally {
      setBusy(false);
    }
  };

  const deleteFact = async (fact: string) => {
    const confirmed = window.confirm(`Delete relationship fact?\n\n"${fact}"`);
    if (!confirmed) return;
    try {
      const res = await fetch(`/api/v1/memory/relationship?fact=${encodeURIComponent(fact)}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(await res.text());
      await fetchFacts();
    } catch (e) {
      console.error("Failed to delete relationship fact", e);
      alert("Failed to delete relationship fact");
    }
  };

  return (
    <div className="mt-3 shrink-0 rounded-lg border border-charcoal-blue-700 bg-charcoal-blue-950/70 p-2.5">
      <div className="mb-2 flex items-center gap-1.5 text-sky-reflection-400">
        <UserRound className="h-3.5 w-3.5" />
        <h2 className="text-[10px] font-semibold uppercase tracking-[0.2em]">Relationship</h2>
      </div>

      <div className="mb-2 flex gap-1.5">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search facts..."
          className="h-7 border-charcoal-blue-700 bg-charcoal-blue-900 text-[11px]"
        />
        <Button
          type="button"
          size="icon"
          variant="outline"
          className="h-7 w-7 border-charcoal-blue-700 bg-charcoal-blue-900 hover:bg-charcoal-blue-800"
          onClick={() => void fetchFacts()}
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
      </div>

      <ScrollArea className="h-28 rounded border border-charcoal-blue-800 bg-charcoal-blue-900/40 px-2 py-1.5">
        <div className="space-y-1.5">
          {facts.map((fact, idx) => (
            <div key={`${fact.fact}-${idx}`} className="rounded border border-charcoal-blue-800/80 bg-charcoal-blue-900/60 p-1.5">
              <div className="flex items-start justify-between gap-1">
                <p className="text-[11px] text-slate-200 break-words">{fact.fact}</p>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="h-5 w-5 text-red-400 hover:text-red-300 hover:bg-charcoal-blue-800"
                  onClick={() => void deleteFact(fact.fact)}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
              <p className="mt-1 text-[10px] text-slate-400 break-words">
                {fact.tags.join(", ") || "user_profile"} | conf {fact.confidence.toFixed(2)} | {fact.last_confirmed || "n/a"}
              </p>
            </div>
          ))}
          {facts.length === 0 && (
            <p className="py-2 text-center text-[11px] text-slate-500">No relationship facts.</p>
          )}
        </div>
      </ScrollArea>

      <Textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Add durable user fact..."
        className="mt-2 min-h-[54px] border-charcoal-blue-700 bg-charcoal-blue-900 text-[11px]"
      />
      <div className="mt-1.5 flex gap-1.5">
        <Input
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="tags: preference, communication_style"
          className="h-7 border-charcoal-blue-700 bg-charcoal-blue-900 text-[11px]"
        />
        <Input
          type="number"
          min="0.5"
          max="0.99"
          step="0.05"
          value={confidence}
          onChange={(e) => setConfidence(e.target.value)}
          className="h-7 w-16 border-charcoal-blue-700 bg-charcoal-blue-900 text-[11px]"
        />
        <Button
          type="button"
          size="sm"
          className="h-7 bg-baltic-blue-600 px-2 text-[11px] hover:bg-baltic-blue-500"
          disabled={!draft.trim() || busy}
          onClick={() => void addFact()}
        >
          <Plus className="mr-1 h-3 w-3" />
          Add
        </Button>
      </div>
    </div>
  );
}
