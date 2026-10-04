import { AnimatePresence, motion } from 'framer-motion'
import { Check, Copy, FileText, MapPin, MessageSquareText, Phone, ShieldCheck, Sparkles, X, Zap } from 'lucide-react'
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Area, AreaChart, ReferenceLine, ResponsiveContainer, Tooltip, YAxis } from 'recharts'
import type { OrbitNode } from '../components/Orbit360'
import { BandPill, Card, IntentChip, RiskGauge, TranscriptModal } from '../components/ui'
import { bandColor, fmtDate, healthColor, inr, useStore, type Driver, type Row } from '../data'

const Orbit360 = lazy(() => import('../components/Orbit360'))

const DRIVER_MAX: Record<string, number> = {
  'Negative sentiment': 25, 'Cancellation / porting intent': 20, 'Price sensitivity': 10,
  'Payment stress': 15, 'Claim friction': 15, 'Renewal due soon': 15,
}

export default function Customer360() {
  const { store } = useStore()
  const { id } = useParams()
  const nav = useNavigate()
  const [active, setActive] = useState<string | null>(null)
  const [transcript, setTranscript] = useState<Row | null>(null)

  useEffect(() => {
    if (store && (!id || !store.c360ById.has(id))) {
      const top = [...store.nba].sort((a, b) => b.RISK_SCORE - a.RISK_SCORE)[0]
      nav(`/customer/${top.CUSTOMER_ID}`, { replace: true })
    }
  }, [store, id])
  useEffect(() => setActive(null), [id])

  const d = useMemo(() => {
    if (!store || !id || !store.c360ById.has(id)) return null
    const c = store.c360ById.get(id)!
    const n = store.nbaById.get(id) ?? {}
    const calls = store.insightsByCust.get(id) ?? []
    const pols = store.policiesByCust.get(id) ?? []
    const clms = store.claimsByCust.get(id) ?? []
    const pays = store.paymentsByCust.get(id) ?? []
    return { c, n, calls, pols, clms, pays }
  }, [store, id])

  if (!d) return <Skeleton />
  const { c, n, calls, pols, clms, pays } = d

  const late = pays.filter((p) => p.PAYMENT_STATUS === 'Late').length
  const missed = pays.filter((p) => p.PAYMENT_STATUS === 'Missed').length
  const openClaims = clms.filter((x) => x.STATUS === 'Pending' || x.STATUS === 'Under Review')
  const rejected = clms.filter((x) => x.STATUS === 'Rejected').length
  const badPol = pols.filter((p) => /cancel|grace|lapse/i.test(p.STATUS)).length
  const sent = c.AVG_SENTIMENT_90D ?? c.AVG_SENTIMENT_180D
  const cancelCalls = calls.filter((x) => x.PRIMARY_INTENT === 'cancellation_intent').length

  const nodes: OrbitNode[] = [
    {
      key: 'policies', label: 'Policies', count: pols.length,
      health: badPol ? 'bad' : (c.DAYS_TO_RENEWAL ?? 999) <= 30 ? 'warn' : 'good',
      headline: `${c.N_ACTIVE_POLICIES} active · ${inr(c.TOTAL_ANNUAL_PREMIUM)}/yr`,
      sub: badPol ? `${badPol} in cancellation / grace` : `Next renewal ${fmtDate(c.NEXT_RENEWAL_DATE)}`,
    },
    {
      key: 'claims', label: 'Claims', count: clms.length,
      health: rejected || (c.N_SLOW_CLAIMS ?? 0) > 0 ? 'bad' : openClaims.length ? 'warn' : 'good',
      headline: clms.length ? `${openClaims.length} open · ${rejected} rejected` : 'No claims filed',
      sub: c.MAX_OPEN_CLAIM_DAYS ? `Oldest open: ${c.MAX_OPEN_CLAIM_DAYS} days` : `Avg settle ${c.AVG_DAYS_TO_SETTLE ? Math.round(c.AVG_DAYS_TO_SETTLE) + 'd' : '—'}`,
    },
    {
      key: 'payments', label: 'Payments', count: pays.length,
      health: missed ? 'bad' : late ? 'warn' : 'good',
      headline: `${late} late · ${missed} missed`,
      sub: `On-time rate ${c.ON_TIME_RATE_12M != null ? Math.round(c.ON_TIME_RATE_12M * 100) + '%' : '—'} (12m)`,
    },
    {
      key: 'calls', label: 'Call Transcripts', count: calls.length,
      health: cancelCalls || (sent ?? 0) < -0.2 ? 'bad' : (sent ?? 0) < 0.2 ? 'warn' : 'good',
      headline: `${calls.length} calls · sentiment ${sent != null ? sent.toFixed(2) : '—'}`,
      sub: `Last intent: ${(c.LAST_INTENT ?? '—').replace(/_/g, ' ')}`,
    },
  ]

  return (
    <div className="grid grid-cols-12 gap-5">
     <div className="col-span-12 space-y-5 xl:col-span-9">
      <div className="grid grid-cols-12 gap-5">
        {/* Left: profile + risk */}
        <div className="col-span-12 space-y-5 lg:col-span-4">
          <Card className="p-5">
            <div className="flex items-start gap-3">
              <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl text-lg font-extrabold text-ink-950" style={{ background: `linear-gradient(135deg, ${bandColor(n.RISK_BAND)}, #38d9f5)` }}>
                {String(c.FULL_NAME).split(' ').map((s: string) => s[0]).join('').slice(0, 2)}
              </div>
              <div className="min-w-0">
                <div className="truncate text-lg font-bold text-white">{c.FULL_NAME}</div>
                <div className="font-mono text-xs text-slate-500">{c.CUSTOMER_ID} · {c.GENDER} · {c.AGE}y</div>
                <div className="mt-1 flex flex-wrap gap-1.5"><BandPill band={n.RISK_BAND} /><span className="chip border-cyan-400/30 text-cyan-300">{c.SEGMENT}</span></div>
              </div>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2.5 text-[13px]">
              <Info k="Location" v={<span className="flex items-center gap-1"><MapPin size={12} />{c.CITY}</span>} />
              <Info k="Tenure" v={`${c.TENURE_YEARS} yrs`} />
              <Info k="Products" v={c.PRODUCT_LINES} />
              <Info k="Premium" v={inr(c.TOTAL_ANNUAL_PREMIUM)} />
              <Info k="Channel" v={c.PREFERRED_CHANNEL} />
              <Info k="Language" v={c.PREFERRED_LANGUAGE} />
              <Info k="Next renewal" v={fmtDate(c.NEXT_RENEWAL_DATE)} />
              <Info k="Days left" v={<span className={(c.DAYS_TO_RENEWAL ?? 999) <= 30 ? 'text-amber-300' : ''}>{c.DAYS_TO_RENEWAL ?? '—'}</span>} />
            </dl>
          </Card>
          <Card className="p-5" delay={0.05}>
            <div className="label">Churn risk</div>
            <div className="mt-2 flex justify-center"><RiskGauge score={Math.round(n.RISK_SCORE ?? 0)} band={n.RISK_BAND ?? 'Low'} /></div>
            <div className="mt-1 text-center text-xs text-slate-400">Premium at risk <span className="font-semibold text-amber-300">{inr(n.PREMIUM_AT_RISK)}</span></div>
          </Card>
        </div>

        {/* Center: orbit */}
        <Card className="relative col-span-12 h-[600px] overflow-hidden lg:col-span-8" delay={0.08}>
          <div className="absolute left-5 top-4 z-10">
            <div className="label">360 Orbit</div>
            <div className="text-xs text-slate-500">Drag to rotate · hover a node · click for detail</div>
          </div>
          <div className="absolute right-5 top-4 z-10 flex gap-3 text-[11px] text-slate-400">
            {(['good', 'warn', 'bad'] as const).map((h) => <span key={h} className="flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: healthColor(h) }} />{h === 'good' ? 'Healthy' : h === 'warn' ? 'Watch' : 'At risk'}</span>)}
          </div>
          <Suspense fallback={<div className="grid h-full place-items-center"><div className="skeleton h-40 w-40 rounded-full" /></div>}>
            <Orbit360 nodes={nodes} coreColor={bandColor(n.RISK_BAND)} active={active} onSelect={setActive} name={c.FULL_NAME} />
          </Suspense>
          <AnimatePresence>
            {active && (
              <motion.div initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 40, opacity: 0 }} transition={{ type: 'spring', damping: 26, stiffness: 260 }}
                className="absolute bottom-3 right-3 top-3 z-20 w-[min(340px,85%)] overflow-hidden rounded-2xl border border-white/10 bg-ink-900/90 backdrop-blur-xl">
                <DetailPanel kind={active} pols={pols} clms={clms} pays={pays} calls={calls} onClose={() => setActive(null)} onOpen={setTranscript} />
              </motion.div>
            )}
          </AnimatePresence>
        </Card>

      </div>

      <div className="grid grid-cols-12 gap-5">
        <Card className="col-span-12 p-5 lg:col-span-5" delay={0.1}>
          <div className="label">Sentiment trend</div>
          <div className="mt-1 text-xs text-slate-500">Cortex SENTIMENT on customer turns, per call</div>
          <SentimentSpark calls={calls} />
        </Card>
        <Card className="col-span-12 p-5 lg:col-span-7" delay={0.12}>
          <div className="flex items-center justify-between"><div className="label">Interaction timeline</div><div className="text-xs text-slate-500">AI summaries · intent classification</div></div>
          <Timeline calls={calls} onOpen={setTranscript} />
        </Card>
      </div>
     </div>
      {/* Right: NBA */}
      <div className="col-span-12 xl:col-span-3">
        <div className="xl:sticky xl:top-[84px]">
          <NBAPanel key={id} n={n} onOpen={(tid) => setTranscript(store!.insightById.get(tid) ?? null)} />
        </div>
      </div>
      <AnimatePresence>{transcript && <TranscriptModal t={transcript} onClose={() => setTranscript(null)} />}</AnimatePresence>
    </div>
  )
}

