'use client';

import { useEffect, useState, useCallback } from 'react';
import { api, type SkillType, type MarketplaceSearchResult, type SkillPreview as SkillPreviewType } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Sparkles, Search, ArrowRight, Hash, Plus, Globe, Download,
  RefreshCw, ExternalLink, BookOpen, Github,
} from 'lucide-react';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';

// ── Source badge component ─────────────────────────────────────

function SourceBadge({ source }: { source: string }) {
  if (source === 'local') return null;
  const config = {
    skills_sh: { label: 'skills.sh', icon: Globe, className: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300' },
    github: { label: 'GitHub', icon: Github, className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' },
  }[source] ?? { label: source, icon: Globe, className: '' };
  const Icon = config.icon;
  return (
    <Badge variant="secondary" className={`text-xs gap-1 ${config.className}`}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}

// ── Marketplace result card ────────────────────────────────────

function MarketplaceCard({
  result,
  onPreview,
  importing,
}: {
  result: MarketplaceSearchResult;
  onPreview: (result: MarketplaceSearchResult) => void;
  importing: boolean;
}) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base">{result.name}</CardTitle>
            <CardDescription className="text-xs font-mono mt-1">{result.repo}</CardDescription>
          </div>
          <SourceBadge source={result.source} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground line-clamp-2">{result.description}</p>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Download className="h-3 w-3" />
            {result.install_count.toLocaleString()} installs
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onPreview(result)}
            disabled={importing}
          >
            <BookOpen className="mr-1 h-3 w-3" />
            Preview & Import
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Skill preview dialog ───────────────────────────────────────

function SkillPreviewDialog({
  open,
  onOpenChange,
  result,
  onImport,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: MarketplaceSearchResult | null;
  onImport: (result: MarketplaceSearchResult, category?: string, tags?: string[]) => void;
}) {
  const [preview, setPreview] = useState<SkillPreviewType | null>(null);
  const [loading, setLoading] = useState(false);
  const [importCategory, setImportCategory] = useState('');
  const [importTags, setImportTags] = useState('');
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    if (open && result) {
      setLoading(true);
      setPreview(null);
      api.previewSkill(result.repo).then(data => {
        setPreview(data);
        setLoading(false);
      });
    }
  }, [open, result]);

  const handleImport = async () => {
    if (!result) return;
    setImporting(true);
    const tags = importTags ? importTags.split(',').map(t => t.trim()).filter(Boolean) : [];
    await onImport(result, importCategory || undefined, tags.length > 0 ? tags : undefined);
    setImporting(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {result?.name}
            <SourceBadge source={result?.source ?? ''} />
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2">
            <span className="font-mono text-xs">{result?.repo}</span>
            {result?.install_count && (
              <>
                <span className="text-border">|</span>
                <span>{result.install_count.toLocaleString()} installs</span>
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        {/* SKILL.md preview */}
        <ScrollArea className="flex-1 min-h-0 max-h-[400px] border rounded-lg p-4">
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-full" />
            </div>
          ) : preview ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{preview.body || preview.raw_content}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Failed to load preview
            </p>
          )}
        </ScrollArea>

        {/* Import options */}
        <div className="grid grid-cols-2 gap-3 pt-2">
          <div className="space-y-1">
            <Label className="text-xs">Category (optional)</Label>
            <Input
              placeholder="e.g., frontend"
              value={importCategory}
              onChange={e => setImportCategory(e.target.value)}
              className="h-8 text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Tags (optional, comma-separated)</Label>
            <Input
              placeholder="e.g., react, typescript"
              value={importTags}
              onChange={e => setImportTags(e.target.value)}
              className="h-8 text-sm"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleImport} disabled={importing || loading}>
            {importing ? 'Importing...' : 'Import Skill'}
            {!importing && <Download className="ml-2 h-4 w-4" />}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Main Page ──────────────────────────────────────────────────

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillType[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState('my-skills');

  // Marketplace state
  const [mpQuery, setMpQuery] = useState('');
  const [mpResults, setMpResults] = useState<MarketplaceSearchResult[]>([]);
  const [mpSearching, setMpSearching] = useState(false);
  const [mpImporting, setMpImporting] = useState(false);

  // Preview dialog
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewResult, setPreviewResult] = useState<MarketplaceSearchResult | null>(null);

  // Create dialog
  const [showCreate, setShowCreate] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [newSkill, setNewSkill] = useState({ name: '', description: '', category: '', icon: '', tags: '' });

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    const data = await api.getSkills({ search: search || undefined });
    setSkills(data.skills);
    setLoading(false);
  }, [search]);

  useEffect(() => { fetchSkills(); }, [fetchSkills]);

  const handleSearchLocal = () => { fetchSkills(); };

  const handleSearchMarketplace = async () => {
    if (!mpQuery.trim()) return;
    setMpSearching(true);
    const data = await api.searchMarketplace({ q: mpQuery, limit: 12 });
    setMpResults(data.results);
    setMpSearching(false);
  };

  const handlePreview = (result: MarketplaceSearchResult) => {
    setPreviewResult(result);
    setPreviewOpen(true);
  };

  const handleImport = async (result: MarketplaceSearchResult, category?: string, tags?: string[]) => {
    setMpImporting(true);
    const imported = await api.importSkill({
      repo: result.repo,
      source: result.source,
      external_id: result.external_id,
      category,
      tags,
    });
    setMpImporting(false);
    if (imported) {
      toast.success(`Imported "${imported.name}" from ${result.source}`);
      setActiveTab('my-skills');
      fetchSkills();
    } else {
      toast.error('Failed to import skill');
    }
  };

  const handleRefresh = async (skillId: string, name: string) => {
    const updated = await api.refreshSkill(skillId);
    if (updated) {
      toast.success(`"${name}" refreshed to v${updated.version}`);
      fetchSkills();
    } else {
      toast.error('Failed to refresh skill');
    }
  };

  const handleUseSkill = async (skillId: string, skillName: string) => {
    const result = await api.useSkill(skillId);
    if (result) {
      toast.success(`Skill "${skillName}" configuration ready. Use it to create a new function.`);
    }
  };

  const handleCreate = async () => {
    if (!newSkill.name.trim()) return;
    setCreateLoading(true);
    const result = await api.createSkill({
      name: newSkill.name,
      description: newSkill.description || undefined,
      category: newSkill.category || undefined,
      icon: newSkill.icon || undefined,
      tags: newSkill.tags ? newSkill.tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
    });
    setCreateLoading(false);
    if (result) {
      toast.success(`Skill "${result.name}" created`);
      setShowCreate(false);
      setNewSkill({ name: '', description: '', category: '', icon: '', tags: '' });
      fetchSkills();
    } else {
      toast.error('Failed to create skill');
    }
  };

  const categories = [...new Set(skills.map(s => s.category).filter(Boolean))];
  const localSkills = skills.filter(s => s.source === 'local');
  const importedSkills = skills.filter(s => s.source !== 'local');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Skill Library</h2>
          <p className="text-muted-foreground">
            Reusable templates &amp; imported knowledge for your agents
          </p>
        </div>
        <Dialog open={showCreate} onOpenChange={setShowCreate}>
          <DialogTrigger asChild>
            <Button><Plus className="mr-2 h-4 w-4" /> New Skill</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Skill Template</DialogTitle>
              <DialogDescription>
                Create a new reusable skill from scratch, or use &quot;Save as Skill&quot; from the Functions page.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input placeholder="e.g., Code Review" value={newSkill.name} onChange={e => setNewSkill({ ...newSkill, name: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea placeholder="What does this skill do?" value={newSkill.description} onChange={e => setNewSkill({ ...newSkill, description: e.target.value })} rows={3} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Input placeholder="e.g., development" value={newSkill.category} onChange={e => setNewSkill({ ...newSkill, category: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Tags</Label>
                  <Input placeholder="comma-separated" value={newSkill.tags} onChange={e => setNewSkill({ ...newSkill, tags: e.target.value })} />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={createLoading || !newSkill.name.trim()}>
                {createLoading ? 'Creating...' : 'Create'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Tabs: My Skills | Marketplace */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="my-skills">
            My Skills
            <Badge variant="secondary" className="ml-2 text-xs">{skills.length}</Badge>
          </TabsTrigger>
          <TabsTrigger value="marketplace">
            <Globe className="mr-1 h-3.5 w-3.5" />
            Marketplace
          </TabsTrigger>
        </TabsList>

        {/* ── My Skills Tab ─────────────────────────────────────── */}
        <TabsContent value="my-skills" className="space-y-4 mt-4">
          {/* Search + filters */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search skills..."
                className="pl-9"
                value={search}
                onChange={e => setSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearchLocal()}
              />
            </div>
          </div>

          {categories.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {categories.map(cat => (
                <Badge key={cat} variant="outline" className="cursor-pointer hover:bg-accent">
                  <Hash className="h-3 w-3 mr-1" />{cat}
                </Badge>
              ))}
            </div>
          )}

          {/* Imported skills section */}
          {importedSkills.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Globe className="h-4 w-4" /> Imported from Marketplace ({importedSkills.length})
              </h3>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {importedSkills.map(skill => (
                  <Card key={skill.id} className="group hover:shadow-md transition-shadow border-dashed">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{skill.icon || '📦'}</span>
                          <div>
                            <CardTitle className="text-base">{skill.name}</CardTitle>
                            <CardDescription className="text-xs font-mono">{skill.source_metadata?.repo}</CardDescription>
                          </div>
                        </div>
                        <SourceBadge source={skill.source} />
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {skill.description && <p className="text-sm text-muted-foreground line-clamp-2">{skill.description}</p>}
                      <div className="flex items-center justify-between">
                        <div className="flex flex-wrap gap-1">
                          {(skill.tags || []).slice(0, 3).map(tag => (
                            <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                          ))}
                        </div>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleRefresh(skill.id, skill.name)}>
                          <RefreshCw className="h-3 w-3" />
                        </Button>
                      </div>
                      <Button variant="outline" size="sm" className="w-full" onClick={() => handleUseSkill(skill.id, skill.name)}>
                        Use Skill <ArrowRight className="ml-2 h-3 w-3" />
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Local skills section */}
          {loading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map(i => <Card key={i}><CardContent className="p-6"><Skeleton className="h-28" /></CardContent></Card>)}
            </div>
          ) : localSkills.length === 0 && importedSkills.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold">No skills yet</h3>
                <p className="text-muted-foreground text-sm mt-1 text-center max-w-md">
                  Create a skill from scratch, use <strong>Save as Skill</strong> from Functions, or browse the <strong>Marketplace</strong> tab to import community skills.
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              {localSkills.length > 0 && importedSkills.length > 0 && (
                <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Sparkles className="h-4 w-4" /> Local Skills ({localSkills.length})
                </h3>
              )}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {localSkills.map(skill => (
                  <Card key={skill.id} className="group hover:shadow-md transition-shadow">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{skill.icon || '🔧'}</span>
                          <div>
                            <CardTitle className="text-base">{skill.name}</CardTitle>
                            {skill.category && <CardDescription className="text-xs">{skill.category}</CardDescription>}
                          </div>
                        </div>
                        <Badge variant="secondary" className="text-xs">v{skill.version}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {skill.description && <p className="text-sm text-muted-foreground line-clamp-2">{skill.description}</p>}
                      <div className="flex items-center justify-between">
                        <div className="flex flex-wrap gap-1">
                          {(skill.tags || []).slice(0, 3).map(tag => (
                            <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                          ))}
                        </div>
                        <span className="text-xs text-muted-foreground">{skill.usage_count} uses</span>
                      </div>
                      <Button variant="outline" size="sm" className="w-full group-hover:bg-primary group-hover:text-primary-foreground transition-colors" onClick={() => handleUseSkill(skill.id, skill.name)}>
                        Use Skill <ArrowRight className="ml-2 h-3 w-3" />
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </TabsContent>

        {/* ── Marketplace Tab ───────────────────────────────────── */}
        <TabsContent value="marketplace" className="space-y-4 mt-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search skills.sh marketplace..."
                className="pl-9"
                value={mpQuery}
                onChange={e => setMpQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearchMarketplace()}
              />
            </div>
            <Button onClick={handleSearchMarketplace} disabled={mpSearching || !mpQuery.trim()}>
              {mpSearching ? 'Searching...' : 'Search'}
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            Search the <a href="https://skills.sh" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">skills.sh</a> marketplace for community-built agent skills. Import them to use as knowledge for your FlowForge agents.
          </p>

          {mpSearching ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map(i => <Card key={i}><CardContent className="p-6"><Skeleton className="h-28" /></CardContent></Card>)}
            </div>
          ) : mpResults.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {mpResults.map(result => (
                <MarketplaceCard
                  key={result.external_id}
                  result={result}
                  onPreview={handlePreview}
                  importing={mpImporting}
                />
              ))}
            </div>
          ) : mpQuery ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Search className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold">No results</h3>
                <p className="text-muted-foreground text-sm mt-1">Try a different search term</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Globe className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold">Discover Skills</h3>
                <p className="text-muted-foreground text-sm mt-1 text-center max-w-md">
                  Search for agent skills like &quot;react&quot;, &quot;docker&quot;, &quot;python&quot;, or &quot;architecture&quot; to find community-built knowledge for your agents.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Preview + Import dialog */}
      <SkillPreviewDialog
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        result={previewResult}
        onImport={handleImport}
      />
    </div>
  );
}
