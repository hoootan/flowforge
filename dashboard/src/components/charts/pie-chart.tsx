"use client"

import { Cell, Pie, PieChart as RechartsPieChart, Legend, Tooltip } from "recharts"
import { ChartConfig, ChartContainer } from "@/components/ui/chart"

interface PieChartProps {
  data: Array<{
    name: string
    value: number
    color?: string
  }>
  config: ChartConfig
  className?: string
  innerRadius?: number
  outerRadius?: number
  showLegend?: boolean
}

export function PieChart({
  data,
  config,
  className,
  innerRadius = 60,
  outerRadius = 80,
  showLegend = true,
}: PieChartProps) {
  const colors = [
    "var(--color-chart-1)",
    "var(--color-chart-2)",
    "var(--color-chart-3)",
    "var(--color-chart-4)",
    "var(--color-chart-5)",
  ]

  return (
    <ChartContainer config={config} className={className}>
      <RechartsPieChart>
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const data = payload[0]
            return (
              <div className="rounded-lg border bg-background px-3 py-2 shadow-sm">
                <div className="flex items-center gap-2">
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: data.payload.color || colors[0] }}
                  />
                  <span className="text-sm font-medium">{data.name}</span>
                  <span className="ml-auto font-mono text-sm">
                    {data.value?.toLocaleString()}
                  </span>
                </div>
              </div>
            )
          }}
        />
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          paddingAngle={2}
          dataKey="value"
          nameKey="name"
        >
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.color || colors[index % colors.length]}
            />
          ))}
        </Pie>
        {showLegend && (
          <Legend
            content={({ payload }) => {
              if (!payload?.length) return null
              return (
                <div className="flex items-center justify-center gap-4 pt-3">
                  {payload.map((item, index) => (
                    <div key={index} className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 shrink-0 rounded-[2px]"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-xs text-muted-foreground">
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              )
            }}
          />
        )}
      </RechartsPieChart>
    </ChartContainer>
  )
}
