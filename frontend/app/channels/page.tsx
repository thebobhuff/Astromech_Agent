"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FeatureInfoIcon } from "@/components/feature-info-icon";
import { 
  MessageSquare, Mail, Phone, ExternalLink, 
  Settings, Save, RefreshCw, Radio, Hash, Send 
} from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";

type EnvSettings = Record<string, string>;

const CHANNEL_DEFS = [
  {
    id: "telegram",
    name: "Telegram",
    description: "Connect via Telegram Bot API.",
    icon: <Send className="w-8 h-8 text-blue-400" />,
    fields: [
      { key: "TELEGRAM_BOT_TOKEN", label: "Bot Token", type: "password" },
      { key: "TELEGRAM_ALLOWED_USERS", label: "Allowed User IDs (comma separated)", type: "text" }
    ],
    verifiedKey: "TELEGRAM_BOT_TOKEN"
  },
  {
    id: "discord",
    name: "Discord",
    description: "Integrate with a Discord Bot.",
    icon: <Hash className="w-8 h-8 text-indigo-400" />,
    fields: [
      { key: "DISCORD_BOT_TOKEN", label: "Bot Token", type: "password" }
    ],
    verifiedKey: "DISCORD_BOT_TOKEN"
  },
  {
    id: "whatsapp",
    name: "WhatsApp",
    description: "Messaging via WhatsApp Cloud API.",
    icon: <MessageSquare className="w-8 h-8 text-green-400" />,
    fields: [
      { key: "WHATSAPP_API_TOKEN", label: "API Token", type: "password" },
      { key: "WHATSAPP_PHONE_ID", label: "Phone Number ID", type: "text" }
    ],
    verifiedKey: "WHATSAPP_API_TOKEN"
  },
  {
    id: "email",
    name: "Email",
    description: "SMTP Server configuration for sending emails.",
    icon: <Mail className="w-8 h-8 text-yellow-400" />,
    fields: [
      { key: "EMAIL_SMTP_SERVER", label: "SMTP Server", type: "text" },
      { key: "EMAIL_SMTP_PORT", label: "SMTP Port", type: "number" },
      { key: "EMAIL_SENDER", label: "Sender Email", type: "email" },
      { key: "EMAIL_PASSWORD", label: "Password / App Password", type: "password" }
    ],
    verifiedKey: "EMAIL_SMTP_SERVER"
  },
  {
    id: "phone",
    name: "Phone / SMS",
    description: "Voice and SMS via Twilio.",
    icon: <Phone className="w-8 h-8 text-red-400" />,
    fields: [
      { key: "TWILIO_ACCOUNT_SID", label: "Account SID", type: "text" },
      { key: "TWILIO_AUTH_TOKEN", label: "Auth Token", type: "password" },
      { key: "TWILIO_PHONE_NUMBER", label: "Phone Number", type: "text" }
    ],
    verifiedKey: "TWILIO_ACCOUNT_SID"
  }
];

