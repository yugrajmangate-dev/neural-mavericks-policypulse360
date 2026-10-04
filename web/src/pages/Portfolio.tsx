import { motion } from 'framer-motion'
import { AlertTriangle, IndianRupee, Smile, Users } from 'lucide-react'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BandPill, Card, CountUp } from '../components/ui'
import { bandColor, inr, INTENT_COLORS, intentLabel, useStore } from '../data'

const tip = { background: '#0a0f1c', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 12, color: '#e2e8f0' }

export default function Portfolio() {
  const { store } = useStore()
  const nav = useNavigate()
  const top = useMemo(() => store ? [...store.nba].sort((a, b) => (b.PREMIUM_AT_RISK ?? 0) - (a.PREMIUM_AT_RISK ?? 0) || b.RISK_SCORE - a.RISK_SCORE).filter((r) => r.RISK_BAND !== 'Low').slice(0, 20) : [], [store])
  if (!store) return <div className="grid grid-cols-4 gap-5">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-28" />)}<div className="skeleton col-span-4 h-80" /></div>
  const p = store.portfolio
  const intents = Object.entries(p.intents).map(([k, v]) => ({ name: k, value: v }))
  const bands = ['High', 'Medium', 'Low'].map((b) => ({ name: b, value: p.risk_bands[b] ?? 0 }))

  const kpis = [
    { label: 'Customers', icon: Users, value: p.n_customers, fmt: (n: number) => Math.round(n).toLocaleString('en-IN'), accent: '#38d9f5', sub: `${p.n_transcripts} call transcripts analysed` },
    { label: 'High risk', icon: AlertTriangle, value: p.pct_high_risk, fmt: (n: number) => `${n.toFixed(1)}%`, accent: '#ff5c6c', sub: `${p.risk_bands.High} customers score ≥ 55` },
    { label: 'Premium at risk', icon: IndianRupee, value: p.premium_at_risk, fmt: (n: number) => inr(n), accent: '#ffb547', sub: `of ${inr(p.total_premium)} total annual premium` },
    { label: 'Avg sentiment', icon: Smile, value: p.avg_sentiment, fmt: (n: number) => n.toFixed(2), accent: p.avg_sentiment < 0 ? '#ffb547' : '#34d399', sub: 'Cortex SENTIMENT, scale −1 to +1' },
  ]

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-5 xl:grid-cols-4">
        {kpis.map((k, i) => (
          <Card key={k.label} className="relative overflow-hidden p-5" delay={i * 0.06}>
            <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full blur-3xl" style={{ background: k.accent + '30' }} />
            <div className="flex items-center justify-between"><span className="label">{k.label}</span><k.icon size={16} style={{ color: k.accent }} /></div>
            <div className="mt-2 text-3xl font-extrabold text-white"><CountUp value={k.value} format={k.fmt} /></div>
            <div className="mt-1 text-xs text-slate-500">{k.sub}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-5">
        <Card className="col-span-12 p-5 lg:col-span-5" delay={0.15}>
          <div className="label">Churn-risk distribution</div>
          <div className="mt-1 text-xs text-slate-500">Customers by explainable risk score (0–100)</div>
          <div className="mt-3 h-56">
            <ResponsiveContainer>
              <BarChart data={p.risk_histogram} margin={{ left: -20, right: 0, top: 4 }}>
                <XAxis dataKey="bucket" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tip} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {p.risk_histogram.map((h) => { const lo = parseInt(h.bucket); return <Cell key={h.bucket} fill={lo >= 55 || lo >= 50 ? '#ff5c6c' : lo >= 30 ? '#ffb547' : '#34d399'} /> })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex gap-2">
            {bands.map((b) => <div key={b.name} className="flex-1 rounded-xl border border-white/5 bg-white/[0.02] p-2 text-center"><div className="text-lg font-bold" style={{ color: bandColor(b.name) }}>{b.value}</div><div className="text-[11px] text-slate-500">{b.name}</div></div>)}
          </div>
        </Card>

        <Card className="col-span-12 p-5 lg:col-span-4" delay={0.2}>
          <div className="label">Call intent mix</div>
          <div className="mt-1 text-xs text-slate-500">Cortex AI_CLASSIFY over {p.n_transcripts} transcripts</div>
          <div className="relative mt-2 h-52">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={intents} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="92%" paddingAngle={2} stroke="none">
                  {intents.map((d) => <Cell key={d.name} fill={INTENT_COLORS[d.name] ?? '#64748b'} />)}
                </Pie>
                <Tooltip contentStyle={tip} formatter={(v, n) => [v, intentLabel(String(n))]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 grid place-items-center text-center"><div><div className="text-2xl font-extrabold text-white">{p.n_transcripts}</div><div className="text-[11px] text-slate-500">calls</div></div></div>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11.5px]">
            {intents.map((d) => <div key={d.name} className="flex items-center gap-1.5 capitalize text-slate-300"><span className="h-2 w-2 rounded-full" style={{ background: INTENT_COLORS[d.name] }} />{intentLabel(d.name)}<span className="ml-auto tnum text-slate-500">{d.value}</span></div>)}
          </div>
        </Card>

        <Card className="col-span-12 p-5 lg:col-span-3" delay={0.25}>
          <div className="label">Recommended plays</div>
          <div className="mt-1 text-xs text-slate-500">Next best action by category</div>
          <div className="mt-3 space-y-2">
            {Object.entries(p.actions).map(([k, v], i) => {
              const max = Math.max(...Object.values(p.actions))
              return (
                <div key={k}>
                  <div className="flex justify-between text-[11.5px]"><span className="font-mono text-slate-300">{k}</span><span className="tnum text-slate-500">{v}</span></div>
                  <div className="mt-1 h-1.5 rounded-full bg-white/[0.05]"><motion.div initial={{ width: 0 }} animate={{ width: `${(v / max) * 100}%` }} transition={{ duration: 0.8, delay: 0.3 + i * 0.05 }} className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-cyan-300" /></div>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden" delay={0.3}>
        <div className="flex items-center justify-between px-5 pt-5"><div><div className="label">Top 20 at-risk customers</div><div className="text-xs text-slate-500">Ranked by premium at risk · click a row to open the 360 view</div></div></div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-[13px]">
            <thead className="border-y border-white/5 bg-white/[0.02] text-[11px] uppercase tracking-wider text-slate-500">
              <tr><th className="px-5 py-2.5">Customer</th><th>Segment</th><th>Products</th><th>Risk</th><th>Renewal</th><th className="text-right">Premium at risk</th><th className="px-5">Next best action</th></tr>
            </thead>
            <tbody>
              {top.map((r, i) => (
                <motion.tr key={r.CUSTOMER_ID} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 + i * 0.02 }} onClick={() => nav(`/customer/${r.CUSTOMER_ID}`)}
                  className="cursor-pointer border-b border-white/[0.04] transition hover:bg-cyan-400/[0.05]">
                  <td className="px-5 py-2.5"><div className="font-semibold text-white">{r.FULL_NAME}</div><div className="font-mono text-[11px] text-slate-500">{r.CUSTOMER_ID} · {r.CITY}</div></td>
                  <td className="text-slate-300">{r.SEGMENT}</td>
                  <td className="text-slate-300">{r.PRODUCT_LINES}</td>
                  <td><div className="flex items-center gap-2"><span className="tnum w-6 font-bold" style={{ color: bandColor(r.RISK_BAND) }}>{Math.round(r.RISK_SCORE)}</span><BandPill band={r.RISK_BAND} /></div></td>
                  <td className={`tnum ${(r.DAYS_TO_RENEWAL ?? 999) <= 30 ? 'text-amber-300' : 'text-slate-400'}`}>{r.DAYS_TO_RENEWAL != null ? `${r.DAYS_TO_RENEWAL}d` : '—'}</td>
                  <td className="tnum text-right font-semibold text-amber-300">{inr(r.PREMIUM_AT_RISK)}</td>
                  <td className="max-w-[280px] truncate px-5 text-slate-300" title={r.ACTION}><span className="mr-2 font-mono text-[10.5px] text-cyan-300">{r.ACTION_CATEGORY}</span>{r.ACTION}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
