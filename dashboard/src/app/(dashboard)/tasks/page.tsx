'use client';

import { useEffect, useState, useCallback } from 'react';
import { api, type TaskType, type TaskBoardResponse, type AgentType, type CommentType } from '@/lib/api';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Card, CardContent } from '@/components/ui/card';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, KanbanSquare, List, Bot, User, MessageSquare, Send, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const statusConfig: Record<string, { label: string; color: string }> = {
  todo: { label: 'To Do', color: 'bg-slate-100 dark:bg-slate-800' },
  in_progress: { label: 'In Progress', color: 'bg-blue-50 dark:bg-blue-950' },
  in_review: { label: 'In Review', color: 'bg-purple-50 dark:bg-purple-950' },
  done: { label: 'Done', color: 'bg-green-50 dark:bg-green-950' },
  blocked: { label: 'Blocked', color: 'bg-red-50 dark:bg-red-950' },
  cancelled: { label: 'Cancelled', color: 'bg-gray-50 dark:bg-gray-950' },
};

const priorityColors: Record<string, string> = {
  urgent: 'text-red-600 bg-red-50 dark:bg-red-950',
  high: 'text-orange-600 bg-orange-50 dark:bg-orange-950',
  medium: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-950',
  low: 'text-blue-600 bg-blue-50 dark:bg-blue-950',
  none: 'text-gray-400',
};

// Kanban columns to show (subset for board)
const boardColumns = ['todo', 'in_progress', 'in_review', 'done'];

