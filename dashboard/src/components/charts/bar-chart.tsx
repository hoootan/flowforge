"use client"

import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"

interface BarChartProps {
  data: Array<Record<string, unknown>>
  xAxisKey: string
  yAxisKey: string
  config: ChartConfig
  className?: string
  showGrid?: boolean
  showYAxis?: boolean
  barRadius?: number
}

export function BarChart({
  data,
  xAxisKey,
  yAxisKey,
  config,
  className,
  showGrid = true,
  showYAxis = false,
  barRadius = 4,
}: BarChartProps) {
  return (
    <ChartContainer config={config} className={className}>
      <RechartsBarChart
        data={data}
        margin={{ left: 12, right: 12, top: 12, bottom: 0 }}
      >
        {showGrid && (
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
        )}
        <XAxis
          dataKey={xAxisKey}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={32}
          tickFormatter={(value) => {
            if (typeof value === "string") {
              return value.slice(0, 3)
            }
            return value
          }}
        />
        {showYAxis && (
          <YAxis
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            tickFormatter={(value) => `${value}`}
          />
        )}
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent indicator="dot" />}
        />
        <Bar
          dataKey={yAxisKey}
          fill={`var(--color-${yAxisKey})`}
          radius={barRadius}
        />
      </RechartsBarChart>
    </ChartContainer>
  )
}
