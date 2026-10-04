import { animate, motion, useMotionValue, useTransform } from 'framer-motion'
import { useEffect, useState, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { bandColor, fmtDate, INTENT_COLORS, intentLabel, type Row } from '../data'

export function CountUp({ value, format = (n) => Math.round(n).toLocaleString('en-IN'), duration = 1.4 }: { value: number; format?: (n: number) => string; duration?: number }) {
  const mv = useMotionValue(0)
  const [txt, setTxt] = useState(format(0))
  useEffect(() => {
    const c = animate(mv, value, { duration, ease: [0.16, 1, 0.3, 1] })
    const u = mv.on('change', (v) => setTxt(format(v)))
    return () => { c.stop(); u() }
  }, [value])
  return <span className="tnum">{txt}</span>
}

export function Card({ children, className = '', delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }} className={`glass ${className}`}>
      {children}
    </motion.div>
  )
}

export function RiskGauge({ score, band }: { score: number; band: string }) {
  const r = 52, c = 2 * Math.PI * r, arc = c * 0.75
  const mv = useMotionValue(0)
  const dash = useTransform(mv, (v) => `${(v / 100) * arc} ${c}`)
  useEffect(() => { const a = animate(mv, score, { duration: 1.4, ease: [0.16, 1, 0.3, 1] }); return () => a.stop() }, [score])
  const col = bandColor(band)
  return (
    <div className="relative grid place-items-center">
      <svg width="148" height="148" viewBox="0 0 128 128" className="-rotate-[225deg]">
        <circle cx="64" cy="64" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10" strokeDasharray={`${arc} ${c}`} strokeLinecap="round" />
        <motion.circle cx="64" cy="64" r={r} fill="none" stroke={col} strokeWidth="10" strokeLinecap="round" style={{ strokeDasharray: dash, filter: `drop-shadow(0 0 6px ${col}88)` }} />
      </svg>
      <div className="absolute text-center">
        <div className="text-4xl font-extrabold text-white"><CountUp value={score} /></div>
        <div className="text-[11px] font-bold uppercase tracking-widest" style={{ color: col }}>{band} risk</div>
      </div>
    </div>
  )
}

export function BandPill({ band }: { band: string }) {
  const c = bandColor(band)
  return <span className="chip" style={{ color: c, borderColor: c + '55', background: c + '14' }}>{band}</span>
}

export function IntentChip({ intent }: { intent: string }) {
  const c = INTENT_COLORS[intent] ?? '#94a3b8'
  return <span className="chip capitalize" style={{ color: c, borderColor: c + '44', background: c + '12' }}>{intentLabel(intent)}</span>
}

export function SourceBadge({ source }: { source?: string }) {
  const live = source === 'cortex'
  return (
    <span className={`chip font-mono ${live ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-300' : 'border-amber-400/40 bg-amber-400/10 text-amber-300'}`} title="Data source tag from the export">
      <span className={`h-1.5 w-1.5 rounded-full ${live ? 'bg-cyan-300' : 'bg-amber-300'}`} />
      source: {source ?? 'unknown'}
    </span>
  )
}

export function TranscriptModal({ t, onClose }: { t: Row | null; onClose: () => void }) {
  if (!t) return null
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <motion.div initial={{ scale: 0.96, y: 10 }} animate={{ scale: 1, y: 0 }} className="glass max-h-[80vh] w-full max-w-2xl overflow-hidden !bg-ink-900/95" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between border-b border-white/5 p-5">
          <div>
            <div className="font-mono text-xs text-cyan-300">{t.TRANSCRIPT_ID} · {fmtDate(t.CALL_TS)} · {t.AGENT_ID}</div>
            <div className="mt-1 text-sm text-slate-200">{t.SUMMARY}</div>
            <div className="mt-2 flex gap-2"><IntentChip intent={t.PRIMARY_INTENT} /><span className="chip border-white/10 text-slate-300">sentiment {Number(t.SENTIMENT_SCORE).toFixed(2)}</span></div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-white/5 hover:text-white"><X size={18} /></button>
        </div>
        <div className="max-h-[55vh] space-y-2 overflow-y-auto p-5 text-sm leading-relaxed">
          {String(t.TRANSCRIPT_TEXT ?? '').split('\n').map((line: string, i: number) => {
            const cust = line.startsWith('Customer:')
            return <p key={i} className={cust ? 'rounded-lg bg-cyan-400/[0.06] px-3 py-1.5 text-slate-100' : 'px-3 text-slate-400'}>{line}</p>
          })}
        </div>
        <div className="border-t border-white/5 px-5 py-2 text-[11px] text-slate-500">Enriched by: {t.ENRICHED_BY}</div>
      </motion.div>
    </motion.div>
  )
}
