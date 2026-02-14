"use client";

import { useEffect, useState } from "react";
import { Save, RefreshCw, Layers, Key, Shield, Info } from "lucide-react";
import { FeatureInfoIcon } from "@/components/feature-info-icon";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

// Use Next.js API rewrite in dev and production-safe relative routing.
const API_BASE_URL = "/api/v1";

interface EnvSettings {
  [key: string]: string;
}

const INTEGRATION_GROUPS = {
  "LLM Providers": ["OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"],
  "Communication": [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USERS",
    "DISCORD_BOT_TOKEN",
    "WHATSAPP_API_TOKEN",
    "WHATSAPP_PHONE_ID",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
  ],
  "Email": ["EMAIL_SMTP_SERVER", "EMAIL_SMTP_PORT", "EMAIL_SENDER", "EMAIL_PASSWORD"],
};

export default function VaultPage() {
  const [settings, setSettings] = useState<EnvSettings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Fetch settings from the backend
  const fetchSettings = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE_URL}/system/env`);
      if (!response.ok) {
        throw new Error(`Failed to fetch settings: ${response.statusText}`);
      }
      const data = await response.json();
      setSettings(data);
    } catch (err: any) {
        setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleInputChange = (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE_URL}/system/env`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ settings }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to save settings");
      }
      
      const resData = await response.json();
      setMessage({ type: "success", text: resData.message || "Settings saved successfully." });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-charcoal-blue-950 text-slate-100 p-8 space-y-6 overflow-y-auto">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <h1 className="text-3xl font-bold tracking-tight">System Vault & Integrations</h1>
            <FeatureInfoIcon featureId="FE-008" featureName="Vault Configuration" />
          </div>
          <p className="text-slate-400">
            Secure storage for API keys, access tokens, and environment configuration.
          </p>
        </div>
        <div className="flex gap-2">
            <Button variant="outline" size="icon" onClick={fetchSettings} disabled={loading} className="bg-charcoal-blue-900 border-charcoal-blue-800 hover:bg-charcoal-blue-800 text-slate-300">
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button onClick={handleSave} disabled={loading || saving} className="bg-baltic-blue-600 hover:bg-baltic-blue-500 text-white border-0">
                <Save className="mr-2 h-4 w-4" />
                {saving ? "Saving..." : "Save Changes"}
            </Button>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-md border ${message.type === "success" ? "bg-green-500/10 border-green-500/30 text-green-400" : "bg-red-500/10 border-red-500/30 text-red-400"}`}>
          {message.text}
        </div>
      )}

      {loading && Object.keys(settings).length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-baltic-blue-500"></div>
        </div>
      ) : (
        <div className="space-y-8">
            {Object.entries(INTEGRATION_GROUPS).map(([groupName, keys]) => (
                <Card key={groupName} className="bg-charcoal-blue-900 border-charcoal-blue-800 text-slate-100">
                    <CardHeader>
                        <CardTitle className="text-xl font-medium flex items-center gap-2 text-sky-reflection-50">
                            {groupName === "LLM Providers" && <BrainIcon className="h-5 w-5 text-indigo-400" />}
                            {groupName === "Communication" && <MessageIcon className="h-5 w-5 text-green-400" />}
                            {groupName === "Email" && <MailIcon className="h-5 w-5 text-blue-400" />}
                            {groupName}
                        </CardTitle>
                        <CardDescription className="text-slate-400">
                            Configure access tokens and endpoints for {groupName.toLowerCase()}.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {keys.map((key) => {
                            const isSecret = key.includes("KEY") || key.includes("TOKEN") || key.includes("PASSWORD");
                            return (
                                <div key={key} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                                    <Label htmlFor={key} className="font-mono text-xs md:text-sm text-slate-400 break-all">
                                        {key}
                                    </Label>
                                    <div className="md:col-span-2">
                                        <div className="relative">
                                            <Input
                                                id={key}
                                                type={isSecret ? "password" : "text"}
                                                value={settings[key] || ""}
                                                onChange={(e) => handleInputChange(key, e.target.value)}
                                                className="font-mono text-sm bg-charcoal-blue-950 border-charcoal-blue-700 text-slate-200 focus:border-sky-reflection-500 placeholder:text-charcoal-blue-600"
                                                placeholder={`Not Set`}
                                            />
                                            {isSecret && (
                                                <Key className="absolute right-3 top-2.5 h-4 w-4 text-slate-600 opacity-50" />
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </CardContent>
                </Card>
            ))}
        </div>
      )}
    </div>
  );
}

// Simple Icons
function BrainIcon(props: React.ComponentProps<"svg">) {
    return (
      <svg
        {...props}
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
        <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
        <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
        <path d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
        <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />
        <path d="M3.477 12.505a4 4 0 0 0 .399-.4" />
        <path d="M20.124 12.105a4 4 0 0 0 .399.4" />
      </svg>
    )
}

function MessageIcon(props: React.ComponentProps<"svg">) {
    return (
        <svg
        {...props}
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        >
        <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
        </svg>
    )
}


function MailIcon(props: React.ComponentProps<"svg">) {
    return (
        <svg
        {...props}
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        >
        <rect width="20" height="16" x="2" y="4" rx="2" />
        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
        </svg>
    )
}

