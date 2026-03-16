import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine, ReferenceArea,
} from 'recharts'
import type { MetricPoint } from '../../types/experiments'

interface SeriesDef {
  data: MetricPoint[]
  name: string
  color: string
}

export interface SegmentMark {
  ts: string        // ISO timestamp of segment boundary (ts_start)
  color: string     // segment prediction color (green=normal, red=attack)
  label: string     // e.g. "seg1"
}

export interface SegmentHighlight {
  tsStart: string   // ISO timestamp
  tsEnd: string     // ISO timestamp
  color: string     // rgba or css color
}

interface MetricLineChartProps {
  data: MetricPoint[]
  unit?: string
  color?: string
  height?: number
  name?: string
  compareData?: MetricPoint[]
  compareName?: string
  segmentMarks?: SegmentMark[]
  highlight?: SegmentHighlight | null
}

function formatTs(ts: string): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function buildChartData(series: SeriesDef[]) {
  const maxLen = Math.max(...series.map(s => s.data.length))
  return Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, string | number> = {
      ts: series[0]?.data[i] ? formatTs(series[0].data[i].ts) : '',
      _rawTs: series[0]?.data[i]?.ts ?? '',
    }
    series.forEach(s => {
      row[s.name] = s.data[i] != null ? Number(Number(s.data[i].value).toFixed(4)) : NaN
    })
    return row
  })
}

// Find the formatted ts of the data point closest to the given ISO timestamp
function findClosestTs(chartData: ReturnType<typeof buildChartData>, isoTs: string): string | null {
  if (!isoTs || chartData.length === 0) return null
  const target = new Date(isoTs).getTime()
  let best = 0
  let bestDiff = Infinity
  chartData.forEach((row, i) => {
    const t = new Date(row._rawTs as string).getTime()
    if (isNaN(t)) return
    const diff = Math.abs(t - target)
    if (diff < bestDiff) { bestDiff = diff; best = i }
  })
  return chartData[best]?.ts as string ?? null
}

export default function MetricLineChart({
  data,
  unit = '',
  color = 'var(--color-brand)',
  height = 200,
  name = 'value',
  compareData,
  compareName,
  segmentMarks,
  highlight,
}: MetricLineChartProps) {
  const series: SeriesDef[] = [{ data, name, color }]
  if (compareData && compareData.length > 0) {
    series.push({ data: compareData, name: compareName ?? 'compare', color: '#06b6d4' })
  }

  const chartData = buildChartData(series)

  // Map segment boundary ISO timestamps → formatted x-axis values
  const resolvedMarks = (segmentMarks ?? []).map(m => ({
    ...m,
    xVal: findClosestTs(chartData, m.ts),
  })).filter(m => m.xVal !== null)

  // Map highlight region
  const hlStart = highlight ? findClosestTs(chartData, highlight.tsStart) : null
  const hlEnd   = highlight ? findClosestTs(chartData, highlight.tsEnd)   : null

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

        {/* Highlighted selected segment region */}
        {hlStart && hlEnd && (
          <ReferenceArea
            x1={hlStart}
            x2={hlEnd}
            fill={highlight!.color}
            fillOpacity={0.12}
            stroke={highlight!.color}
            strokeOpacity={0.3}
            strokeWidth={1}
          />
        )}

        {/* Segment boundary vertical lines */}
        {resolvedMarks.map((m, i) => (
          <ReferenceLine
            key={i}
            x={m.xVal!}
            stroke={m.color}
            strokeOpacity={0.35}
            strokeWidth={1}
            strokeDasharray="4 3"
            label={{
              value: m.label,
              position: 'insideTopRight',
              fontSize: 9,
              fill: m.color,
              opacity: 0.6,
            }}
          />
        ))}

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
