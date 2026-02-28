import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import type { AttackTypeGroup } from '../../types/analysis'

interface AttackTypeDonutProps {
  data: AttackTypeGroup[]
  height?: number
}

const TYPE_COLORS: Record<string, string> = {
  normal:     'var(--color-normal)',
  'attack-pos': 'var(--color-attack)',
  'attack-neg': '#f97316',
  unknown:    'var(--color-muted)',
}

export default function AttackTypeDonut({ data, height = 200 }: AttackTypeDonutProps) {
  const chartData = data.map((d) => ({
    name: d.exp_type,
    value: d.total_segments,
    color: TYPE_COLORS[d.exp_type] || 'var(--color-brand)',
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius="55%"
          outerRadius="75%"
          dataKey="value"
          paddingAngle={3}
        >
          {chartData.map((entry, i) => (
            <Cell key={`cell-${i}`} fill={entry.color} />
          ))}
        </Pie>
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
      </PieChart>
    </ResponsiveContainer>
  )
}
