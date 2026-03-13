import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { MetricPoint } from '../../types/experiments'

interface SeriesDef {
  data: MetricPoint[]
  name: string
  color: string
}

interface MetricLineChartProps {
  data: MetricPoint[]
  unit?: string
  color?: string
  height?: number
  name?: string
  compareData?: MetricPoint[]
  compareName?: string
}

function formatTs(ts: string): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function buildChartData(series: SeriesDef[]) {
  const maxLen = Math.max(...series.map(s => s.data.length))
  return Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, string | number> = {
      ts: series[0]?.data[i] ? formatTs(series[0].data[i].ts) : '',
    }
    series.forEach(s => {
      row[s.name] = s.data[i] != null ? Number(Number(s.data[i].value).toFixed(4)) : NaN
    })
    return row
  })
}

export default function MetricLineChart({
  data,
  unit = '',
  color = 'var(--color-brand)',
  height = 200,
  name = 'value',
  compareData,
  compareName,
}: MetricLineChartProps) {
  const series: SeriesDef[] = [{ data, name, color }]
  if (compareData && compareData.length > 0) {
    series.push({ data: compareData, name: compareName ?? 'compare', color: '#06b6d4' })
  }

  const chartData = buildChartData(series)

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
          tickFormatter={(v: number) => `${v}${unit ? ' ' + unit : ''}`}
          width={52}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg)',
            border: 'none',
            boxShadow: 'var(--shadow-raised-sm)',
            borderRadius: 10,
            fontSize: 12,
          }}
          formatter={(v: number, n: string) => [`${v}${unit ? ' ' + unit : ''}`, n]}
        />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {series.map(s => (
          <Line
            key={s.name}
            type="monotone"
            dataKey={s.name}
            stroke={s.color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
