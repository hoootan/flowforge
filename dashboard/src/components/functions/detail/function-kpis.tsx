"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Activity, CheckCircle, Clock, DollarSign } from "lucide-react";

interface FunctionKPIsProps {
  totalRuns: number;
  successRate: number;
  avgDuration: string;
  totalCost: number;
}

export function FunctionKPIs({ totalRuns, successRate, avgDuration, totalCost }: FunctionKPIsProps) {
  const kpis = [
    { label: "Total Runs", value: totalRuns.toLocaleString(), icon: Activity },
    {
      label: "Success Rate", value: `${successRate.toFixed(1)}%`, icon: CheckCircle,
      sub: successRate >= 95 ? "healthy" : successRate >= 80 ? "acceptable" : "needs attention",
      subColor: successRate >= 95 ? "text-green-500" : successRate >= 80 ? "text-yellow-500" : "text-red-500",
    },
    { label: "Avg Duration", value: avgDuration, icon: Clock },
    { label: "Total Cost", value: totalCost < 1 ? `$${totalCost.toFixed(3)}` : `$${totalCost.toFixed(2)}`, icon: DollarSign },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-4">
      {kpis.map((kpi) => {
        const Icon = kpi.icon;
        return (
          <Card key={kpi.label} className="bg-muted/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-muted-foreground">{kpi.label}</p>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </div>
              <p className="text-2xl font-bold">{kpi.value}</p>
              {kpi.sub && <p className={`text-xs mt-0.5 ${kpi.subColor || ""}`}>{kpi.sub}</p>}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
