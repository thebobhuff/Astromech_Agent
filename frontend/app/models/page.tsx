"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { FeatureInfoIcon } from "@/components/feature-info-icon";
import { Loader2, Plus, Trash2, RefreshCw, Save, Eye, EyeOff } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ModelConfig {
  provider: string;
  name: string;
  model_id: string;
  description: string;
  is_active: boolean;
}

interface ProviderConfig {
  provider: string; // This is actually the "type" or protocol
  enabled: boolean;
  base_url?: string;
  api_key?: string;
  available_models: string[];
}

interface SystemConfig {
  active_models: ModelConfig[];
  providers: Record<string, ProviderConfig>;
}

export default function ModelsPage() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();
  
  // New Provider State
  const [isAddProviderOpen, setIsAddProviderOpen] = useState(false);
  const [newProviderId, setNewProviderId] = useState("");
  const [newProviderType, setNewProviderType] = useState("openai");
  
  // Show/Hide API Keys
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/models/");
      if (!res.ok) throw new Error("Failed to fetch config");
      const data = await res.json();
      setConfig(data);
    } catch (error) {
      toast({ title: "Error", description: "Could not load model configuration", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    if (!config) return;
    try {
      setSaving(true);
      const res = await fetch("/api/v1/models/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) throw new Error("Failed to save");
      toast({ title: "Success", description: "Configuration saved successfully" });
    } catch (error) {
      toast({ title: "Error", description: "Failed to save configuration", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const refreshOllama = async () => {
    try {
      const res = await fetch("/api/v1/models/refresh-ollama", { method: "POST" });
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      toast({ title: "Ollama Refreshed", description: `Found ${data.models.length} models.` });
      fetchConfig();
    } catch (e) {
      toast({ title: "Error", description: "Could not refresh Ollama models", variant: "destructive" });
    }
  };

  const toggleModel = (index: number) => {
    if (!config) return;
    const newModels = [...config.active_models];
    newModels[index].is_active = !newModels[index].is_active;
    setConfig({ ...config, active_models: newModels });
  };

  const addModel = () => {
    if (!config) return;
    const newModel: ModelConfig = {
      provider: "gemini",
      name: "new-model",
      model_id: "gemini-1.5-flash",
      description: "New model configuration",
      is_active: true
    };
    setConfig({ ...config, active_models: [...config.active_models, newModel] });
  };
  
  const removeModel = (index: number) => {
    if (!config) return;
    const newModels = config.active_models.filter((_, i) => i !== index);
    setConfig({ ...config, active_models: newModels });
  };

  const updateModel = (index: number, field: keyof ModelConfig, value: any) => {
     if (!config) return;
     const newModels = [...config.active_models];
     newModels[index] = { ...newModels[index], [field]: value };
     setConfig({ ...config, active_models: newModels });
  };

  const updateProvider = (key: string, field: keyof ProviderConfig, value: any) => {
     if (!config) return;
     const newProviders = {...config.providers};
     newProviders[key] = { ...newProviders[key], [field]: value };
     setConfig({...config, providers: newProviders});
  };
  
  const handleAddProvider = () => {
      if (!config || !newProviderId) return;
      
      const newProviders = {...config.providers};
      newProviders[newProviderId.toLowerCase()] = {
          provider: newProviderType,
          enabled: true,
          available_models: [],
          api_key: "",
          base_url: newProviderType === "ollama" ? "http://localhost:11434" : "" 
      };
      
      setConfig({ ...config, providers: newProviders });
      setNewProviderId("");
      setIsAddProviderOpen(false);
      toast({ title: "Provider Added", description: `Configured ${newProviderId} as ${newProviderType} provider.` });
  };

  const toggleKeyVisibility = (key: string) => {
      setShowKeys(prev => ({...prev, [key]: !prev[key]}));
  };

  if (loading || !config) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-baltic-blue-500" />
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 overflow-y-auto h-full text-slate-100 font-sans">
            <div className="max-w-4xl mx-auto space-y-8">
                <div className="flex justify-between items-center bg-charcoal-blue-900/50 p-6 rounded-2xl border border-charcoal-blue-800 backdrop-blur-sm">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-reflection-300 to-white bg-clip-text text-transparent">Model Registry</h1>
                            <FeatureInfoIcon featureId="FE-010" featureName="Model Registry" />
                        </div>
                        <p className="text-slate-400">Manage LLM providers and configure active models for the agent.</p>
                    </div>
                    <Button onClick={saveConfig} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-900/20">
                        {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                        Save Changes
                    </Button>
                </div>

                <Tabs defaultValue="active-models" className="w-full">
                    <TabsList className="bg-charcoal-blue-900 border border-charcoal-blue-700 p-1">
                        <TabsTrigger value="active-models">Active Models</TabsTrigger>
                        <TabsTrigger value="providers">Providers</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="active-models" className="space-y-4 mt-6">
                        <div className="grid gap-4">
                            {config.active_models.map((model, idx) => (
                                <Card key={idx} className="bg-charcoal-blue-900 border-charcoal-blue-800">
                                    <CardContent className="p-6 flex items-start gap-4">
                                        <div className="pt-2">
                                           <Switch checked={model.is_active} onCheckedChange={() => toggleModel(idx)} />
                                        </div>
                                        <div className="flex-1 grid grid-cols-2 lg:grid-cols-4 gap-4">
                                            <div className="space-y-1">
                                                <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Config Alias</label>
                                                <Input 
                                                    value={model.name} 
                                                    onChange={(e) => updateModel(idx, 'name', e.target.value)} 
                                                    className="bg-charcoal-blue-950 border-charcoal-blue-700"
                                                />
                                            </div>
                                            <div className="space-y-1">
                                                <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Provider</label>
                                                 {/* Use providers from config keys */}
                                                <select 
                                                    className="w-full h-10 px-3 rounded-md border border-charcoal-blue-700 bg-charcoal-blue-950 text-sm focus:outline-none focus:ring-2 focus:ring-baltic-blue-500"
                                                    value={model.provider}
                                                    onChange={(e) => updateModel(idx, 'provider', e.target.value)}
                                                >
                                                    {Object.keys(config.providers).map(p => (
                                                        <option key={p} value={p}>{p}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div className="space-y-1">
                                                <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Model ID</label>
                                                <Input 
                                                    value={model.model_id} 
                                                    onChange={(e) => updateModel(idx, 'model_id', e.target.value)} 
                                                    className="bg-charcoal-blue-950 border-charcoal-blue-700 font-mono text-xs"
                                                />
                                            </div>
                                            <div className="space-y-1">
                                                <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Reasoning</label>
                                                <Input 
                                                    value={model.description} 
                                                    onChange={(e) => updateModel(idx, 'description', e.target.value)} 
                                                    className="bg-charcoal-blue-950 border-charcoal-blue-700 text-xs"
                                                />
                                            </div>
                                        </div>
                                        <Button variant="ghost" size="icon" onClick={() => removeModel(idx)} className="text-slate-500 hover:text-red-400">
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                        <Button variant="outline" onClick={addModel} className="w-full border-dashed border-charcoal-blue-700 text-slate-400 hover:bg-charcoal-blue-800 hover:text-white">
                            <Plus className="mr-2 h-4 w-4" /> Add Model Configuration
                        </Button>
                    </TabsContent>

                    <TabsContent value="providers" className="space-y-4 mt-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {Object.entries(config.providers).map(([key, provider]) => (
                                <Card key={key} className="bg-charcoal-blue-900 border-charcoal-blue-800">
                                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                                        <div className="flex items-center gap-2">
                                            <CardTitle className="capitalize text-lg">{key}</CardTitle>
                                            {provider.enabled && <Badge className="bg-emerald-900 text-emerald-300 border-none">Enabled</Badge>}
                                        </div>
                                        {key === 'ollama' && (
                                            <Button variant="ghost" size="icon" onClick={refreshOllama} title="Fetch models">
                                                <RefreshCw className="h-4 w-4" />
                                            </Button>
                                        )}
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-medium text-slate-300">Enable Provider</span>
                                                    <span className="text-xs text-slate-500">Protocol: {provider.provider}</span>
                                                </div>
                                                <Switch 
                                                    checked={provider.enabled} 
                                                    onCheckedChange={(c) => updateProvider(key, 'enabled', c)} 
                                                />
                                            </div>
                                            
                                            <div className="space-y-1">
                                                <label className="text-xs text-slate-500 uppercase font-bold">Base URL</label>
                                                <Input 
                                                    value={provider.base_url || ""}
                                                    onChange={(e) => updateProvider(key, 'base_url', e.target.value)}
                                                    placeholder={provider.provider === "ollama" ? "http://localhost:11434" : "https://api.openai.com/v1"}
                                                    className="bg-charcoal-blue-950 border-charcoal-blue-700 font-mono text-xs"
                                                />
                                            </div>

                                            <div className="space-y-1">
                                                <label className="text-xs text-slate-500 uppercase font-bold">API Key</label>
                                                <div className="relative">
                                                    <Input 
                                                        type={showKeys[key] ? "text" : "password"}
                                                        value={provider.api_key || ""}
                                                        onChange={(e) => updateProvider(key, 'api_key', e.target.value)}
                                                        placeholder="sk-..."
                                                        className="bg-charcoal-blue-950 border-charcoal-blue-700 font-mono text-xs pr-10"
                                                    />
                                                    <button 
                                                        onClick={() => toggleKeyVisibility(key)}
                                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                                                    >
                                                        {showKeys[key] ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                                                    </button>
                                                </div>
                                                <p className="text-[10px] text-slate-600">
                                                    If left blank, uses system environment variable.
                                                </p>
                                            </div>

                                            <div>
                                                <p className="text-xs text-slate-500 mb-2 uppercase font-bold">Detected Models</p>
                                                <div className="flex flex-wrap gap-2">
                                                    {provider.available_models.length > 0 ? (
                                                        provider.available_models.map(m => (
                                                            <Badge key={m} variant="secondary" className="bg-charcoal-blue-800 text-slate-300">{m}</Badge>
                                                        ))
                                                    ) : (
                                                        <span className="text-xs text-slate-600 italic">No models detected/configured.</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>

                         <div className="mt-6 flex justify-center">
                             <Dialog open={isAddProviderOpen} onOpenChange={setIsAddProviderOpen}>
                                <DialogTrigger asChild>
                                    <Button variant="outline" className="border-dashed border-charcoal-blue-700 text-slate-400 hover:bg-charcoal-blue-800 hover:text-white">
                                        <Plus className="mr-2 h-4 w-4" /> Add Custom Provider
                                    </Button>
                                </DialogTrigger>
                                <DialogContent className="bg-charcoal-blue-900 border-charcoal-blue-700 text-slate-100">
                                    <DialogHeader>
                                        <DialogTitle>Add Custom Provider</DialogTitle>
                                        <DialogDescription className="text-slate-400">
                                            Register a new LLM provider.
                                        </DialogDescription>
                                    </DialogHeader>
                                    <div className="grid gap-4 py-4">
                                        <div className="grid gap-2">
                                            <Label>Provider ID (Unique)</Label>
                                            <Input 
                                                value={newProviderId}
                                                onChange={(e) => setNewProviderId(e.target.value)}
                                                placeholder="e.g. my-local-llm"
                                                className="bg-charcoal-blue-950 border-charcoal-blue-700"
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label>Protocol Type</Label>
                                            <Select value={newProviderType} onValueChange={setNewProviderType}>
                                                <SelectTrigger className="bg-charcoal-blue-950 border-charcoal-blue-700">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent className="bg-charcoal-blue-950 border-charcoal-blue-700 text-slate-200">
                                                    <SelectItem value="openai">OpenAI Compatible (Generic)</SelectItem>
                                                    <SelectItem value="openrouter">OpenRouter</SelectItem>
                                                    <SelectItem value="ollama">Ollama</SelectItem>
                                                    <SelectItem value="gemini">Google Gemini</SelectItem>
                                                    <SelectItem value="anthropic">Anthropic</SelectItem>
                                                    <SelectItem value="nvidia">NVIDIA NIM</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </div>
                                    <DialogFooter>
                                        <Button onClick={handleAddProvider} className="bg-baltic-blue-600 hover:bg-baltic-blue-500">
                                            Add Provider
                                        </Button>
                                    </DialogFooter>
                                </DialogContent>
                             </Dialog>
                         </div>
                    </TabsContent>
                </Tabs>
            </div>
    </div>
  );
}
