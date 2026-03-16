import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

interface MetricBar {
  name: string
  value: number
  color?: string
}

interface PerformanceBarChartProps {
  data: MetricBar[]
  height?: number
  domain?: [number, number]
  unit?: string
}

export default function PerformanceBarChart({ data, height = 180, domain = [0, 1], unit = '' }: PerformanceBarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(113,128,150,0.15)" />
        <XAxis
          type="number"
          domain={domain}
          tick={{ fontSize: 10, fill: 'var(--color-muted)' }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}${unit || '%'}`}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--color-text)' }}
          tickLine={false}
          axisLine={false}
          width={72}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg)',
            border: 'none',
            boxShadow: 'var(--shadow-raised-sm)',
            borderRadius: 10,
            fontSize: 12,
          }}
          formatter={(v: number) => [`${(v * 100).toFixed(2)}%`]}
        />
        <Bar dataKey="value" radius={[0, 6, 6, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={`cell-${i}`}
              fill={entry.color || 'var(--color-brand)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