function Info({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="min-w-0"><dt className="text-[11px] text-slate-500">{k}</dt><dd className="truncate font-medium text-slate-200">{v}</dd></div>
}

function NBAPanel({ n, onOpen }: { n: Row; onOpen: (id: string) => void }) {
  const [copied, setCopied] = useState(false)
  const drivers: Driver[] = Array.isArray(n.RISK_DRIVERS) ? n.RISK_DRIVERS : []
  const evidence: string[] = Array.isArray(n.EVIDENCE) ? n.EVIDENCE : []
  const copy = () => { navigator.clipboard?.writeText(n.CUSTOMER_MESSAGE ?? ''); setCopied(true); setTimeout(() => setCopied(false), 1600) }
  return (
    <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
      className="glass relative h-full overflow-hidden p-5">
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-cyan-400/20 blur-3xl" />
      <div className="flex items-center gap-2"><Zap size={16} className="text-cyan-300" /><span className="label !text-cyan-300">Next best action</span></div>
      <div className="mt-1 font-mono text-[11px] text-slate-500">{n.ACTION_CATEGORY} · via {n.CHANNEL}</div>
      <div className="mt-3 text-[17px] font-bold leading-snug text-white">{n.ACTION}</div>
      <div className="mt-2 text-[13px] leading-relaxed text-slate-300">{n.REASON}</div>

      <div className="mt-4 label">Why this action</div>
      <div className="mt-2 space-y-2.5">
        {drivers.length ? drivers.map((dr, i) => {
          const max = DRIVER_MAX[dr.factor] ?? 25
          const neg = dr.points < 0
          return (
            <div key={dr.factor}>
              <div className="flex justify-between text-[12px]"><span className="text-slate-200">{dr.factor}</span><span className={`tnum font-semibold ${neg ? 'text-emerald-400' : 'text-amber-300'}`}>{neg ? '' : '+'}{dr.points.toFixed(1)}</span></div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                <motion.div initial={{ width: 0 }} animate={{ width: `${Math.min(100, (Math.abs(dr.points) / max) * 100)}%` }} transition={{ duration: 0.9, delay: 0.2 + i * 0.08 }}
                  className={`h-full rounded-full ${neg ? 'bg-emerald-400' : 'bg-gradient-to-r from-amber-400 to-risk-high'}`} />
              </div>
              <div className="mt-0.5 text-[11px] text-slate-500">{dr.detail}</div>
            </div>
          )
        }) : <div className="text-xs text-slate-500">No material risk drivers.</div>}
      </div>

      {evidence.length > 0 && (<>
        <div className="mt-4 label">Evidence</div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {evidence.map((t) => (
            <button key={t} onClick={() => onOpen(t)} className="chip border-cyan-400/30 bg-cyan-400/[0.07] font-mono text-cyan-300 transition hover:bg-cyan-400/20">
              <FileText size={11} />{t}
            </button>
          ))}
        </div>
      </>)}

      <div className="mt-4 label">Customer message</div>
      <div className="relative mt-2 rounded-xl border border-white/10 bg-ink-950/60 p-3 pr-10 text-[12.5px] leading-relaxed text-slate-200">
        {n.CUSTOMER_MESSAGE}
        <button onClick={copy} title="Copy message" className="absolute right-2 top-2 rounded-lg p-1.5 text-slate-400 transition hover:bg-white/10 hover:text-white">
          {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
        </button>
      </div>
      <div className="mt-3 flex items-center gap-1.5 text-[10.5px] text-slate-500"><Sparkles size={11} />Generated by {n.GENERATED_BY}</div>
    </motion.div>
  )
}

function SentimentSpark({ calls }: { calls: Row[] }) {
  const data = calls.map((x) => ({ t: fmtDate(x.CALL_TS), s: Number(x.SENTIMENT_SCORE), id: x.TRANSCRIPT_ID }))
  if (!data.length) return <div className="grid h-40 place-items-center text-sm text-slate-500">No calls on record</div>
  return (
    <div className="mt-3 h-40">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 6, right: 4, bottom: 0, left: -28 }}>
          <defs>
            <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#38d9f5" stopOpacity={0.45} /><stop offset="100%" stopColor="#38d9f5" stopOpacity={0} /></linearGradient>
          </defs>
          <YAxis domain={[-1, 1]} ticks={[-1, 0, 1]} tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />
          <Tooltip contentStyle={{ background: '#0a0f1c', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 12 }} labelFormatter={(_, p) => (p?.[0]?.payload ? `${p[0].payload.id} · ${p[0].payload.t}` : '')} formatter={(v) => [Number(v).toFixed(2), 'sentiment']} />
          <Area type="monotone" dataKey="s" stroke="#38d9f5" strokeWidth={2} fill="url(#sg)" dot={{ r: 3, fill: '#38d9f5', strokeWidth: 0 }} isAnimationActive />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function Timeline({ calls, onOpen }: { calls: Row[]; onOpen: (t: Row) => void }) {
  const list = [...calls].reverse()
  if (!list.length) return <div className="py-8 text-center text-sm text-slate-500">No interactions</div>
  return (
    <div className="mt-3 max-h-56 space-y-1 overflow-y-auto pr-1">
      {list.map((x, i) => {
        const s = Number(x.SENTIMENT_SCORE)
        const col = s < -0.2 ? '#ff5c6c' : s < 0.2 ? '#ffb547' : '#34d399'
        return (
          <motion.button key={x.TRANSCRIPT_ID} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }} onClick={() => onOpen(x)}
            className="group flex w-full items-start gap-3 rounded-xl px-2 py-2 text-left transition hover:bg-white/[0.04]">
            <div className="flex flex-col items-center pt-1"><span className="h-2.5 w-2.5 rounded-full" style={{ background: col, boxShadow: `0 0 8px ${col}` }} /></div>
            <div className="w-24 shrink-0"><div className="text-xs text-slate-300">{fmtDate(x.CALL_TS)}</div><div className="font-mono text-[10.5px] text-slate-500">{x.TRANSCRIPT_ID}</div></div>
            <div className="min-w-0 flex-1"><div className="text-[13px] text-slate-200">{x.SUMMARY}</div><div className="mt-1 flex gap-1.5"><IntentChip intent={x.PRIMARY_INTENT} /><span className="chip border-white/10 text-slate-400">{s.toFixed(2)}</span></div></div>
            <MessageSquareText size={14} className="mt-1 text-slate-600 group-hover:text-cyan-300" />
          </motion.button>
        )
      })}
    </div>
  )
}

