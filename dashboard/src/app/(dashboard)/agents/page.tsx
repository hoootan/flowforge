'use client';

import { useEffect, useState } from 'react';
import { api, type AgentType } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Bot, Plus, Circle, Trash2, Sparkles, X } from 'lucide-react';
import { toast } from 'sonner';
import { type SkillType } from '@/lib/api';

const statusColors: Record<string, string> = {
  online: 'bg-green-500',
  idle: 'bg-yellow-500',
  busy: 'bg-blue-500',
  offline: 'bg-gray-400',
};

const statusBadge: Record<string, string> = {
  online: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  idle: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  busy: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  offline: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newAgent, setNewAgent] = useState({ name: '', description: '', model: '' });
  const [allSkills, setAllSkills] = useState<SkillType[]>([]);
  const [skillPickerAgent, setSkillPickerAgent] = useState<AgentType | null>(null);
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [pendingSkills, setPendingSkills] = useState<string[]>([]);

  const fetchAgents = async () => {
    setLoading(true);
    const data = await api.getAgents();
    setAgents(data.agents);
    setLoading(false);
  };

  const fetchSkills = async () => {
    const data = await api.getSkills();
    setAllSkills(data.skills);
  };

  useEffect(() => { fetchAgents(); fetchSkills(); }, []);

  const handleCreate = async () => {
    if (!newAgent.name.trim()) return;
    const agent = await api.createAgent({
      name: newAgent.name,
      description: newAgent.description || undefined,
      model: newAgent.model || undefined,
    });
    if (agent) {
      toast.success(`Agent "${agent.name}" created`);
      setShowCreate(false);
      setNewAgent({ name: '', description: '', model: '' });
      fetchAgents();
    } else {
      toast.error('Failed to create agent');
    }
  };

  const handleDelete = async (agentId: string, name: string) => {
    if (!confirm(`Delete agent "${name}"?`)) return;
    const success = await api.deleteAgent(agentId);
    if (success) {
      toast.success(`Agent "${name}" deleted`);
      fetchAgents();
    }
  };

  const handleOpenSkillPicker = (agent: AgentType) => {
    setSkillPickerAgent(agent);
    setPendingSkills(agent.enabled_skills || []);
    setSkillPickerOpen(true);
  };

  const handleToggleSkill = (skillId: string) => {
    setPendingSkills(prev =>
      prev.includes(skillId) ? prev.filter(id => id !== skillId) : [...prev, skillId]
    );
  };

  const handleSaveSkills = async () => {
    if (!skillPickerAgent) return;
    const result = await api.setAgentSkills(skillPickerAgent.id, pendingSkills);
    if (result) {
      toast.success(`Updated skills for "${skillPickerAgent.name}"`);
      setSkillPickerOpen(false);
      fetchAgents();
    } else {
      toast.error('Failed to update skills');
    }
  };

  const onlineCount = agents.filter(a => a.status !== 'offline').length;
  const totalRuns = agents.reduce((sum, a) => sum + ((a.stats as any)?.total_runs || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Agents</h2>
          <p className="text-muted-foreground">
            AI team members that can be assigned tasks and execute workflows
          </p>
        </div>
        <Dialog open={showCreate} onOpenChange={setShowCreate}>
          <DialogTrigger asChild>
            <Button><Plus className="mr-2 h-4 w-4" /> New Agent</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Agent</DialogTitle>
              <DialogDescription>
                Add a new AI agent to your team
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., Code Reviewer, Deploy Bot"
                  value={newAgent.name}
                  onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="What does this agent do?"
                  value={newAgent.description}
                  onChange={(e) => setNewAgent({ ...newAgent, description: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Default Model</Label>
                <Input
                  id="model"
                  placeholder="e.g., claude-sonnet-4-6"
                  value={newAgent.model}
                  onChange={(e) => setNewAgent({ ...newAgent, model: e.target.value })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button onClick={handleCreate}>Create Agent</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats row */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Agents</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? <Skeleton className="h-8 w-12" /> : agents.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Online</CardTitle>
            <Circle className="h-4 w-4 text-green-500 fill-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? <Skeleton className="h-8 w-12" /> : onlineCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? <Skeleton className="h-8 w-12" /> : totalRuns}</div>
          </CardContent>
        </Card>
      </div>

      {/* Agent cards */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map(i => (
            <Card key={i}><CardContent className="p-6"><Skeleton className="h-24" /></CardContent></Card>
          ))}
        </div>
      ) : agents.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Bot className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold">No agents yet</h3>
            <p className="text-muted-foreground text-sm mt-1">Create your first AI agent to get started</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map(agent => (
            <Card key={agent.id} className="relative group">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <Bot className="h-5 w-5 text-primary" />
                      </div>
                      <div className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background ${statusColors[agent.status] || statusColors.offline}`} />
                    </div>
                    <div>
                      <CardTitle className="text-base">{agent.name}</CardTitle>
                      <CardDescription className="text-xs">{agent.slug}</CardDescription>
                    </div>
                  </div>
                  <Badge className={statusBadge[agent.status] || statusBadge.offline} variant="secondary">
                    {agent.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {agent.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">{agent.description}</p>
                )}
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  {agent.model && <span className="font-mono">{agent.model}</span>}
                  {agent.is_active ? (
                    <Badge variant="outline" className="text-xs">Active</Badge>
                  ) : (
                    <Badge variant="destructive" className="text-xs">Inactive</Badge>
                  )}
                </div>
                {/* Enabled Skills */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                      <Sparkles className="h-3 w-3" /> Skills ({agent.enabled_skills?.length || 0})
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs px-2"
                      onClick={() => handleOpenSkillPicker(agent)}
                    >
                      Manage
                    </Button>
                  </div>
                  {agent.enabled_skills && agent.enabled_skills.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {agent.enabled_skills.slice(0, 3).map(skillId => {
                        const skill = allSkills.find(s => s.id === skillId);
                        return (
                          <Badge key={skillId} variant="secondary" className="text-xs gap-1">
                            {skill?.icon || '🔧'} {skill?.name || skillId.slice(0, 8)}
                          </Badge>
                        );
                      })}
                      {agent.enabled_skills.length > 3 && (
                        <Badge variant="outline" className="text-xs">+{agent.enabled_skills.length - 3}</Badge>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground/60">No skills enabled</p>
                  )}
                </div>
                <div className="flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive"
                    onClick={() => handleDelete(agent.id, agent.name)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Skill Picker Dialog */}
      <Dialog open={skillPickerOpen} onOpenChange={setSkillPickerOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Manage Skills for {skillPickerAgent?.name}</DialogTitle>
            <DialogDescription>
              Toggle skills on/off. Enabled skills inject their knowledge into the agent&apos;s context at runtime.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 max-h-[400px] overflow-y-auto py-2 scrollbar-none">
            {allSkills.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">No skills available. Import skills from the Marketplace first.</p>
            ) : (
              allSkills.map(skill => {
                const isEnabled = pendingSkills.includes(skill.id);
                return (
                  <div
                    key={skill.id}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      isEnabled ? 'bg-primary/5 border-primary/30' : 'hover:bg-muted/50'
                    }`}
                    onClick={() => handleToggleSkill(skill.id)}
                  >
                    <span className="text-lg shrink-0">{skill.icon || '🔧'}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{skill.name}</span>
                        {skill.source !== 'local' && (
                          <Badge variant="secondary" className="text-xs">{skill.source === 'skills_sh' ? 'skills.sh' : 'GitHub'}</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{skill.description}</p>
                    </div>
                    <div className={`h-5 w-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                      isEnabled ? 'bg-primary border-primary text-primary-foreground' : 'border-muted-foreground/30'
                    }`}>
                      {isEnabled && <span className="text-xs">✓</span>}
                    </div>
                  </div>
                );
              })
            )}
          </div>
          <DialogFooter>
            <div className="flex items-center justify-between w-full">
              <span className="text-xs text-muted-foreground">{pendingSkills.length} skill(s) enabled</span>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setSkillPickerOpen(false)}>Cancel</Button>
                <Button onClick={handleSaveSkills}>Save</Button>
              </div>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
