import { useState, useEffect, useRef, useCallback } from 'react'
import { useApp } from '../context/AppContext'
import SectionTitle from '../components/common/SectionTitle'
import Badge from '../components/common/Badge'
import { useRunStatus, useRunHistory, launchExperiment, cancelRun } from '../hooks/useRun'
import { useModels } from '../hooks/useModels'
import type { LaunchRequest } from '../hooks/useRun'

const PIPELINE_STAGES = ['ns3', 'exporter', 'kafka', 'windowizer', 'gcn', 'db'] as const
const STAGE_LABELS: Record<string, string> = {
  ns3: 'NS-3 Simulation',
  exporter: 'Telemetry Exporter',
  kafka: 'Kafka / Redpanda',
  windowizer: 'Windowizer',
  gcn: 'GCN Detector',
  db: 'Database',
}

const SCENARIO_OPTIONS = [
  { value: 'normal',   label: 'Normal',     description: 'No attack' },
  { value: 'positive', label: 'Attack (+)', description: '+bias' },
  { value: 'negative', label: 'Attack (−)', description: '−bias' },
  { value: 'dynamic',  label: 'Dynamic',    description: 'segment builder' },
] as const

const SEGMENT_LENGTHS = [32, 64, 128, 256] as const

// ── Segment builder types & helpers ──────────────────────────────────────────

type PhaseType = 'normal' | 'positive' | 'negative'

interface SegmentBlock {
  id: string
  primaryType: PhaseType
  transition: boolean       // false = full block, true = has a split
  splitPercent: number      // % that is primaryType (1–99)
  secondaryType: PhaseType  // type after the split
  count: number             // repetitions (only when !transition)
}

function biasOf(t: PhaseType): number {
  if (t === 'positive') return 5000
  if (t === 'negative') return -5000
  return 0
}

function computePhasesAndSimTime(
  blocks: SegmentBlock[],
  segLen: number,
): { phases: string; simTime: number; totalSegments: number } {
  const segDur = segLen * 0.1
  let t = 0
  let curBias: number | null = null
  const parts: string[] = []
  let totalSegments = 0

  for (const blk of blocks) {
    const primBias = biasOf(blk.primaryType)

    if (primBias !== curBias) {
      parts.push(`${Math.round(t)}:${primBias}`)
      curBias = primBias
    }

    if (blk.transition) {
      totalSegments += 1
      const splitT = t + (blk.splitPercent / 100) * segDur
      const secBias = biasOf(blk.secondaryType)
      parts.push(`${Math.round(splitT)}:${secBias}`)
      curBias = secBias
      t += segDur
    } else {
      totalSegments += blk.count
      t += segDur * blk.count
    }
  }

  return { phases: parts.join(','), simTime: Math.ceil(t), totalSegments }
}

// Default: NEG×2 → 60%NEG/40%NORM → NORM×2 → 35%NORM/65%POS → 60%NORM/40%POS → POS×2
const DEFAULT_BLOCKS: SegmentBlock[] = [
  { id: 'b1', primaryType: 'negative', transition: false, splitPercent: 60, secondaryType: 'normal',   count: 2 },
  { id: 'b2', primaryType: 'negative', transition: true,  splitPercent: 60, secondaryType: 'normal',   count: 1 },
  { id: 'b3', primaryType: 'normal',   transition: false, splitPercent: 35, secondaryType: 'positive', count: 2 },
  { id: 'b4', primaryType: 'normal',   transition: true,  splitPercent: 35, secondaryType: 'positive', count: 1 },
  { id: 'b5', primaryType: 'normal',   transition: true,  splitPercent: 60, secondaryType: 'positive', count: 1 },
  { id: 'b6', primaryType: 'positive', transition: false, splitPercent: 60, secondaryType: 'normal',   count: 2 },
]

const TYPE_LABELS: Record<PhaseType, string> = { normal: 'Normal', positive: '+Attack', negative: '−Attack' }
const TYPE_COLORS: Record<PhaseType, string> = {
  normal:   'var(--color-normal)',
  positive: 'var(--color-attack)',
  negative: 'var(--color-warning)',
}