function DetailPanel({ kind, pols, clms, pays, calls, onClose, onOpen }: {
  kind: string; pols: Row[]; clms: Row[]; pays: Row[]; calls: Row[]; onClose: () => void; onOpen: (t: Row) => void
}) {
  const title = { policies: 'Policies', claims: 'Claims', payments: 'Payments (latest 12)', calls: 'Call transcripts' }[kind]
  const Icon = { policies: ShieldCheck, claims: FileText, payments: Check, calls: Phone }[kind] ?? FileText
  const statusCol = (s: string) => (/reject|missed|cancel|lapse/i.test(s) ? 'text-risk-high' : /pending|review|late|grace/i.test(s) ? 'text-amber-300' : 'text-emerald-400')
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-bold text-white"><Icon size={15} className="text-cyan-300" />{title}</div>
        <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-white/5 hover:text-white"><X size={16} /></button>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-3 text-[12.5px]">
        {kind === 'policies' && pols.map((p) => (
          <div key={p.POLICY_ID} className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
            <div className="flex justify-between"><span className="font-semibold text-white">{p.PLAN_NAME}</span><span className={statusCol(p.STATUS)}>{p.STATUS}</span></div>
            <div className="font-mono text-[11px] text-slate-500">{p.POLICY_ID} · {p.PRODUCT_LINE}</div>
            <div className="mt-1 text-slate-400">Premium {inr(p.ANNUAL_PREMIUM)} · SI {inr(p.SUM_INSURED)} · renews {fmtDate(p.RENEWAL_DATE)}</div>
          </div>
        ))}
        {kind === 'claims' && (clms.length ? clms.map((x) => (
          <div key={x.CLAIM_ID} className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
            <div className="flex justify-between"><span className="font-semibold text-white">{x.CLAIM_TYPE}</span><span className={statusCol(x.STATUS)}>{x.STATUS}</span></div>
            <div className="font-mono text-[11px] text-slate-500">{x.CLAIM_ID} · {fmtDate(x.CLAIM_DATE)}</div>
            <div className="mt-1 text-slate-400">Claimed {inr(x.CLAIM_AMOUNT)} · approved {inr(x.APPROVED_AMOUNT)} · {x.DAYS_OPEN}d</div>
          </div>
        )) : <div className="p-4 text-center text-slate-500">No claims on record</div>)}
        {kind === 'payments' && [...pays].reverse().slice(0, 12).map((x) => (
          <div key={x.PAYMENT_ID} className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
            <div><div className="text-slate-200">{fmtDate(x.DUE_DATE)} · {inr(x.AMOUNT_DUE, false)}</div><div className="font-mono text-[11px] text-slate-500">{x.POLICY_ID} · {x.PAYMENT_METHOD}</div></div>
            <span className={statusCol(x.PAYMENT_STATUS)}>{x.PAYMENT_STATUS}{x.DAYS_LATE ? ` +${x.DAYS_LATE}d` : ''}</span>
          </div>
        ))}
        {kind === 'calls' && [...calls].reverse().map((x) => (
          <button key={x.TRANSCRIPT_ID} onClick={() => onOpen(x)} className="w-full rounded-xl border border-white/5 bg-white/[0.02] p-3 text-left hover:border-cyan-400/30">
            <div className="flex justify-between font-mono text-[11px] text-slate-500"><span>{x.TRANSCRIPT_ID}</span><span>{fmtDate(x.CALL_TS)}</span></div>
            <div className="mt-1 text-slate-200">{x.SUMMARY}</div>
            <div className="mt-1.5"><IntentChip intent={x.PRIMARY_INTENT} /></div>
          </button>
        ))}
      </div>
    </div>
  )
}

function Skeleton() {
  return (
    <div className="grid grid-cols-12 gap-5">
      <div className="col-span-12 space-y-5 lg:col-span-3"><div className="skeleton h-64" /><div className="skeleton h-56" /></div>
      <div className="skeleton col-span-12 h-[560px] lg:col-span-6" />
      <div className="skeleton col-span-12 h-[560px] lg:col-span-3" />
    </div>
  )
}
