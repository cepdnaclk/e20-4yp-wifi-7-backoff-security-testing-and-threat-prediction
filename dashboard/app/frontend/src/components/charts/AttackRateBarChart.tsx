import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import type { Experiment } from '../../types/experiments'

interface AttackRateBarChartProps {
  experiments: Experiment[]
  height?: number
}

function shortId(id: string): string {
  const parts = id.split('-')
  return parts.slice(-2).join('-')
}

export default function AttackRateBarChart({ experiments, height = 220 }: AttackRateBarChartProps) {
  const data = experiments.map((e) => ({
    id: shortId(e.experiment_id),
    rate: +(e.attack_rate * 100).toFixed(1),
    type: e.inferred_type,
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(113,128,150,0.15)" />
        <XAxis
          dataKey="id"
          tick={{ fontSize: 9, fill: 'var(--color-muted)' }}
          tickLine={false}
          axisLine={false}
          angle={-30}
          textAnchor="end"
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--color-muted)' }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `${v}%`}
          domain={[0, 100]}
          width={36}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg)',
            border: 'none',
            boxShadow: 'var(--shadow-raised-sm)',
            borderRadius: 10,
            fontSize: 12,
          }}
          formatter={(v: number) => [`${v}%`, 'Attack Rate']}
        />
        <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={`cell-${i}`}
              fill={entry.type === 'attack' ? 'var(--color-attack)' : 'var(--color-normal)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