// ── Main component ────────────────────────────────────────────────────────────

function generateExpId(scenario: string, numAp: number, seed: number, gcnVer?: string): string {
  const now = new Date()
  const ts = now.toISOString().slice(0, 16).replace('T', '-').replace(/:/g, '')
  const ver = gcnVer ? `-${gcnVer.replace(/\./g, '')}` : ''
  return `${ts}-${scenario}-${numAp}ap-seed${seed}${ver}`
}

export default function RunSection() {
  const { setSelectedExperimentId } = useApp()
  const { status, refresh } = useRunStatus(2000)
  const { history, reload: reloadHistory } = useRunHistory()
  const { data: modelList } = useModels()

  // Form state
  const [scenario, setScenario] = useState<'normal' | 'positive' | 'negative' | 'dynamic'>('positive')
  const [seed, setSeed] = useState(42)
  const [simTime, setSimTime] = useState(80)
  const [bias, setBias] = useState(5000)
  const [numAp, setNumAp] = useState(1)
  const [numSta, setNumSta] = useState(2)
  const [segmentLength, setSegmentLength] = useState<32 | 64 | 128 | 256>(256)
  const [gcnVersion, setGcnVersion] = useState<string>('')
  const [customExpId, setCustomExpId] = useState('')
  const [showSeedHelp, setShowSeedHelp] = useState(false)

  // Dynamic segment builder
  const [segmentBlocks, setSegmentBlocks] = useState<SegmentBlock[]>(DEFAULT_BLOCKS)
  const blockIdCounter = useRef(10)

  // Benchmark state
  const benchmarkQueue = useRef<LaunchRequest[]>([])
  const [benchmarkRunning, setBenchmarkRunning] = useState(false)
  const [benchmarkStep, setBenchmarkStep] = useState(0)
  const [benchmarkTotal, setBenchmarkTotal] = useState(0)

  // UI state
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState<string | null>(null)
  const [completedExpId, setCompletedExpId] = useState<string | null>(null)

  const isRunning = status?.active === true
  const availableVersions = modelList?.models?.map(m => m.version) ?? []
  const activeVersion = modelList?.active_version ?? ''

  useEffect(() => {
    if (activeVersion && !gcnVersion) setGcnVersion(activeVersion)
  }, [activeVersion])

  // Computed phases & sim time from segment builder
  const computed = computePhasesAndSimTime(segmentBlocks, segmentLength)

  const autoExpId = generateExpId(scenario, numAp, seed, gcnVersion)

  // When run completes: reload history and optionally show completion card
  const prevIsRunning = useRef(false)
  useEffect(() => {
    if (prevIsRunning.current && !isRunning) {
      reloadHistory()
    }
    prevIsRunning.current = isRunning
  }, [isRunning])

  useEffect(() => {
    if (!isRunning && status?.experiment_id && status.state !== 'error' && !benchmarkRunning) {
      const latest = history[0]
      if (latest?.outcome === 'success') setCompletedExpId(latest.experiment_id)
    }
  }, [isRunning, status, history, benchmarkRunning])

  // Benchmark sequential launcher: when idle, launch next queued experiment
  useEffect(() => {
    if (!benchmarkRunning) return
    if (isRunning) return
    if (benchmarkQueue.current.length === 0) {
      setBenchmarkRunning(false)
      reloadHistory()
      return
    }
    const next = benchmarkQueue.current.shift()!
    setBenchmarkStep(s => s + 1)
    launchExperiment(next)
      .then(() => { refresh(); reloadHistory() })
      .catch(e => { setLaunchError(String(e)); setBenchmarkRunning(false) })
  }, [isRunning, benchmarkRunning])

  // ── Segment builder helpers ────────────────────────────────────────────────

  const updateBlock = useCallback((id: string, patch: Partial<SegmentBlock>) => {
    setSegmentBlocks(bs => bs.map(b => b.id === id ? { ...b, ...patch } : b))
  }, [])

  const removeBlock = useCallback((id: string) => {
    setSegmentBlocks(bs => bs.filter(b => b.id !== id))
  }, [])

  const addBlock = useCallback(() => {
    const id = `b${++blockIdCounter.current}`
    setSegmentBlocks(bs => [...bs, {
      id, primaryType: 'normal', transition: false, splitPercent: 50, secondaryType: 'positive', count: 1,
    }])
  }, [])

  // ── Launch handlers ────────────────────────────────────────────────────────

  // Reference phases/simTime always computed from 256w — keeps scenario identical across all window sizes.
  // Only the windowizer segment_length changes so the comparison is fair.
  const refComputed = computePhasesAndSimTime(segmentBlocks, 256)

  const buildDynamicReq = (sl: number, expIdOverride?: string): LaunchRequest => ({
    scenario: 'dynamic',
    seed,
    sim_time: refComputed.simTime,   // same sim_time for all
    bias: 0,
    num_ap: numAp,
    num_sta: numSta,
    segment_length: sl as 32 | 64 | 128 | 256,
    experiment_id: expIdOverride,
    gcn_version: gcnVersion || undefined,
    phases: refComputed.phases,      // same phases for all (256w reference)
  })

  const handleLaunch = async () => {
    setLaunching(true)
    setLaunchError(null)
    setCompletedExpId(null)
    try {
      let req: LaunchRequest
      if (scenario === 'dynamic') {
        req = buildDynamicReq(segmentLength, customExpId || undefined)
      } else {
        req = {
          scenario,
          seed,
          sim_time: simTime,
          bias: scenario === 'normal' ? 0 : bias,
          num_ap: numAp,
          num_sta: numSta,
          segment_length: segmentLength,
          experiment_id: customExpId || undefined,
          gcn_version: gcnVersion || undefined,
        }
      }
      await launchExperiment(req)
      refresh()
      reloadHistory()
    } catch (e) {
      setLaunchError(String(e))
    } finally {
      setLaunching(false)
    }
  }

  const handleBenchmark = async () => {
    setLaunchError(null)
    setCompletedExpId(null)
    const now = new Date()
    const ts = now.toISOString().slice(0, 16).replace('T', '-').replace(/:/g, '')

    const allReqs = SEGMENT_LENGTHS.map(sl => {
      const expId = `${ts}-benchmark-${sl}w-seed${seed}`
      return buildDynamicReq(sl, expId)
    })

    // Queue remaining, launch first immediately
    benchmarkQueue.current = allReqs.slice(1)
    setBenchmarkRunning(true)
    setBenchmarkStep(1)
    setBenchmarkTotal(allReqs.length)

    try {
      await launchExperiment(allReqs[0])
      refresh()
      reloadHistory()
    } catch (e) {
      setLaunchError(String(e))
      setBenchmarkRunning(false)
    }
  }

  const handleCancel = async () => {
    try {
      await cancelRun()
      refresh()
      if (benchmarkRunning) {
        benchmarkQueue.current = []
        setBenchmarkRunning(false)
      }
    } catch (e) {
      setLaunchError(String(e))
    }
  }

  const handleViewResults = () => {
    if (completedExpId) {
      setSelectedExperimentId(completedExpId)
      window.dispatchEvent(new CustomEvent('navigate', { detail: { section: 'experiment' } }))
    }
  }

  const needsV3Warning = numAp > 1 || segmentLength < 256

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle
        title="Run Experiment"
        subtitle="Configure and launch NS-3 scenarios from the dashboard"
      />

      {needsV3Warning && (
        <div className="neu-card text-sm" style={{ borderLeft: '3px solid var(--color-warning)', color: 'var(--color-warning)' }}>
          Multi-AP or short segment lengths require <strong>GCN v3.0.0</strong> — set the model below.
        </div>
      )}

      {!isRunning && (
        <div className="neu-card flex flex-col gap-4">
          <div className="section-title text-base">Simulation Configuration</div>

          {/* Scenario selector */}
          <div>
            <div className="text-xs font-semibold mb-2" style={{ color: 'var(--color-muted)' }}>SCENARIO</div>
            <div className="flex gap-2">
              {SCENARIO_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={`neu-btn text-xs px-3 py-1.5 ${scenario === opt.value ? 'neu-btn-primary' : ''}`}
                  onClick={() => setScenario(opt.value)}
                >
                  {opt.label}
                  <span className="ml-1 opacity-50">{opt.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Main params grid */}
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, 1fr) auto' }}>
            {/* SEED */}
            <div className="neu-inset flex flex-col gap-1 p-2.5">
              <div className="flex items-center gap-1">
                <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SEED</label>
                <button
                  className="text-xs leading-none opacity-50 hover:opacity-100"
                  style={{ color: 'var(--color-brand)' }}
                  onClick={() => setShowSeedHelp(h => !h)}
                >?</button>
              </div>
              <input
                type="number" min={1} max={9999}
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>

            {/* SIM TIME — hidden for dynamic (auto-computed) */}
            {scenario !== 'dynamic' ? (
              <div className="neu-inset flex flex-col gap-1 p-2.5">
                <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SIM TIME (s)</label>
                <input
                  type="number" min={10} max={600} step={10}
                  value={simTime}
                  onChange={(e) => setSimTime(Number(e.target.value))}
                  className="bg-transparent text-sm font-mono outline-none w-full"
                />
              </div>
            ) : (
              <div className="neu-inset flex flex-col gap-1 p-2.5" style={{ opacity: 0.6 }}>
                <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SIM TIME (s)</label>
                <div className="text-sm font-mono" style={{ color: 'var(--color-brand)' }}>{computed.simTime}s</div>
                <div className="text-xs opacity-50">auto from blocks</div>
              </div>
            )}

            {/* BIAS — hidden for dynamic */}
            {scenario !== 'dynamic' && (
              <div className="neu-inset flex flex-col gap-1 p-2.5" style={{ opacity: scenario === 'normal' ? 0.4 : 1 }}>
                <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>BIAS</label>
                <input
                  type="number" step={500}
                  value={scenario === 'normal' ? 0 : bias}
                  disabled={scenario === 'normal'}
                  onChange={(e) => setBias(Number(e.target.value))}
                  className="bg-transparent text-sm font-mono outline-none w-full"
                />
              </div>
            )}

            {/* APs / STAs */}
            <div className="neu-inset flex flex-col gap-1 p-2.5">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>APs / STAs</label>
              <div className="flex gap-1 items-center">
                <input
                  type="number" min={1} max={6}
                  value={numAp}
                  onChange={(e) => { const n = Number(e.target.value); setNumAp(n); setNumSta(n * 2) }}
                  className="bg-transparent text-sm font-mono outline-none w-8"
                />
                <span className="text-xs opacity-40">/</span>
                <input
                  type="number" min={1} max={12}
                  value={numSta}
                  onChange={(e) => setNumSta(Number(e.target.value))}
                  className="bg-transparent text-sm font-mono outline-none w-8"
                />
              </div>
            </div>

            {/* Launch button */}
            <button
              className="neu-btn neu-btn-primary px-5 font-semibold text-sm self-stretch"
              onClick={handleLaunch}
              disabled={launching || benchmarkRunning}
              style={{ minWidth: 130 }}
            >
              {launching ? 'Launching…' : '▶ Launch'}
            </button>
          </div>

          {/* ── Dynamic Segment Builder ─────────────────────────────────────── */}
          {scenario === 'dynamic' && (
            <div className="neu-inset flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>
                  SCENARIO BUILDER
                </label>
                <span className="text-xs" style={{ color: 'var(--color-brand)' }}>
                  {computed.totalSegments} segments · {computed.simTime}s (at {segmentLength}w)
                </span>
              </div>

              {segmentBlocks.map((blk, idx) => (
                <div key={blk.id} className="flex items-center gap-2 flex-wrap" style={{ fontSize: 12 }}>
                  {/* Index */}
                  <span className="opacity-30 w-4 text-right shrink-0">{idx + 1}</span>

                  {/* Primary type */}
                  <select
                    value={blk.primaryType}
                    onChange={e => updateBlock(blk.id, { primaryType: e.target.value as PhaseType })}
                    className="neu-btn text-xs py-0.5 px-1.5 font-mono outline-none"
                    style={{ color: TYPE_COLORS[blk.primaryType], background: 'var(--color-surface)', border: 'none' }}
                  >
                    <option value="normal">Normal</option>
                    <option value="positive">+Attack</option>
                    <option value="negative">−Attack</option>
                  </select>

                  {/* Full / Split toggle */}
                  <button
                    className={`neu-btn text-xs py-0.5 px-2 ${!blk.transition ? 'neu-btn-primary' : ''}`}
                    onClick={() => updateBlock(blk.id, { transition: false })}
                  >Full</button>
                  <button
                    className={`neu-btn text-xs py-0.5 px-2 ${blk.transition ? 'neu-btn-primary' : ''}`}
                    onClick={() => updateBlock(blk.id, { transition: true })}
                  >Split</button>

                  {/* Full: count */}
                  {!blk.transition && (
                    <div className="flex items-center gap-1">
                      <span className="opacity-40">×</span>
                      <input
                        type="number" min={1} max={20}
                        value={blk.count}
                        onChange={e => updateBlock(blk.id, { count: Math.max(1, Number(e.target.value)) })}
                        className="bg-transparent text-xs font-mono outline-none"
                        style={{ width: 32 }}
                      />
                      <span className="opacity-40">seg{blk.count !== 1 ? 's' : ''}</span>
                    </div>
                  )}

                  {/* Split: percent + secondary type */}
                  {blk.transition && (
                    <>
                      <div className="flex items-center gap-1">
                        <input
                          type="number" min={1} max={99}
                          value={blk.splitPercent}
                          onChange={e => updateBlock(blk.id, { splitPercent: Math.min(99, Math.max(1, Number(e.target.value))) })}
                          className="bg-transparent text-xs font-mono outline-none"
                          style={{ width: 32 }}
                        />
                        <span className="opacity-40">%</span>
                      </div>
                      <span className="opacity-40">→</span>
                      <span className="opacity-40" style={{ fontSize: 10 }}>{100 - blk.splitPercent}%</span>
                      <select
                        value={blk.secondaryType}
                        onChange={e => updateBlock(blk.id, { secondaryType: e.target.value as PhaseType })}
                        className="neu-btn text-xs py-0.5 px-1.5 font-mono outline-none"
                        style={{ color: TYPE_COLORS[blk.secondaryType], background: 'var(--color-surface)', border: 'none' }}
                      >
                        <option value="normal">Normal</option>
                        <option value="positive">+Attack</option>
                        <option value="negative">−Attack</option>
                      </select>
                    </>
                  )}

                  {/* Delete */}
                  <button
                    className="ml-auto text-xs opacity-30 hover:opacity-80"
                    onClick={() => removeBlock(blk.id)}
                    title="Remove block"
                  >✕</button>
                </div>
              ))}

              <button
                className="neu-btn text-xs self-start mt-1"
                onClick={addBlock}
              >+ Add Block</button>

              {/* Generated phases preview */}
              <div className="text-xs font-mono mt-2 px-1" style={{ color: 'var(--color-muted)', wordBreak: 'break-all' }}>
                <span className="opacity-50">phases ({segmentLength}w): </span>{computed.phases}
              </div>
            </div>
          )}

          {/* ── Benchmark runner (dynamic only) ────────────────────────────── */}
          {scenario === 'dynamic' && (
            <div className="neu-inset p-3 flex flex-col gap-2">
              <div className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>WINDOW SIZE BENCHMARK</div>
              <div className="text-xs opacity-60">
                Runs the same scenario with 32w, 64w, 128w, 256w — same seed — to find the best window size for dynamic detection.
              </div>
              <div className="flex gap-3 items-center flex-wrap">
                <button
                  className="neu-btn neu-btn-primary text-xs px-4 py-2 font-semibold"
                  onClick={handleBenchmark}
                  disabled={benchmarkRunning || isRunning || launching}
                >
                  {benchmarkRunning
                    ? `Running step ${benchmarkStep}/${benchmarkTotal}…`
                    : '⚡ Run All Window Sizes (32→64→128→256)'}
                </button>
                {benchmarkRunning && (
                  <span className="text-xs" style={{ color: 'var(--color-brand)' }}>
                    {SEGMENT_LENGTHS[benchmarkStep - 1]}w running — {benchmarkTotal - benchmarkStep} remaining after this
                  </span>
                )}
              </div>
              {/* Reference scenario info — same for all 4 runs */}
              <div className="flex flex-col gap-1 mt-1">
                <div className="text-xs opacity-50" style={{ wordBreak: 'break-all' }}>
                  <span style={{ opacity: 0.8 }}>Reference (256w · {refComputed.simTime}s): </span>{refComputed.phases}
                </div>
                <div className="flex gap-3 text-xs opacity-50 flex-wrap">
                  {SEGMENT_LENGTHS.map(sl => {
                    const segs = Math.floor(refComputed.simTime / (sl * 0.1))
                    return <span key={sl}>{sl}w → {segs} segments</span>
                  })}
                </div>
                <div className="text-xs opacity-40 italic">Same NS-3 sim for all · only windowizer segment size varies</div>
              </div>
            </div>
          )}

          {/* Seed help */}
          {showSeedHelp && (
            <div className="neu-inset p-3 text-xs" style={{ color: 'var(--color-muted)' }}>
              <strong style={{ color: 'var(--color-text)' }}>What is seed?</strong> The random seed initialises NS-3's
              random number generator. Same seed → identical packet arrival times, backoff draws, and
              channel conditions every run. Change it to get a statistically independent simulation.
              Use the <em>same seed</em> when comparing scenarios so the only variable is the attack bias.
              Use <em>different seeds</em> to test generalisation.
            </div>
          )}

          {/* Second row: segment length + model + exp ID */}
          <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 1fr 2fr' }}>
            {/* SEGMENT LENGTH */}
            <div className="neu-inset flex flex-col gap-1 p-2.5">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SEGMENT LENGTH</label>
              <div className="flex gap-1.5 mt-0.5 flex-wrap">
                {SEGMENT_LENGTHS.map((l) => (
                  <button
                    key={l}
                    className={`neu-btn text-xs py-0.5 px-1.5 ${segmentLength === l ? 'neu-btn-primary' : ''}`}
                    onClick={() => setSegmentLength(l as typeof segmentLength)}
                  >
                    {l}w
                  </button>
                ))}
              </div>
              <div className="text-xs mt-0.5 opacity-50">~{(segmentLength * 0.1).toFixed(1)}s window</div>
            </div>

            {/* GCN MODEL */}
            <div className="neu-inset flex flex-col gap-1 p-2.5">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>GCN MODEL</label>
              <select
                value={gcnVersion}
                onChange={(e) => setGcnVersion(e.target.value)}
                className="bg-transparent text-sm font-mono outline-none w-full"
                style={{ color: 'var(--color-text)' }}
              >
                {availableVersions.map(v => (
                  <option key={v} value={v} style={{ background: 'var(--color-surface)' }}>
                    {v}{v === activeVersion ? ' (active)' : ''}
                  </option>
                ))}
              </select>
              {gcnVersion && gcnVersion !== activeVersion && (
                <div className="text-xs opacity-60" style={{ color: 'var(--color-warning)' }}>
                  Will deploy {gcnVersion} before running
                </div>
              )}
            </div>

            {/* EXPERIMENT ID */}
            <div className="neu-inset flex flex-col gap-1 p-2.5">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>EXPERIMENT ID</label>
              <input
                type="text"
                placeholder={autoExpId}
                value={customExpId}
                onChange={(e) => setCustomExpId(e.target.value)}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>
          </div>

          {launchError && (
            <div className="text-sm" style={{ color: 'var(--color-attack)' }}>{launchError}</div>
          )}
        </div>
      )}

      {/* Live progress */}
      {isRunning && status && (
        <div className="neu-card flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="section-title text-base">
              {benchmarkRunning ? `Benchmark — Step ${benchmarkStep}/${benchmarkTotal}` : 'Running Experiment'}
            </div>
            <button className="neu-btn text-xs" style={{ color: 'var(--color-attack)' }} onClick={handleCancel}>
              {benchmarkRunning ? 'Cancel Benchmark' : 'Cancel'}
            </button>
          </div>
          <div className="font-mono text-sm" style={{ color: 'var(--color-brand)' }}>{status.experiment_id}</div>
          {benchmarkRunning && (
            <div className="text-xs" style={{ color: 'var(--color-muted)' }}>
              Window sizes: {SEGMENT_LENGTHS.map(sl => (
                <span key={sl} style={{
                  marginRight: 8,
                  color: sl === SEGMENT_LENGTHS[benchmarkStep - 1] ? 'var(--color-brand)' : 'var(--color-muted)',
                  fontWeight: sl === SEGMENT_LENGTHS[benchmarkStep - 1] ? 'bold' : 'normal',
                }}>{sl}w</span>
              ))}
            </div>
          )}
          {status.message && (
            <div className="text-sm" style={{ color: 'var(--color-muted)' }}>{status.message}</div>
          )}
          <div className="flex flex-col gap-2">
            {PIPELINE_STAGES.map((stage) => {
              const currentIdx = status.stage ? PIPELINE_STAGES.indexOf(status.stage as typeof PIPELINE_STAGES[number]) : -1
              const stageIdx = PIPELINE_STAGES.indexOf(stage)
              const isCurrent = status.stage === stage
              const isComplete = currentIdx >= 0 && stageIdx < currentIdx
              return (
                <div key={stage} className="neu-inset flex items-center gap-3 py-2 px-3" style={{ opacity: isComplete || isCurrent ? 1 : 0.4 }}>
                  <span style={{ color: isCurrent ? 'var(--color-brand)' : isComplete ? 'var(--color-normal)' : 'var(--color-muted)', fontSize: 16 }}>
                    {isCurrent ? '⚙' : isComplete ? '✓' : '○'}
                  </span>
                  <span className="text-sm">{STAGE_LABELS[stage]}</span>
                  {isCurrent && <span className="text-xs ml-auto" style={{ color: 'var(--color-brand)' }}>RUNNING</span>}
                  {isComplete && <span className="text-xs ml-auto" style={{ color: 'var(--color-normal)' }}>DONE</span>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Post-run card */}
      {completedExpId && !isRunning && (
        <div className="neu-card flex items-center justify-between gap-4">
          <div>
            <div className="text-sm font-semibold" style={{ color: 'var(--color-normal)' }}>Experiment Complete</div>
            <div className="font-mono text-xs mt-0.5" style={{ color: 'var(--color-muted)' }}>{completedExpId}</div>
          </div>
          <button className="neu-btn neu-btn-primary px-4 py-2 text-sm" onClick={handleViewResults}>
            View Results →
          </button>
        </div>
      )}

      {/* Run history */}
      {history.length > 0 && (
        <div className="neu-card">
          <div className="section-title text-base mb-3">Recent Runs</div>
          <div className="flex flex-col gap-2">
            {history.map((entry) => (
              <div key={entry.experiment_id} className="neu-inset flex items-center gap-3 py-2 px-3 flex-wrap">
                <span className="font-mono text-xs flex-1" style={{ color: 'var(--color-muted)' }}>
                  {entry.experiment_id}
                </span>
                <span className="text-xs opacity-60">
                  {entry.num_ap}AP · {entry.sim_time}s · seg={entry.segment_length}
                  {entry.gcn_version ? ` · ${entry.gcn_version}` : ''}
                </span>
                <Badge
                  variant={entry.outcome === 'success' ? 'normal' : entry.outcome === 'running' ? 'brand' : 'attack'}
                  label={entry.outcome}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
