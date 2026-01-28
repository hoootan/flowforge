"use client"

import {
  Area,
  AreaChart as RechartsAreaChart,
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

interface AreaChartProps {
  data: Array<Record<string, unknown>>
  xAxisKey: string
  yAxisKey: string
  config: ChartConfig
  className?: string
  showGrid?: boolean
  showYAxis?: boolean
  gradientId?: string
}

export function AreaChart({
  data,
  xAxisKey,
  yAxisKey,
  config,
  className,
  showGrid = true,
  showYAxis = false,
  gradientId = "fillArea",
}: AreaChartProps) {
  return (
    <ChartContainer config={config} className={className}>
      <RechartsAreaChart
        data={data}
        margin={{ left: 12, right: 12, top: 12, bottom: 0 }}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="5%"
              stopColor={`var(--color-${yAxisKey})`}
              stopOpacity={0.8}
            />
            <stop
              offset="95%"
              stopColor={`var(--color-${yAxisKey})`}
              stopOpacity={0.1}
            />
          </linearGradient>
        </defs>
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
        <Area
          dataKey={yAxisKey}
          type="monotone"
          fill={`url(#${gradientId})`}
          stroke={`var(--color-${yAxisKey})`}
          strokeWidth={2}
        />
      </RechartsAreaChart>
    </ChartContainer>
  )
}
