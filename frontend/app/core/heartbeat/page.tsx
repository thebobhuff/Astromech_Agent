"use client";

import { useState, useEffect } from "react";
import { Save, RefreshCw, Activity, Clock, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FeatureInfoIcon } from "@/components/feature-info-icon";

export default function HeartbeatPage() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("Loading...");

  const fetchHeartbeat = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/system/files/heartbeat");
      if (res.ok) {
        const data = await res.json();
        setContent(data.content);
        setStatus("Loaded");
      } else {
        setStatus("Error loading file");
      }
    } catch (error) {
      console.error(error);
      setStatus("Connection error");
    } finally {
      setLoading(false);
    }
  };

  const saveHeartbeat = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/v1/system/files/heartbeat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        setStatus("Saved successfully");
        setTimeout(() => setStatus("Ready"), 2000);
      } else {
        setStatus("Error saving file");
      }
    } catch (error) {
      console.error(error);
      setStatus("Connection error");
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    fetchHeartbeat();
  }, []);

  return (
    <div className="flex flex-col h-full bg-charcoal-blue-900 text-slate-200 p-6 overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/20 rounded-lg">
            <Activity className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-2xl font-bold text-slate-100">Autonomous Heartbeat</h1>
              <FeatureInfoIcon featureId="FE-009" featureName="Heartbeat Dashboard" />
            </div>
            <p className="text-sm text-slate-400">Manage standing orders and autonomous protocols (Checked every 30m)</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 bg-charcoal-blue-800 px-3 py-1 rounded-full border border-charcoal-blue-700">
                {status}
            </span>
            <Button 
                variant="outline" 
                size="sm" 
                onClick={fetchHeartbeat} 
                className="border-charcoal-blue-700 hover:bg-charcoal-blue-800 text-slate-400 hover:text-slate-300"
            >
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Reload
            </Button>
            <Button 
                onClick={saveHeartbeat} 
                disabled={saving}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
                <Save className="w-4 h-4 mr-2" />
                {saving ? "Saving..." : "Save Orders"}
            </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        <div className="lg:col-span-2 flex flex-col h-full gap-2">
            <div className="bg-charcoal-blue-800/50 rounded-t-lg border border-charcoal-blue-700 p-3 flex items-center justify-between">
                <span className="text-sm font-inconsolata font-semibold text-emerald-400">DATA/HEARTBEAT.MD</span>
                <span className="text-xs text-slate-500">Markdown format supported</span>
            </div>
            <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="flex-1 bg-charcoal-blue-950 font-mono text-sm border-charcoal-blue-700 focus:ring-emerald-500/50 resize-none p-4 leading-relaxed"
                spellCheck={false}
            />
        </div>
        
        <div className="flex flex-col gap-4">
            <div className="bg-charcoal-blue-800 rounded-lg p-5 border border-charcoal-blue-700">
                <h3 className="font-semibold text-slate-200 mb-3 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-sky-400" />
                    How it Works
                </h3>
                <p className="text-sm text-slate-400 leading-relaxed mb-4">
                    The Heartbeat system periodically wakes up a specialized instance of the agent to check these "Standing Orders".
                </p>
                <ul className="text-sm text-slate-400 space-y-2 list-disc pl-4 marker:text-emerald-500">
                    <li>
                        Checks run automatically every <span className="text-emerald-400 font-mono">30 minutes</span>.
                    </li>
                    <li>
                        The agent will read this file and execute any instructions that are relevant to the current time or state.
                    </li>
                    <li>
                        If no action is needed, the agent stays silent.
                    </li>
                </ul>
            </div>

            <div className="bg-charcoal-blue-800 rounded-lg p-5 border border-charcoal-blue-700 flex-1">
                 <h3 className="font-semibold text-slate-200 mb-3 flex items-center gap-2">
                    <Play className="w-4 h-4 text-purple-400" />
                    Example Orders
                </h3>
                <div className="text-xs font-mono text-slate-400 bg-charcoal-blue-900/50 p-3 rounded border border-charcoal-blue-700/50 overflow-auto max-h-[300px]">
<pre>{`## Daily Routine
- At 09:00, check my unread emails and summarize urgent ones.
- At 18:00, ensure all tasks marked "in_progress" have a status update.

## Maintenance
- Check disk space usage on the server once a day.
- Verify that the backup job ran successfully last night.

## Research
- Every 4 hours, check for news about "Astromech Droids" and save interesting articles to memory.`}</pre>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}
