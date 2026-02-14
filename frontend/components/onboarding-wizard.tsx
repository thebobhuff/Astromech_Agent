"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Send, Terminal } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Props {
  onComplete: () => void;
}

type Message = {
  role: "system" | "user";
  content: string;
};

export default function OnboardingWizard({ onComplete }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "system", content: "Initializing core systems..." },
    { role: "system", content: "Memory banks empty. Initiating programming sequence." },
    { role: "system", content: "Please execute the following directive: Who am I? (Define my name and core purpose)" }
  ]);
  const [input, setInput] = useState("");
  const [stage, setStage] = useState(0); // 0: Agent Identity, 1: User Identity, 2: User Name
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Collected Data
  const [agentIdentity, setAgentIdentity] = useState("");
  const [userIdentity, setUserIdentity] = useState("");
  const [userName, setUserName] = useState("");

  useEffect(() => {
    const scrollToBottom = () => {
        scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    };
    scrollToBottom();
    setTimeout(scrollToBottom, 100);
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = input;
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setInput("");
    setLoading(true);

    // Simulate thinking delay
    await new Promise(r => setTimeout(r, 600));

    try {
      if (stage === 0) {
        setAgentIdentity(userMsg);
        setMessages(prev => [...prev, { role: "system", content: "Identity parameter accepted. \n\nNext directive: Who are you? (Describe your role or profession)" }]);
        setStage(1);
      } else if (stage === 1) {
        setUserIdentity(userMsg);
        setMessages(prev => [...prev, { role: "system", content: "User profile updated. \n\nFinal directive: What do I call you? (Preferred name)" }]);
        setStage(2);
      } else if (stage === 2) {
        setUserName(userMsg);
        setMessages(prev => [...prev, { role: "system", content: "Writing to core memory... Please wait." }]);
        
        // Save Everything
        await saveConfiguration(agentIdentity, userIdentity, userMsg);
        
        onComplete();
      }
    } catch (e: any) {
      console.error(e);
      setMessages(prev => [...prev, { role: "system", content: "Error writing to memory. Please retry." }]);
    } finally {
      setLoading(false);
    }
  };

  const saveConfiguration = async (agentId: string, userId: string, name: string) => {
    // Construct MD content
    const coreMd = `# Agent Core Identity

${agentId}

## Personality
- Helpful, efficient, and logical.
- Observes the user's preferences carefully.
`;

    const userMd = `# User Profile

- **Name**: ${name}
- **Role**: ${userId}
- **Preferences**: 
    - (To be learned)
`;

    // Save CORE.md
    await fetch("/api/v1/system/files/core", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: coreMd })
    });

    // Save USER.md
    await fetch("/api/v1/system/files/user", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: userMd })
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-charcoal-blue-950 p-4 font-mono">
      <Card className="w-full max-w-2xl bg-charcoal-blue-900 border-charcoal-blue-800 text-green-500 shadow-2xl border-2">
        <CardHeader className="border-b border-charcoal-blue-800 bg-black/20">
          <CardTitle className="flex items-center gap-2 text-xl tracking-widest uppercase">
            <Terminal className="w-6 h-6 animate-pulse" />
            System_Boot_Sequence // Programming_Mode
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col h-[60vh] p-0">
            <ScrollArea className="flex-1">
                <div className="space-y-4 p-6">
                    {messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[85%] rounded p-3 text-sm ${
                                msg.role === 'user' 
                                ? 'bg-green-900/20 text-green-300 border border-green-800/50' 
                                : 'text-green-500' // Terminal style
                            }`}>
                                <span className="mr-2 opacity-50">{msg.role === 'system' ? '>' : '$'}</span>
                                <span className="whitespace-pre-wrap">{msg.content}</span>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="text-green-500 text-sm animate-pulse pl-3">
                           &gt; Processing...
                        </div>
                    )}
                    <div ref={scrollRef} />
                </div>
            </ScrollArea>
            
            <div className="p-4 border-t border-charcoal-blue-800 bg-black/20 flex gap-2">
                <div className="flex-1 relative">
                    <span className="absolute left-3 top-2.5 text-green-700">$</span>
                    <Input 
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        className="bg-charcoal-blue-950/50 border-charcoal-blue-800 text-green-400 pl-8 font-mono focus:border-green-800 focus:ring-green-900"
                        placeholder="_"
                        autoFocus
                    />
                </div>
                <Button onClick={handleSend} className="bg-green-900/30 hover:bg-green-900/50 text-green-400 border border-green-800/50">
                    <Send className="w-4 h-4" />
                </Button>
            </div>
        </CardContent>
      </Card>
    </div>
  );
}