export default function ChannelsPage() {
  const [settings, setSettings] = useState<EnvSettings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [openDialog, setOpenDialog] = useState<string | null>(null);
  const [tempSettings, setTempSettings] = useState<EnvSettings>({});

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await fetch("/api/v1/system/env", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    } catch (e) {
      console.error("Failed to fetch settings", e);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (channelId: string) => {
    setTempSettings({ ...settings }); // Copy current settings to temp
    setOpenDialog(channelId);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Merge tempSettings into base settings (only the changed ones matter, but sending all is safer for consistency)
      // Actually we send only what's changed or all of temp?
      // Let's send all tracked fields to be safe.
      
      const payload = { settings: tempSettings };
      
      const res = await fetch("/api/v1/system/env", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        setSettings(tempSettings);
        setOpenDialog(null);
        // Maybe show toast?
      }
    } catch (e) {
      console.error("Failed to save", e);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: string, value: string) => {
    setTempSettings(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return <div className="p-8 text-slate-400">Loading channels...</div>;
  }

  return (
    <div className="h-full bg-charcoal-blue-950 text-slate-100 p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto w-full space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-baltic-blue-900/50 rounded-xl border border-baltic-blue-800 shadow-lg shadow-baltic-blue-900/20">
              <Radio className="w-8 h-8 text-sky-reflection-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Communication Grid</h1>
                <FeatureInfoIcon featureId="FE-007" featureName="Channels UI" />
              </div>
              <p className="text-slate-400">Manage external communication channels and integrations.</p>
            </div>
          </div>
          <Button variant="outline" onClick={fetchSettings} className="border-charcoal-blue-700 hover:bg-charcoal-blue-800 text-slate-400 hover:text-slate-100">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {CHANNEL_DEFS.map((channel) => {
             const isConfigured = !!settings[channel.verifiedKey] && settings[channel.verifiedKey].length > 5;
             
             return (
              <Card key={channel.id} className="bg-charcoal-blue-900 border-charcoal-blue-800 flex flex-col">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="p-2 bg-charcoal-blue-950 rounded-lg border border-charcoal-blue-800">
                      {channel.icon}
                    </div>
                    <Badge variant={isConfigured ? "default" : "outline"} className={isConfigured ? "bg-green-500/20 text-green-400 border-green-500/50" : "text-slate-500 border-slate-700"}>
                      {isConfigured ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <CardTitle className="mt-4 text-slate-100">{channel.name}</CardTitle>
                  <CardDescription className="text-slate-400">{channel.description}</CardDescription>
                </CardHeader>
                <CardContent className="flex-1">
                   {/* Status details or mini-stats could go here */}
                   <div className="text-sm text-slate-500">
                     {isConfigured 
                       ? "Credentials configured." 
                       : "Not configured. Agent cannot use this channel."}
                   </div>
                </CardContent>
                <CardFooter className="bg-charcoal-blue-950/30 border-t border-charcoal-blue-800 p-4">
                  <Dialog open={openDialog === channel.id} onOpenChange={(open) => !open && setOpenDialog(null)}>
                    <DialogTrigger asChild>
                      <Button 
                        variant="secondary" 
                        className="w-full bg-charcoal-blue-800 hover:bg-charcoal-blue-700 text-slate-200"
                        onClick={() => handleEdit(channel.id)}
                      >
                        <Settings className="w-4 h-4 mr-2" /> Configure
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-charcoal-blue-900 border-charcoal-blue-800 text-slate-100 max-w-md">
                      <DialogHeader>
                        <DialogTitle>Configure {channel.name}</DialogTitle>
                        <DialogDescription className="text-slate-400">
                          Enter your API credentials below. These will be saved to your local environment.
                        </DialogDescription>
                      </DialogHeader>
                      
                      <div className="space-y-4 py-4">
                        {channel.fields.map((field) => (
                          <div key={field.key} className="space-y-2">
                            <Label htmlFor={field.key} className="text-slate-300">{field.label}</Label>
                            <Input
                              id={field.key}
                              type={field.type}
                              value={tempSettings[field.key] || ""}
                              onChange={(e) => handleChange(field.key, e.target.value)}
                              className="bg-charcoal-blue-950 border-charcoal-blue-700 focus:border-baltic-blue-500"
                              placeholder={field.type === "password" ? "••••••••" : ""}
                            />
                          </div>
                        ))}
                      </div>

                      <DialogFooter>
                         <div className="flex justify-between w-full items-center">
                            <div className="text-xs text-yellow-500/80">Restart required to apply changes.</div>
                            <Button onClick={handleSave} disabled={saving} className="bg-baltic-blue-600 hover:bg-baltic-blue-500">
                              {saving ? "Saving..." : "Save Configuration"}
                            </Button>
                         </div>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </CardFooter>
              </Card>
             );
          })}
        </div>

      </div>
    </div>
  );
}
