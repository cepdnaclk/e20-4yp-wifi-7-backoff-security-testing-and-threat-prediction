import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { ConfidenceHistogram as ConfidenceHistogramType } from '../../types/analysis'

interface ConfidenceHistogramProps {
  data: ConfidenceHistogramType
  height?: number
}

export default function ConfidenceHistogram({ data, height = 200 }: ConfidenceHistogramProps) {
  // Merge normal and attack bins into unified chart data
  const bins: Record<string, { label: string; normal: number; attack: number }> = {}

  data.normal.forEach((b) => {
    const label = `${(b.bin_start * 100).toFixed(0)}-${(b.bin_end * 100).toFixed(0)}%`
    if (!bins[label]) bins[label] = { label, normal: 0, attack: 0 }
    bins[label].normal = b.count
  })

  data.attack.forEach((b) => {
    const label = `${(b.bin_start * 100).toFixed(0)}-${(b.bin_end * 100).toFixed(0)}%`
    if (!bins[label]) bins[label] = { label, normal: 0, attack: 0 }
    bins[label].attack = b.count
  })

  const chartData = Object.values(bins).sort((a, b) => a.label.localeCompare(b.label))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(113,128,150,0.15)" />
        <XAxis dataKey="label" tick={{ fontSize: 10, fill: 'var(--color-muted)' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 10, fill: 'var(--color-muted)' }} tickLine={false} axisLine={false} width={36} />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg)',
            border: 'none',
            boxShadow: 'var(--shadow-raised-sm)',
            borderRadius: 10,
            fontSize: 12,
          }}
        />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="normal" name="Normal" fill="var(--color-normal)" radius={[4, 4, 0, 0]} />
        <Bar dataKey="attack" name="Attack" fill="var(--color-attack)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
