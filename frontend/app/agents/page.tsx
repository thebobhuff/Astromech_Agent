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
  Users, Plus, Settings, RefreshCw, Terminal, Search
} from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

type AgentProfile = {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  allowed_tools: string[];
  parent_id?: string;
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);
  
  // New Agent Form State
  const [newAgent, setNewAgent] = useState<AgentProfile>({
    id: "",
    name: "",
    description: "",
    system_prompt: "",
    allowed_tools: ["all"]
  });

  const [toolsInput, setToolsInput] = useState("all");

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/agent/profiles", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setAgents(data);
      }
    } catch (e) {
      console.error("Failed to fetch agents", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      // Process tools input
      const tools = toolsInput.split(",").map(t => t.trim()).filter(t => t.length > 0);
      
      const payload = {
        ...newAgent,
        allowed_tools: tools.length > 0 ? tools : ["all"]
      };
      
      const res = await fetch("/api/v1/agent/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        setOpenDialog(false);
        fetchAgents();
        // Reset form
        setNewAgent({
            id: "",
            name: "",
            description: "",
            system_prompt: "",
            allowed_tools: ["all"]
        });
        setToolsInput("all");
      }
    } catch (e) {
      console.error("Failed to create agent", e);
    } finally {
      setSaving(false);
    }
  };

  if (loading && agents.length === 0) {
    return <div className="p-8 text-slate-400">Loading agents...</div>;
  }

  return (
    <div className="h-full bg-charcoal-blue-950 text-slate-100 p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto w-full space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-baltic-blue-900/50 rounded-xl border border-baltic-blue-800 shadow-lg shadow-baltic-blue-900/20">
              <Users className="w-8 h-8 text-sky-reflection-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Agent Fleet</h1>
                <FeatureInfoIcon featureId="FE-011" featureName="Agent Management" />
              </div>
              <p className="text-slate-400">Manage subagents and specialized workers.</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchAgents} className="border-charcoal-blue-700 hover:bg-charcoal-blue-800 text-slate-400 hover:text-slate-100">
                <RefreshCw className="w-4 h-4 mr-2" /> Refresh
            </Button>
            
            <Dialog open={openDialog} onOpenChange={setOpenDialog}>
                <DialogTrigger asChild>
                    <Button className="bg-baltic-blue-600 hover:bg-baltic-blue-500 text-white">
                        <Plus className="w-4 h-4 mr-2" /> Create Agent
                    </Button>
                </DialogTrigger>
                <DialogContent className="bg-charcoal-blue-900 border-charcoal-blue-800 text-slate-100 max-w-2xl">
                    <DialogHeader>
                    <DialogTitle>Decommission New Agent</DialogTitle>
                    <DialogDescription className="text-slate-400">
                        Define the identity and capabilities of a new subagent.
                    </DialogDescription>
                    </DialogHeader>
                    
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="id">Agent ID</Label>
                                <Input
                                id="id"
                                value={newAgent.id}
                                onChange={(e) => setNewAgent({...newAgent, id: e.target.value})}
                                placeholder="e.g. researcher"
                                className="bg-charcoal-blue-950 border-charcoal-blue-700"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="name">Display Name</Label>
                                <Input
                                id="name"
                                value={newAgent.name}
                                onChange={(e) => setNewAgent({...newAgent, name: e.target.value})}
                                placeholder="e.g. Junior Researcher"
                                className="bg-charcoal-blue-950 border-charcoal-blue-700"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="description">Description</Label>
                            <Input
                            id="description"
                            value={newAgent.description}
                            onChange={(e) => setNewAgent({...newAgent, description: e.target.value})}
                            placeholder="Short description of capabilities"
                            className="bg-charcoal-blue-950 border-charcoal-blue-700"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="system_prompt">System Prompt</Label>
                            <Textarea
                            id="system_prompt"
                            value={newAgent.system_prompt}
                            onChange={(e) => setNewAgent({...newAgent, system_prompt: e.target.value})}
                            placeholder="You are an expert at..."
                            className="bg-charcoal-blue-950 border-charcoal-blue-700 min-h-[150px]"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="tools">Allowed Tools (comma separated)</Label>
                            <Input
                            id="tools"
                            value={toolsInput}
                            onChange={(e) => setToolsInput(e.target.value)}
                            placeholder="google_search, read_file, or 'all'"
                            className="bg-charcoal-blue-950 border-charcoal-blue-700"
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpenDialog(false)} className="border-charcoal-blue-700 hover:bg-charcoal-blue-800 text-slate-300">
                            Cancel
                        </Button>
                        <Button onClick={handleCreate} disabled={saving} className="bg-baltic-blue-600 hover:bg-baltic-blue-500">
                            {saving ? "Creating..." : "Create Agent"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <Card key={agent.id} className="bg-charcoal-blue-900 border-charcoal-blue-800 flex flex-col hover:border-baltic-blue-700 transition-all">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="p-2 bg-charcoal-blue-950 rounded-lg border border-charcoal-blue-800">
                    <Terminal className="w-6 h-6 text-indigo-400" />
                  </div>
                  <Badge variant="outline" className="text-slate-500 border-slate-700">
                    ID: {agent.id}
                  </Badge>
                </div>
                <CardTitle className="mt-4 text-slate-100">{agent.name}</CardTitle>
                <CardDescription className="text-slate-400 line-clamp-2">{agent.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 space-y-4">
                 <div className="space-y-2">
                    <Label className="text-xs text-slate-500 uppercase tracking-widest">Capabilities</Label>
                    <div className="flex flex-wrap gap-1">
                        {agent.allowed_tools.slice(0, 3).map(tool => (
                            <Badge key={tool} variant="secondary" className="bg-charcoal-blue-950 text-slate-400 hover:bg-charcoal-blue-800">
                                {tool}
                            </Badge>
                        ))}
                        {agent.allowed_tools.length > 3 && (
                            <Badge variant="secondary" className="bg-charcoal-blue-950 text-slate-400">
                                +{agent.allowed_tools.length - 3} more
                            </Badge>
                        )}
                    </div>
                 </div>
              </CardContent>
              <CardFooter className="bg-charcoal-blue-950/30 border-t border-charcoal-blue-800 p-4">
                 <Button variant="ghost" className="w-full text-slate-400 hover:text-slate-100 hover:bg-charcoal-blue-800">
                    <Settings className="w-4 h-4 mr-2" /> Manage Details
                 </Button>
              </CardFooter>
            </Card>
          ))}
        </div>

      </div>
    </div>
  );
}