function TaskCard({ task, onClick }: { task: TaskType; onClick: () => void }) {
  return (
    <div onClick={onClick} className="cursor-pointer bg-background border rounded-lg p-3 shadow-sm hover:shadow-md transition-shadow space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-muted-foreground">{task.identifier}</span>
            {task.priority !== 'none' && (
              <Badge variant="secondary" className={`text-xs ${priorityColors[task.priority]}`}>
                {task.priority}
              </Badge>
            )}
          </div>
          <p className="text-sm font-medium leading-tight line-clamp-2">{task.title}</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {task.assignee_agent && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Bot className="h-3 w-3" />
              <span>{task.assignee_agent.name}</span>
            </div>
          )}
          {task.assignee_user && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <User className="h-3 w-3" />
              <span>{task.assignee_user.name}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          {task.comments_count > 0 && (
            <span className="flex items-center gap-0.5">
              <MessageSquare className="h-3 w-3" />
              {task.comments_count}
            </span>
          )}
          {task.sub_tasks_count > 0 && (
            <span className="text-xs">{task.sub_tasks_count} sub</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TasksPage() {
  const [board, setBoard] = useState<TaskBoardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'board' | 'list'>('board');
  const [showCreate, setShowCreate] = useState(false);
  const [newTask, setNewTask] = useState({ title: '', description: '', priority: 'none', assignee_agent_id: '' });
  const [agents, setAgents] = useState<AgentType[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskType | null>(null);
  const [taskComments, setTaskComments] = useState<CommentType[]>([]);
  const [newComment, setNewComment] = useState('');
  const [functions, setFunctions] = useState<{ id: string; function_id: string }[]>([]);

  const fetchBoard = useCallback(async () => {
    setLoading(true);
    const data = await api.getTaskBoard();
    setBoard(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchBoard();
    api.getAgents().then((data) => setAgents(data.agents));
    api.getFunctions().then((data) => setFunctions(data.functions));
  }, [fetchBoard]);

  const openTaskDetail = async (task: TaskType) => {
    setSelectedTask(task);
    const data = await api.getComments({ task_id: task.id });
    setTaskComments(data.comments);
  };

  const handleUpdateTask = async (field: string, value: string) => {
    if (!selectedTask) return;
    const updated = await api.updateTask(selectedTask.id, { [field]: value || null });
    if (updated) {
      setSelectedTask(updated);
      fetchBoard();
    }
  };

  const handleAddComment = async () => {
    if (!selectedTask || !newComment.trim()) return;
    const comment = await api.createComment({ task_id: selectedTask.id, content: newComment });
    if (comment) {
      setTaskComments([...taskComments, comment]);
      setNewComment('');
    }
  };

  const handleDeleteTask = async () => {
    if (!selectedTask) return;
    if (await api.deleteTask(selectedTask.id)) {
      setSelectedTask(null);
      fetchBoard();
      toast.success('Task deleted');
    }
  };

  const handleCreate = async () => {
    if (!newTask.title.trim()) return;
    const task = await api.createTask({
      title: newTask.title,
      description: newTask.description || undefined,
      priority: newTask.priority,
      assignee_agent_id: newTask.assignee_agent_id || undefined,
    });
    if (task) {
      toast.success(`Task ${task.identifier} created`);
      setShowCreate(false);
      setNewTask({ title: '', description: '', priority: 'none', assignee_agent_id: '' });
      fetchBoard();
    } else {
      toast.error('Failed to create task');
    }
  };

  const totalTasks = board?.total || 0;
  const doneTasks = board?.columns?.done?.length || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Task Board</h2>
          <p className="text-muted-foreground">
            {totalTasks} tasks &middot; {doneTasks} done
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center border rounded-md">
            <Button
              variant={viewMode === 'board' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('board')}
            >
              <KanbanSquare className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
          <Dialog open={showCreate} onOpenChange={setShowCreate}>
            <DialogTrigger asChild>
              <Button><Plus className="mr-2 h-4 w-4" /> New Task</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Task</DialogTitle>
                <DialogDescription>Add a new task to the board</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input
                    placeholder="What needs to be done?"
                    value={newTask.title}
                    onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    placeholder="Add details..."
                    value={newTask.description}
                    onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Priority</Label>
                  <Select value={newTask.priority} onValueChange={(v) => setNewTask({ ...newTask, priority: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {agents.length > 0 && (
                  <div className="space-y-2">
                    <Label>Assign to Agent</Label>
                    <Select
                      value={newTask.assignee_agent_id}
                      onValueChange={(v) => setNewTask({ ...newTask, assignee_agent_id: v === '_none' ? '' : v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Unassigned" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_none">Unassigned</SelectItem>
                        {agents.map((agent) => (
                          <SelectItem key={agent.id} value={agent.id}>
                            <span className="flex items-center gap-2">
                              <Bot className="h-3 w-3" />
                              {agent.name}
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
                <Button onClick={handleCreate}>Create</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          ))}
        </div>
      ) : viewMode === 'board' ? (
        <div className="grid grid-cols-4 gap-4 min-h-[60vh]">
          {boardColumns.map(col => {
            const tasks = board?.columns?.[col] || [];
            const config = statusConfig[col];
            return (
              <div key={col} className={`rounded-lg p-3 ${config.color}`}>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold">{config.label}</h3>
                  <Badge variant="secondary" className="text-xs">{tasks.length}</Badge>
                </div>
                <div className="space-y-2">
                  {tasks.map(task => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onClick={() => openTaskDetail(task)}
                    />
                  ))}
                  {tasks.length === 0 && (
                    <div className="text-center py-8 text-xs text-muted-foreground">
                      No tasks
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {Object.entries(board?.columns || {}).flatMap(([status, tasks]) =>
                (tasks as TaskType[]).map(task => (
                  <div key={task.id} className="flex items-center gap-4 px-4 py-3 hover:bg-muted/50 cursor-pointer" onClick={() => openTaskDetail(task)}>
                    <span className="text-xs font-mono text-muted-foreground w-16">{task.identifier}</span>
                    <Badge variant="outline" className="text-xs w-24 justify-center">
                      {statusConfig[task.status]?.label || task.status}
                    </Badge>
                    {task.priority !== 'none' && (
                      <Badge variant="secondary" className={`text-xs ${priorityColors[task.priority]}`}>
                        {task.priority}
                      </Badge>
                    )}
                    <span className="flex-1 text-sm truncate">{task.title}</span>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      {task.assignee_agent && <><Bot className="h-3 w-3" />{task.assignee_agent.name}</>}
                      {task.assignee_user && <><User className="h-3 w-3" />{task.assignee_user.name}</>}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Task Detail Sheet */}
      <Sheet open={!!selectedTask} onOpenChange={(open) => !open && setSelectedTask(null)}>
        <SheetContent className="w-[500px] sm:w-[600px] overflow-y-auto">
          {selectedTask && (
            <>
              <SheetHeader>
                <div className="flex items-center justify-between">
                  <SheetTitle className="flex items-center gap-2">
                    <span className="text-muted-foreground font-mono">{selectedTask.identifier}</span>
                  </SheetTitle>
                  <Button variant="ghost" size="icon" onClick={handleDeleteTask}>
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </SheetHeader>

              <div className="space-y-6 mt-6">
                {/* Title */}
                <div>
                  <h3 className="text-lg font-semibold">{selectedTask.title}</h3>
                  {selectedTask.description && (
                    <p className="text-sm text-muted-foreground mt-1">{selectedTask.description}</p>
                  )}
                </div>

                {/* Status */}
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">Status</Label>
                  <Select value={selectedTask.status} onValueChange={(v) => handleUpdateTask('status', v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(statusConfig).map(([value, { label }]) => (
                        <SelectItem key={value} value={value}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Priority */}
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">Priority</Label>
                  <Select value={selectedTask.priority} onValueChange={(v) => handleUpdateTask('priority', v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Assignee */}
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">Assigned Agent</Label>
                  <Select
                    value={selectedTask.assignee_agent_id || '_none'}
                    onValueChange={(v) => handleUpdateTask('assignee_agent_id', v === '_none' ? '' : v)}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_none">Unassigned</SelectItem>
                      {agents.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id}>
                          <span className="flex items-center gap-2">
                            <Bot className="h-3 w-3" /> {agent.name}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Linked Run */}
                {selectedTask.run_id && (
                  <div className="space-y-1">
                    <Label className="text-xs text-muted-foreground uppercase">Linked Run</Label>
                    <p className="text-sm font-mono">{selectedTask.run_id}</p>
                  </div>
                )}

                {/* Comments */}
                <div className="space-y-3">
                  <Label className="text-xs text-muted-foreground uppercase">
                    Comments ({taskComments.length})
                  </Label>

                  <div className="space-y-3 max-h-[300px] overflow-y-auto">
                    {taskComments.map((comment) => (
                      <div key={comment.id} className="bg-muted/50 rounded-lg p-3 space-y-1">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {comment.author_type === 'agent' ? (
                            <><Bot className="h-3 w-3" /><span>{comment.author?.name ?? 'Agent'}</span></>
                          ) : comment.author_type === 'user' ? (
                            <><User className="h-3 w-3" /><span>{comment.author?.name ?? 'User'}</span></>
                          ) : (
                            <span>System</span>
                          )}
                          {comment.created_at && (
                            <span>{new Date(comment.created_at).toLocaleString()}</span>
                          )}
                        </div>
                        <p className="text-sm whitespace-pre-wrap">{comment.content}</p>
                      </div>
                    ))}
                    {taskComments.length === 0 && (
                      <p className="text-sm text-muted-foreground">No comments yet</p>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Input
                      placeholder="Add a comment..."
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddComment()}
                    />
                    <Button size="icon" onClick={handleAddComment} disabled={!newComment.trim()}>
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* Metadata */}
                <div className="text-xs text-muted-foreground space-y-1">
                  {selectedTask.created_at && <p>Created {new Date(selectedTask.created_at).toLocaleString()}</p>}
                  {selectedTask.updated_at && <p>Updated {new Date(selectedTask.updated_at).toLocaleString()}</p>}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
