"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BarChart3, Coins, Clock, Zap, Loader2 } from "lucide-react";
import api from "@/lib/api";
import type { UsageSummary, UsageByProvider, UsageByModel, DailyUsage } from "@/lib/api";

function formatCost(cost: number): string {
  if (cost < 0.01) {
    return `$${cost.toFixed(4)}`;
  }
  return `$${cost.toFixed(2)}`;
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  subValue?: string;
}

function StatCard({ icon, label, value, subValue }: StatCardProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border p-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-xl font-semibold">{value}</p>
        {subValue && <p className="text-xs text-muted-foreground">{subValue}</p>}
      </div>
    </div>
  );
}

interface UsageBarProps {
  label: string;
  value: number;
  maxValue: number;
  formatter: (v: number) => string;
  color?: string;
}

function UsageBar({ label, value, maxValue, formatter, color = "bg-primary" }: UsageBarProps) {
  const percentage = maxValue > 0 ? (value / maxValue) * 100 : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">{formatter(value)}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-secondary">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}

export function AIUsageWidget() {
  const [days, setDays] = useState("30");
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [byProvider, setByProvider] = useState<UsageByProvider[]>([]);
  const [byModel, setByModel] = useState<UsageByModel[]>([]);
  const [daily, setDaily] = useState<DailyUsage[]>([]);

  const loadUsage = async () => {
    setLoading(true);
    try {
      const daysNum = parseInt(days);
      const [summaryData, providerData, modelData, dailyData] = await Promise.all([
        api.getUsageSummary(daysNum),
        api.getUsageByProvider(daysNum),
        api.getUsageByModel(daysNum),
        api.getDailyUsage(daysNum),
      ]);

      setSummary(summaryData);
      setByProvider(providerData);
      setByModel(modelData);
      setDaily(dailyData);
    } catch (error) {
      console.error("Failed to load usage data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsage();
  }, [days]);

  const maxProviderCost = Math.max(...byProvider.map((p) => p.cost_usd), 1);
  const maxModelCost = Math.max(...byModel.map((m) => m.cost_usd), 1);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Usage Statistics
          </CardTitle>
          <CardDescription>
            Token usage and cost tracking for AI operations
          </CardDescription>
        </div>
        <Select value={days} onValueChange={setDays}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Select period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : summary ? (
          <div className="space-y-6">
            {/* Summary Stats */}
            <div className="grid gap-4 md:grid-cols-4">
              <StatCard
                icon={<Zap className="h-5 w-5" />}
                label="Total Requests"
                value={formatNumber(summary.total_requests)}
              />
              <StatCard
                icon={<BarChart3 className="h-5 w-5" />}
                label="Total Tokens"
                value={formatNumber(summary.total_tokens)}
                subValue={`${formatNumber(summary.prompt_tokens)} in / ${formatNumber(summary.completion_tokens)} out`}
              />
              <StatCard
                icon={<Coins className="h-5 w-5" />}
                label="Total Cost"
                value={formatCost(summary.total_cost_usd)}
              />
              <StatCard
                icon={<Clock className="h-5 w-5" />}
                label="Avg Latency"
                value={`${summary.avg_latency_ms.toFixed(0)}ms`}
              />
            </div>

            {/* Breakdown Tabs */}
            {(byProvider.length > 0 || byModel.length > 0) && (
              <Tabs defaultValue="provider" className="w-full">
                <TabsList>
                  <TabsTrigger value="provider">By Provider</TabsTrigger>
                  <TabsTrigger value="model">By Model</TabsTrigger>
                </TabsList>

                <TabsContent value="provider" className="mt-4 space-y-4">
                  {byProvider.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No usage data yet</p>
                  ) : (
                    byProvider.map((p) => (
                      <UsageBar
                        key={p.provider}
                        label={p.provider}
                        value={p.cost_usd}
                        maxValue={maxProviderCost}
                        formatter={formatCost}
                      />
                    ))
                  )}
                </TabsContent>

                <TabsContent value="model" className="mt-4 space-y-4">
                  {byModel.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No usage data yet</p>
                  ) : (
                    byModel.slice(0, 5).map((m) => (
                      <UsageBar
                        key={`${m.provider}-${m.model}`}
                        label={m.model}
                        value={m.cost_usd}
                        maxValue={maxModelCost}
                        formatter={formatCost}
                      />
                    ))
                  )}
                </TabsContent>
              </Tabs>
            )}

            {/* Daily Chart Placeholder */}
            {daily.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Daily Usage (last {days} days)</h4>
                <div className="flex h-20 items-end gap-1">
                  {daily.slice(-14).map((d, i) => {
                    const maxDailyCost = Math.max(...daily.map((x) => x.cost_usd), 0.01);
                    const height = (d.cost_usd / maxDailyCost) * 100;
                    return (
                      <div
                        key={d.date}
                        className="flex-1 rounded-t bg-primary/60 hover:bg-primary transition-colors"
                        style={{ height: `${Math.max(height, 2)}%` }}
                        title={`${d.date}: ${formatCost(d.cost_usd)}`}
                      />
                    );
                  })}
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{daily[Math.max(0, daily.length - 14)]?.date}</span>
                  <span>{daily[daily.length - 1]?.date}</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <BarChart3 className="h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4 text-sm text-muted-foreground">
              No usage data available yet. Usage is tracked when AI steps execute.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
