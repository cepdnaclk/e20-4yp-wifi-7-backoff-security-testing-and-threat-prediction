import { useState, useEffect, useRef } from 'react'
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
] as const

const SEGMENT_LENGTHS = [32, 64, 128, 256] as const

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
  const [scenario, setScenario] = useState<'normal' | 'positive' | 'negative'>('positive')
  const [seed, setSeed] = useState(42)
  const [simTime, setSimTime] = useState(80)
  const [bias, setBias] = useState(5000)
  const [numAp, setNumAp] = useState(1)
  const [numSta, setNumSta] = useState(2)
  const [segmentLength, setSegmentLength] = useState<32 | 64 | 128 | 256>(256)
  const [gcnVersion, setGcnVersion] = useState<string>('')
  const [customExpId, setCustomExpId] = useState('')
  const [showSeedHelp, setShowSeedHelp] = useState(false)

  // UI state
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState<string | null>(null)
  const [completedExpId, setCompletedExpId] = useState<string | null>(null)

  const isRunning = status?.active === true
  const availableVersions = modelList?.models?.map(m => m.version) ?? []
  const activeVersion = modelList?.active_version ?? ''

  // Default gcnVersion to active model once loaded
  useEffect(() => {
    if (activeVersion && !gcnVersion) setGcnVersion(activeVersion)
  }, [activeVersion])

  const autoExpId = generateExpId(scenario, numAp, seed, gcnVersion)

  // When a run completes, reload history then show the completion card
  const prevIsRunning = useRef(false)
  useEffect(() => {
    if (prevIsRunning.current && !isRunning) {
      // Transition: was running → now idle. Reload history to pick up the completed entry.
      reloadHistory()
    }
    prevIsRunning.current = isRunning
  }, [isRunning])

  useEffect(() => {
    if (!isRunning && status?.experiment_id && status.state !== 'error') {
      const latest = history[0]
      if (latest?.outcome === 'success') setCompletedExpId(latest.experiment_id)
    }
  }, [isRunning, status, history])

  const handleLaunch = async () => {
    setLaunching(true)
    setLaunchError(null)
    setCompletedExpId(null)
    try {
      const req: LaunchRequest = {
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
      await launchExperiment(req)
      refresh()
      reloadHistory()
    } catch (e) {
      setLaunchError(String(e))
    } finally {
      setLaunching(false)
    }
  }

  const handleCancel = async () => {
    try { await cancelRun(); refresh() }
    catch (e) { setLaunchError(String(e)) }
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

      {/* v3 warning */}
      {needsV3Warning && (
        <div className="neu-card text-sm" style={{ borderLeft: '3px solid var(--color-warning)', color: 'var(--color-warning)' }}>
          Multi-AP or short segment lengths require <strong>GCN v3.0.0</strong> — set the model below.
        </div>
      )}

      {!isRunning && (
        <div className="neu-card flex flex-col gap-4">
          <div className="section-title text-base">Simulation Configuration</div>

          {/* Scenario row */}
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

          {/* Main params grid — 4 cols left, launch button right */}
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, 1fr) auto' }}>
            {/* SEED */}
            <div className="neu-inset flex flex-col gap-1 p-2.5">
              <div className="flex items-center gap-1">
                <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SEED</label>
                <button
                  className="text-xs leading-none opacity-50 hover:opacity-100"
                  style={{ color: 'var(--color-brand)' }}
                  onClick={() => setShowSeedHelp(h => !h)}
                  title="What is seed?"
                >?</button>
              </div>
              <input
                type="number" min={1} max={9999}
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>

            {/* SIM TIME */}
            <div className="neu-inset flex flex-col gap-1 p-2.5">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SIM TIME (s)</label>
              <input
                type="number" min={10} max={600} step={10}
                value={simTime}
                onChange={(e) => setSimTime(Number(e.target.value))}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>

            {/* BIAS */}
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

            {/* APs */}
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

            {/* LAUNCH BUTTON — same row, right column */}
            <button
              className="neu-btn neu-btn-primary px-5 font-semibold text-sm self-stretch"
              onClick={handleLaunch}
              disabled={launching}
              style={{ minWidth: 130 }}
            >
              {launching ? 'Launching…' : '▶ Launch'}
            </button>
          </div>

          {/* Seed explanation */}
          {showSeedHelp && (
            <div className="neu-inset p-3 text-xs" style={{ color: 'var(--color-muted)' }}>
              <strong style={{ color: 'var(--color-text)' }}>What is seed?</strong> The random seed initialises NS-3's
              random number generator. Same seed → identical packet arrival times, backoff draws, and
              channel conditions every run. Change it to get a statistically independent simulation.
              Use the <em>same seed</em> when comparing scenarios (normal vs attack) so the only
              variable is the attack bias. Use <em>different seeds</em> to test generalisation.
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
            <div className="section-title text-base">Running Experiment</div>
            <button className="neu-btn text-xs" style={{ color: 'var(--color-attack)' }} onClick={handleCancel}>
              Cancel
            </button>
          </div>
          <div className="font-mono text-sm" style={{ color: 'var(--color-brand)' }}>{status.experiment_id}</div>
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
