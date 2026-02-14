"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { FeatureInfoIcon } from "@/components/feature-info-icon";
import { Send, Upload, X, Image as ImageIcon, TestTube, Loader2 } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

type Message = {
  role: "user" | "assistant";
  content: string;
  images?: string[];
  model?: string;
  metadata?: any;
};

export default function PlaygroundPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<string>("auto");
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const providers = [
    { value: "auto", label: "Auto (Router Decision)" },
    { value: "nvidia", label: "NVIDIA NIM" },
    { value: "kimi", label: "Moonshot Kimi" },
    { value: "openai", label: "OpenAI" },
    { value: "anthropic", label: "Anthropic" },
    { value: "gemini", label: "Google Gemini" },
    { value: "ollama", label: "Ollama (Local)" },
    { value: "openrouter", label: "OpenRouter" },
    { value: "deepseek", label: "DeepSeek" },
  ];

  const scrollToBottom = () => {
    if (scrollRef.current) {
        scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const reader = new FileReader();
      
      reader.onload = (event) => {
        if (event.target?.result && typeof event.target.result === 'string') {
           // We just store the base64 string directly
           // Ideally we would want to optimize this for larger files, but this works for testing.
           setAttachedImages(prev => [...prev, event.target!.result as string]);
        }
      };
      
      reader.readAsDataURL(file);
    }
    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeImage = (index: number) => {
    setAttachedImages(prev => prev.filter((_, i) => i !== index));
  };

  const sendMessage = async () => {
    if ((!input.trim() && attachedImages.length === 0) || loading) return;

    const userMsg: Message = { 
        role: "user", 
        content: input, 
        images: attachedImages.length > 0 ? attachedImages : undefined 
    };
    
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setInput("");
    const currentImages = attachedImages;
    setAttachedImages([]);

    try {
        const payload: any = {
            prompt: userMsg.content,
            session_id: "playground-" + Date.now(), // New session per chat or persistently? Let's use ephemeral for playground
            images: currentImages.length > 0 ? currentImages : undefined
        };

        if (selectedProvider !== "auto") {
            payload.model = selectedProvider + (selectedModel ? `/${selectedModel}` : "");
        }

        const res = await fetch("/api/v1/agent/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(await res.text());
        
        const data = await res.json();
        
        setMessages(prev => [...prev, {
            role: "assistant",
            content: data.response,
            metadata: data.metadata,
            model: data.metadata?.model_used
        }]);

    } catch (e: any) {
        toast({ title: "Error", description: e.message, variant: "destructive" });
        setMessages(prev => [...prev, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="flex h-full bg-charcoal-blue-950 text-slate-100 font-sans overflow-hidden">
      {/* Configuration Sidebar */}
      <div className="w-80 bg-charcoal-blue-900 border-r border-charcoal-blue-800 p-6 flex flex-col gap-6 overflow-y-auto">
        <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-sky-reflection-300 to-white bg-clip-text text-transparent flex items-center gap-2">
                <TestTube className="w-6 h-6 text-sky-reflection-400" />
                Playground
                <FeatureInfoIcon featureId="FE-015" featureName="Model Playground" />
            </h1>
            <p className="text-slate-400 text-sm mt-1">Test models and multimodal capabilities directly.</p>
        </div>

        <div className="space-y-4">
            <div className="space-y-2">
                <Label>Provider</Label>
                <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                    <SelectTrigger className="bg-charcoal-blue-950 border-charcoal-blue-700">
                        <SelectValue placeholder="Select Provider" />
                    </SelectTrigger>
                    <SelectContent className="bg-charcoal-blue-950 border-charcoal-blue-700 text-slate-200">
                        {providers.map(p => (
                            <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            
            {selectedProvider !== "auto" && (
                <div className="space-y-2">
                    <Label>Model Override (Optional)</Label>
                    <Input 
                        placeholder="e.g. gpt-4-turbo" 
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="bg-charcoal-blue-950 border-charcoal-blue-700"
                    />
                    <p className="text-xs text-slate-500">Leave blank to use provider default.</p>
                </div>
            )}
            
            <div className="pt-4 border-t border-charcoal-blue-800">
                <p className="text-xs text-slate-500">This playground uses a fresh session for each message to ensure clean state testing.</p>
            </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-charcoal-blue-950">
        <ScrollArea className="flex-1 p-6">
            <div className="max-w-3xl mx-auto space-y-6 pb-4">
                {messages.length === 0 && (
                    <div className="text-center py-20 text-slate-500">
                        <ImageIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <h3 className="text-lg font-medium">Ready to Test</h3>
                        <p>Select a provider, upload an image, or just chat.</p>
                    </div>
                )}
                
                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] rounded-lg p-4 ${
                            msg.role === 'user' 
                                ? 'bg-baltic-blue-900/40 border border-baltic-blue-800 text-sky-reflection-100' 
                                : 'bg-charcoal-blue-900 border border-charcoal-blue-800 text-slate-300 shadow-xl'
                        }`}>
                            {msg.model && (
                                <div className="text-[10px] text-sky-reflection-400 font-mono mb-2 bg-charcoal-blue-950/50 inline-block px-2 py-0.5 rounded">
                                    {msg.model}
                                </div>
                            )}
                            
                            {msg.images && msg.images.length > 0 && (
                                <div className="flex flex-wrap gap-2 mb-3">
                                    {msg.images.map((img, idx) => (
                                        <img key={idx} src={img} alt="Attached" className="max-w-[200px] max-h-[200px] rounded border border-charcoal-blue-700" />
                                    ))}
                                </div>
                            )}
                            
                            <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                            
                            {msg.metadata && msg.metadata.tools_used && msg.metadata.tools_used.length > 0 && (
                                <div className="mt-2 text-xs text-slate-500 pt-2 border-t border-charcoal-blue-800/50">
                                    Tools: {msg.metadata.tools_used.join(", ")}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                
                {loading && (
                     <div className="flex justify-start">
                         <div className="bg-charcoal-blue-900 border border-charcoal-blue-800 rounded-lg p-3 flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin text-sky-reflection-500" />
                            <span className="text-xs text-slate-400">Processing...</span>
                         </div>
                     </div>
                )}
                <div ref={scrollRef} />
            </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 bg-charcoal-blue-900/50 border-t border-charcoal-blue-800">
            <div className="max-w-3xl mx-auto space-y-3">
                {/* Image Attachments Preview */}
                {attachedImages.length > 0 && (
                    <div className="flex gap-2 overflow-x-auto py-2">
                        {attachedImages.map((img, i) => (
                            <div key={i} className="relative group shrink-0">
                                <img src={img} alt="Preview" className="h-16 w-16 object-cover rounded border border-charcoal-blue-700" />
                                <button 
                                    onClick={() => removeImage(i)}
                                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                    <X className="w-3 h-3" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                <div className="flex gap-2">
                     <Button 
                        variant="outline" 
                        size="icon" 
                        onClick={() => fileInputRef.current?.click()}
                        className="shrink-0 border-charcoal-blue-700 bg-charcoal-blue-950 hover:bg-charcoal-blue-800 text-slate-400 hover:text-sky-reflection-400"
                        title="Attach Image"
                    >
                        <Upload className="w-5 h-5" />
                     </Button>
                     <input 
                        type="file" 
                        ref={fileInputRef} 
                        className="hidden" 
                        accept="image/*" 
                        onChange={handleFileSelect}
                        // multiple // Could enable multiple
                     />
                     
                    <Textarea 
                         value={input}
                         onChange={(e) => setInput(e.target.value)}
                         onKeyDown={(e) => {
                           if(e.key === 'Enter' && !e.shiftKey) {
                             e.preventDefault();
                             sendMessage();
                           }
                         }}
                         placeholder="Enter your multimodal prompt..."
                         className="flex-1 bg-charcoal-blue-950 border-charcoal-blue-700 focus:border-sky-reflection-800 min-h-[50px] resize-none"
                    />
                    
                    <Button 
                        onClick={sendMessage} 
                        disabled={loading || (!input.trim() && attachedImages.length === 0)} 
                        className="h-auto px-6 bg-baltic-blue-600 hover:bg-baltic-blue-500 text-white"
                    >
                        <Send className="w-5 h-5" />
                    </Button>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}
