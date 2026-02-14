"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FeatureInfoIcon } from "@/components/feature-info-icon";
import { 
  Cpu, Save, RefreshCw, Zap, Server, 
  Database, Brain, Terminal, Shield,
  FileText, LayoutDashboard, Settings, HardDrive
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils"; // Assuming utils exists, otherwise I'll mock it or use inline

type AgentIdentity = {
  name: string;
  role: string;
  personality: string;
};

type SystemStatus = {
  platform: string;
  python_version: string;
  rag_enabled: boolean;
  skills_loaded: number;
  workspace_path: string;
};

type LLMConfig = {
  provider: string;
  model: string;
};

const CORE_FILES = [
  { id: "core", name: "CORE.md", description: "Primary Directives & Rules" },
  { id: "judgement", name: "JUDGEMENT.md", description: "Decision Making & Autonomy" },
  { id: "user", name: "USER.md", description: "User Profile & Preferences" },
  { id: "agents", name: "AGENTS.md", description: "Sub-Agent Definitions" },
  { id: "memory", name: "MEMORY.md", description: "Long-term Facts" },
];

export default function CorePage() {
  const [activeTab, setActiveTab] = useState<"identity" | "files" | "system">("identity");
  const [selectedFile, setSelectedFile] = useState<string>("core");
  
  const [identity, setIdentity] = useState<AgentIdentity>({
    name: "",
    role: "",
    personality: ""
  });
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [llm, setLlm] = useState<LLMConfig | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [originalFileContent, setOriginalFileContent] = useState<string>("");
  
  const [loading, setLoading] = useState(true);
  const [fileLoading, setFileLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    fetchStatus();
    if (activeTab === "files") {
      fetchFile(selectedFile);
    }
  }, []);

  // Effect to load file when tab or selection changes
  useEffect(() => {
    if (activeTab === "files") {
      fetchFile(selectedFile);
    }
  }, [activeTab, selectedFile]);

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/v1/agent/status", { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to fetch status");
      const data = await res.json();
      
      if (data.identity) setIdentity(data.identity);
      if (data.system) setSystem(data.system);
      if (data.llm) setLlm(data.llm);
      
    } catch (e) {
      console.error(e);
      setMessage({ type: 'error', text: 'Failed to connect to Astromech Core API.' });
    } finally {
      setLoading(false);
    }
  };

  const fetchFile = async (fileName: string) => {
    setFileLoading(true);
    try {
      const res = await fetch(`/api/v1/system/files/${fileName}`, { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to load file");
      const data = await res.json();
      const content = data.content || "";
      setFileContent(content);
      setOriginalFileContent(content);
    } catch (e) {
      console.error(e);
      const errorText = "Error loading file content.";
      setFileContent(errorText);
      setOriginalFileContent(errorText);
    } finally {
      setFileLoading(false);
    }
  };

  const handleSaveIdentity = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch("/api/v1/agent/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(identity)
      });
      
      if (!res.ok) throw new Error("Failed to save configuration");
      
      setMessage({ type: 'success', text: 'Identity Matrix updated successfully.' });
    } catch (e) {
      console.error(e);
      setMessage({ type: 'error', text: 'Failed to persist configuration.' });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveFile = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`/api/v1/system/files/${selectedFile}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: fileContent })
      });
      
      if (!res.ok) throw new Error("Failed to save file");
      setOriginalFileContent(fileContent);
      setMessage({ type: 'success', text: `${CORE_FILES.find(f => f.id === selectedFile)?.name} updated successfully.` });
    } catch (e) {
      console.error(e);
      setMessage({ type: 'error', text: 'Failed to save file content.' });
    } finally {
      setSaving(false);
    }
  };

  const isFileDirty = fileContent !== originalFileContent;
  const lineCount = fileContent ? fileContent.split("\n").length : 0;
  const wordCount = fileContent.trim() ? fileContent.trim().split(/\s+/).length : 0;
  const selectedFileMeta = CORE_FILES.find((f) => f.id === selectedFile);
  const handleRevertFile = () => {
    setFileContent(originalFileContent);
    setMessage(null);
  };

  if (loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-sky-reflection-400 gap-4">
        <Cpu className="w-12 h-12 animate-pulse" />
        <div className="text-sm font-mono tracking-widest">INITIALIZING CORE...</div>
      </div>
    );
  }

  return (
    <div className="h-full bg-charcoal-blue-950 text-slate-100 flex flex-col overflow-hidden">
      
      {/* Header */}
      <div className="flex-none p-6 pb-2">
        <div className="max-w-7xl mx-auto w-full flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-baltic-blue-900/50 rounded-xl border border-baltic-blue-800 shadow-lg shadow-baltic-blue-900/20">
              <Cpu className="w-8 h-8 text-sky-reflection-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Core Configuration</h1>
                <FeatureInfoIcon featureId="FE-014" featureName="Core Hub" />
              </div>
              <p className="text-slate-400">Manage agent identity, knowledge base, and system parameters.</p>
            </div>
          </div>
          <Button variant="outline" onClick={fetchStatus} className="border-charcoal-blue-700 hover:bg-charcoal-blue-800 text-slate-400 hover:text-slate-100">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto w-full flex space-x-1 border-b border-charcoal-blue-800">
          <button
            onClick={() => setActiveTab("identity")}
            className={`px-4 py-2 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "identity" 
                ? "border-baltic-blue-500 text-baltic-blue-400" 
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" /> Identity Matrix
          </button>
          <button
            onClick={() => setActiveTab("files")}
            className={`px-4 py-2 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "files" 
                ? "border-baltic-blue-500 text-baltic-blue-400" 
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileText className="w-4 h-4" /> Knowledge Core
          </button>
          <button
            onClick={() => setActiveTab("system")}
            className={`px-4 py-2 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "system" 
                ? "border-baltic-blue-500 text-baltic-blue-400" 
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Settings className="w-4 h-4" /> System Specs
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6 pt-4">
        <div className="max-w-7xl mx-auto w-full">
          
          {/* TAB: IDENTITY (Legacy) */}
          {activeTab === "identity" && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="xl:col-span-2 space-y-8">
                <Card className="bg-charcoal-blue-900 border-charcoal-blue-800 shadow-xl overflow-hidden">
                  <div className="h-1 bg-gradient-to-r from-baltic-blue-500 to-sky-reflection-500 w-full" />
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-sky-reflection-100 font-medium">
                      <Shield className="w-5 h-5 text-baltic-blue-400" />
                      Agent Persona
                    </CardTitle>
                    <CardDescription className="text-slate-400">
                      Define the agent's persona. Used as a fallback if CORE.md is missing.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label htmlFor="agent-name" className="text-slate-300">Designation (Name)</Label>
                        <Input 
                          id="agent-name" 
                          value={identity.name} 
                          onChange={(e) => setIdentity({...identity, name: e.target.value})}
                          className="bg-charcoal-blue-950 border-charcoal-blue-700 focus:border-baltic-blue-500 text-lg font-medium text-slate-200" 
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="agent-role" className="text-slate-300">Primary Directive (Role)</Label>
                        <Input 
                          id="agent-role" 
                          value={identity.role} 
                          onChange={(e) => setIdentity({...identity, role: e.target.value})}
                          className="bg-charcoal-blue-950 border-charcoal-blue-700 focus:border-baltic-blue-500 text-slate-200" 
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="agent-soul" className="text-slate-300">Cognitive Profile (Personality)</Label>
                      <Textarea 
                        id="agent-soul" 
                        value={identity.personality} 
                        onChange={(e) => setIdentity({...identity, personality: e.target.value})}
                        className="bg-charcoal-blue-950 border-charcoal-blue-700 min-h-[150px] focus:border-baltic-blue-500 leading-relaxed text-slate-200" 
                        placeholder="Describe how the agent interacts with users..."
                      />
                    </div>
                  </CardContent>
                  <CardFooter className="bg-charcoal-blue-950/30 border-t border-charcoal-blue-800 p-6 flex justify-between items-center">
                    <div className="text-sm">
                      {message && (
                        <span className={`inline-flex items-center ${message.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                          {message.type === 'success' ? <Zap className="w-4 h-4 mr-2" /> : null}
                          {message.text}
                        </span>
                      )}
                    </div>
                    <Button 
                      onClick={handleSaveIdentity} 
                      disabled={saving}
                      className="bg-baltic-blue-600 hover:bg-baltic-blue-500 text-white min-w-[140px]"
                    >
                      {saving ? "Saving..." : "Update Identity"}
                    </Button>
                  </CardFooter>
                </Card>
              </div>
              <div className="space-y-6">
                {/* System Status Summary (Small) */}
                <Card className="bg-charcoal-blue-900 border-charcoal-blue-800">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base font-medium text-slate-300 flex items-center gap-2">
                        <Server className="w-4 h-4 text-green-400" />
                        System Status
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center justify-between mb-2">
                         <span className="text-slate-400 text-sm">Status</span>
                         <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                            <span className="text-green-400 text-sm font-medium">Online</span>
                         </div>
                      </div>
                      <div className="flex items-center justify-between">
                         <span className="text-slate-400 text-sm">Skills</span>
                         <span className="text-slate-200 text-sm font-medium">{system?.skills_loaded || 0} loaded</span>
                      </div>
                    </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* TAB: KNOWLEDGE CORE (Files) */}
          {activeTab === "files" && (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-250px)] animate-in fade-in slide-in-from-bottom-2 duration-300">
              
              {/* File List */}
              <div className="lg:col-span-1 space-y-3">
                 {CORE_FILES.map((file) => (
                   <button
                     key={file.id}
                     onClick={() => { setSelectedFile(file.id); setMessage(null); }}
                     className={`w-full text-left p-4 rounded-lg border transition-all ${
                       selectedFile === file.id 
                         ? "bg-baltic-blue-900/40 border-baltic-blue-500/50 shadow-md" 
                         : "bg-charcoal-blue-900 border-charcoal-blue-800 hover:border-charcoal-blue-700 hover:bg-charcoal-blue-800"
                     }`}
                   >
                     <div className="flex items-center justify-between mb-1">
                        <span className={`font-mono font-medium ${selectedFile === file.id ? "text-baltic-blue-300" : "text-slate-300"}`}>
                          {file.name}
                        </span>
                        {selectedFile === file.id && <div className="w-2 h-2 bg-baltic-blue-400 rounded-full" />}
                     </div>
                     <div className="text-xs text-slate-500">{file.description}</div>
                   </button>
                 ))}
                 
                 <div className="bg-charcoal-blue-950/50 p-4 rounded-lg border border-charcoal-blue-800 mt-6">
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Instructions</h4>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      These Markdown files directly control the agent's behavior and long-term memory. 
                      Changes take effect immediately upon save for new interactions.
                    </p>
                 </div>
              </div>

              {/* Editor */}
              <div className="lg:col-span-3 flex flex-col h-full bg-charcoal-blue-900 border border-charcoal-blue-800 rounded-lg overflow-hidden shadow-xl">
                 <div className="flex items-center justify-between px-4 py-3 border-b border-charcoal-blue-800 bg-charcoal-blue-950/50">
                    <div className="flex items-center gap-3">
                       <FileText className="w-4 h-4 text-slate-400" />
                       <span className="text-sm font-medium text-slate-200">
                         {selectedFileMeta?.name}
                       </span>
                       <Badge
                        variant="outline"
                        className={cn(
                          "text-[10px] uppercase tracking-wide",
                          isFileDirty ? "border-amber-500/50 text-amber-300" : "border-emerald-500/50 text-emerald-300"
                        )}
                       >
                         {isFileDirty ? "Unsaved" : "Synced"}
                       </Badge>
                       <span className="text-xs text-slate-500 font-mono">
                         {lineCount} lines • {wordCount} words
                       </span>
                    </div>
                    
                    <div className="flex items-center gap-4">
                       {message && (
                          <span className={`text-xs ${message.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                            {message.text}
                          </span>
                       )}
                       <Button
                        size="sm"
                        variant="outline"
                        onClick={handleRevertFile}
                        disabled={saving || fileLoading || !isFileDirty}
                        className="h-8 border-charcoal-blue-700 text-slate-200 hover:bg-charcoal-blue-800"
                       >
                         Revert
                       </Button>
                       <Button 
                        size="sm" 
                        onClick={handleSaveFile}
                        disabled={saving || fileLoading || !isFileDirty}
                        className="h-8 bg-baltic-blue-600 hover:bg-baltic-blue-500 text-slate-50"
                       >
                         {saving ? <RefreshCw className="w-3 h-3 animate-spin mr-2" /> : <Save className="w-3 h-3 mr-2" />}
                         Save Changes
                       </Button>
                    </div>
                 </div>
                 
                 <div className="flex-1 relative">
                    {fileLoading ? (
                      <div className="absolute inset-0 flex items-center justify-center bg-charcoal-blue-900/80 z-10">
                         <RefreshCw className="w-8 h-8 text-baltic-blue-500 animate-spin" />
                      </div>
                    ) : (
                      <textarea
                        value={fileContent}
                        onChange={(e) => setFileContent(e.target.value)}
                        className="w-full h-full bg-charcoal-blue-900 text-slate-200 font-mono text-sm p-4 resize-none focus:outline-none"
                        spellCheck={false}
                      />
                    )}
                 </div>
              </div>
            </div>
          )}

          {/* TAB: SYSTEM SPECS (Read Only) */}
          {activeTab === "system" && (
            <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                <Card className="bg-charcoal-blue-900 border-charcoal-blue-800">
                   <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                         <Terminal className="w-5 h-5 text-slate-400" />
                         Runtime Environment
                      </CardTitle>
                   </CardHeader>
                   <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm font-mono">
                         <div className="p-4 bg-charcoal-blue-950 rounded border border-charcoal-blue-800/50">
                            <div className="text-slate-500 mb-1">Platform</div>
                            <div className="text-slate-200 truncate">{system?.platform || "Unknown"}</div>
                         </div>
                         <div className="p-4 bg-charcoal-blue-950 rounded border border-charcoal-blue-800/50">
                            <div className="text-slate-500 mb-1">Python Runtime</div>
                            <div className="text-slate-200">{system?.python_version || "Unknown"}</div>
                         </div>
                         <div className="p-4 bg-charcoal-blue-950 rounded border border-charcoal-blue-800/50 md:col-span-2">
                            <div className="text-slate-500 mb-1">Workspace Root</div>
                            <div className="text-slate-200 truncate">{system?.workspace_path || "Unknown"}</div>
                         </div>
                      </div>
                   </CardContent>
                </Card>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card className="bg-charcoal-blue-900 border-charcoal-blue-800">
                       <CardHeader>
                          <CardTitle className="text-base font-medium text-slate-300 flex items-center gap-2">
                             <Brain className="w-4 h-4 text-purple-400" />
                             Cognitive Engine
                          </CardTitle>
                       </CardHeader>
                       <CardContent className="space-y-4">
                          <div className="flex justify-between items-center">
                             <span className="text-slate-400 text-sm">Provider</span>
                             <Badge variant="outline" className="border-purple-500/30 text-purple-300 uppercase">
                                {llm?.provider || "Unknown"}
                             </Badge>
                          </div>
                          <div className="flex justify-between items-center">
                             <span className="text-slate-400 text-sm">Model</span>
                             <span className="text-slate-200 font-mono text-sm">{llm?.model || "Auto"}</span>
                          </div>
                          <div className="pt-2 border-t border-charcoal-blue-800 mt-2">
                            <div className="flex justify-between items-center">
                                <span className="text-slate-400 text-sm">RAG Memory</span>
                                {system?.rag_enabled ? (
                                  <Badge className="bg-green-500/20 text-green-400 hover:bg-green-500/30 border-green-500/50">active</Badge>
                                ) : (
                                  <Badge variant="outline" className="text-slate-500 border-slate-700">disabled</Badge>
                                )}
                            </div>
                          </div>
                       </CardContent>
                    </Card>

                    <Card className="bg-charcoal-blue-900 border-charcoal-blue-800">
                       <CardHeader>
                          <CardTitle className="text-base font-medium text-slate-300 flex items-center gap-2">
                             <Database className="w-4 h-4 text-honey-bronze-400" />
                             Capabilities
                          </CardTitle>
                       </CardHeader>
                       <CardContent className="space-y-4">
                          <div className="text-center py-4">
                             <div className="text-4xl font-bold text-slate-100">{system?.skills_loaded || 0}</div>
                             <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Active Skills</div>
                          </div>
                       </CardContent>
                    </Card>
                </div>

                <Card className="bg-charcoal-blue-900 border-charcoal-blue-800">
                  <CardHeader>
                    <CardTitle className="text-base font-medium text-slate-300 flex items-center gap-2">
                      <HardDrive className="w-4 h-4 text-baltic-blue-300" />
                      Prompt Stack Overview
                    </CardTitle>
                    <CardDescription className="text-slate-500">
                      Runtime prompt layers loaded for orchestration behavior.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {CORE_FILES.map((file) => (
                      <div
                        key={file.id}
                        className="flex items-center justify-between p-3 rounded-md border border-charcoal-blue-800/70 bg-charcoal-blue-950/40"
                      >
                        <div>
                          <div className="text-sm text-slate-200 font-mono">{file.name}</div>
                          <div className="text-xs text-slate-500">{file.description}</div>
                        </div>
                        <Badge variant="outline" className="border-emerald-500/40 text-emerald-300">
                          available
                        </Badge>
                      </div>
                    ))}
                  </CardContent>
                </Card>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

