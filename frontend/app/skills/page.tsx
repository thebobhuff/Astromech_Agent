"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { FeatureInfoIcon } from "@/components/feature-info-icon";
import { Brain, Plus, Trash2, Edit, Save, RefreshCw } from "lucide-react";

type Skill = {
  name: string;
  description: string;
  instructions: string;
  metadata?: Record<string, any>;
};

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);

  // Form State
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formInst, setFormInst] = useState("");

  useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    try {
      const res = await fetch("/api/v1/skills/", { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to fetch skills");
      const data = await res.json();
      setSkills(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormName("");
    setFormDesc("");
    setFormInst("");
    setEditingSkill(null);
  };

  const handleOpenCreate = () => {
    resetForm();
    setIsDialogOpen(true);
  };

  const handleOpenEdit = (skill: Skill) => {
    setFormName(skill.name);
    setFormDesc(skill.description);
    setFormInst(skill.instructions);
    setEditingSkill(skill);
    setIsDialogOpen(true);
  };

  const handleSave = async () => {
    if (!formName || !formDesc) return;

    try {
      if (editingSkill) {
        // Edit Mode (Slug is inferred from original name for now, assuming name matches slug mostly. 
        // Real implementation might need to store slug separately if name != slug)
        // Creating slug same way backend does
        const slug = editingSkill.name.toLowerCase().replace(/ /g, "-");
        
        await fetch(`/api/v1/skills/${slug}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            description: formDesc,
            instructions: formInst,
            metadata: { ...editingSkill.metadata, name: formName } // Update display name
          })
        });
      } else {
        // Create Mode
        await fetch("/api/v1/skills/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: formName,
            description: formDesc,
            instructions: formInst
          })
        });
      }
      setIsDialogOpen(false);
      resetForm();
      fetchSkills();
    } catch (e) {
      console.error("Failed to save skill", e);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Are you sure you want to delete skill "${name}"? This cannot be undone.`)) return;
    
    // Convert to slug
    const slug = name.toLowerCase().replace(/ /g, "-");
    try {
      const res = await fetch(`/api/v1/skills/${slug}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed");
      fetchSkills();
    } catch (e) {
      console.error("Failed to delete", e);
    }
  };

  return (
    <div className="h-full flex flex-col bg-charcoal-blue-950 text-slate-100 p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto w-full space-y-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-baltic-blue-900/50 rounded-lg border border-baltic-blue-800">
              <Brain className="w-8 h-8 text-sky-reflection-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h1 className="text-3xl font-bold text-slate-100">Neural Skills</h1>
                <FeatureInfoIcon featureId="FE-003" featureName="Skill Manager" />
              </div>
              <p className="text-slate-400">Manage the agent's capabilities and tool definitions.</p>
            </div>
          </div>
          
          <Button onClick={handleOpenCreate} className="bg-baltic-blue-600 hover:bg-baltic-blue-500">
            <Plus className="w-4 h-4 mr-2" />
            New Skill
          </Button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 animate-spin text-slate-500" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {skills.map((skill) => (
              <Card key={skill.name} className="bg-charcoal-blue-900 border-charcoal-blue-800 text-slate-100 flex flex-col hover:border-sky-reflection-500/30 transition-all">
                <CardHeader>
                  <CardTitle className="text-lg text-sky-reflection-100">{skill.name}</CardTitle>
                  <CardDescription className="text-slate-400 line-clamp-2 h-10">
                    {skill.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-1 bg-charcoal-blue-950/30 mx-6 mb-4 p-3 rounded rounded-sm border border-charcoal-blue-800/50">
                  <div className="text-xs font-mono text-slate-500 line-clamp-6 whitespace-pre-wrap">
                    {skill.instructions}
                  </div>
                </CardContent>
                <CardFooter className="flex justify-between border-t border-charcoal-blue-800 pt-4">
                   <Button variant="ghost" size="sm" onClick={() => handleOpenEdit(skill)} className="text-slate-400 hover:text-white">
                     <Edit className="w-4 h-4 mr-2" /> Edit
                   </Button>
                   <Button variant="ghost" size="sm" onClick={() => handleDelete(skill.name)} className="text-red-400 hover:text-red-300 hover:bg-red-900/20">
                     <Trash2 className="w-4 h-4" />
                   </Button>
                </CardFooter>
              </Card>
            ))}
            
            {skills.length === 0 && (
                <div className="col-span-full text-center py-20 border-2 border-dashed border-charcoal-blue-800 rounded-lg">
                    <Brain className="w-12 h-12 mx-auto mb-4 text-charcoal-blue-700" />
                    <h3 className="text-lg font-medium text-slate-500">No skills equipped</h3>
                    <p className="text-slate-600 mb-4">Add a new skill to expand the agent's capabilities.</p>
                    <Button variant="outline" onClick={handleOpenCreate} className="border-charcoal-blue-700 hover:bg-charcoal-blue-800 text-slate-400">Create Skill</Button>
                </div>
            )}
          </div>
        )}

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="bg-charcoal-blue-900 border-charcoal-blue-700 text-slate-100 max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editingSkill ? 'Edit Skill' : 'Create New Skill'}</DialogTitle>
              <DialogDescription className="text-slate-400">
                Define the skill parameters and instructions for the LLM.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="s-name">Skill Name</Label>
                <Input 
                  id="s-name" 
                  value={formName} 
                  onChange={(e) => setFormName(e.target.value)}
                  disabled={!!editingSkill} // Disable renaming for now to keep slug simple
                  className="bg-charcoal-blue-950 border-charcoal-blue-700"
                  placeholder="e.g. Weather Search"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="s-desc">Description</Label>
                <Input 
                  id="s-desc" 
                  value={formDesc} 
                  onChange={(e) => setFormDesc(e.target.value)}
                  className="bg-charcoal-blue-950 border-charcoal-blue-700"
                  placeholder="Briefly describe what this skill does..."
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="s-inst">Instructions (Prompt context)</Label>
                <Textarea 
                  id="s-inst" 
                  value={formInst} 
                  onChange={(e) => setFormInst(e.target.value)}
                  className="bg-charcoal-blue-950 border-charcoal-blue-700 font-mono text-sm min-h-[200px]"
                  placeholder="Detailed instructions on how to use this skill, expected inputs, and format..."
                />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleSave} className="bg-baltic-blue-600 hover:bg-baltic-blue-500">
                <Save className="w-4 h-4 mr-2" />
                Save Skill
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

