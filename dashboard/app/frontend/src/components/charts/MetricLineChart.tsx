import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { MetricPoint } from '../../types/experiments'

interface MetricLineChartProps {
  data: MetricPoint[]
  unit?: string
  color?: string
  height?: number
  name?: string
}

function formatTs(ts: string): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function MetricLineChart({
  data,
  unit = '',
  color = 'var(--color-brand)',
  height = 180,
  name = 'value',
}: MetricLineChartProps) {
  const chartData = data.map((p) => ({
    ts: formatTs(p.ts),
    value: Number(p.value.toFixed(4)),
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(113,128,150,0.15)" />
        <XAxis
          dataKey="ts"
          tick={{ fontSize: 10, fill: 'var(--color-muted)' }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--color-muted)' }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `${v}${unit}`}
          width={48}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg)',
            border: 'none',
            boxShadow: 'var(--shadow-raised-sm)',
            borderRadius: 10,
            fontSize: 12,
          }}
          formatter={(v: number) => [`${v} ${unit}`, name]}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          name={name}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
