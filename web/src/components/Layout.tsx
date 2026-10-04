import { AnimatePresence, motion } from 'framer-motion'
import { Command, LayoutDashboard, Orbit, Search, Workflow } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { bandColor, inr, useStore } from '../data'
import { SourceBadge } from './ui'

const NAV = [
  { to: '/customer', icon: Orbit, label: 'Customer 360' },
  { to: '/portfolio', icon: LayoutDashboard, label: 'Portfolio' },
  { to: '/pipeline', icon: Workflow, label: 'Pipeline' },
]

export default function Layout() {
  const { store, error } = useStore()
  const [open, setOpen] = useState(false)
  const loc = useLocation()
  useEffect(() => { window.scrollTo({ top: 0 }) }, [loc.pathname])
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setOpen((o) => !o) }
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  return (
    <div className="flex h-full min-h-screen">
      <aside className="sticky top-0 flex h-screen w-[68px] shrink-0 flex-col items-center gap-2 border-r border-white/5 bg-ink-950/70 py-4 backdrop-blur-xl">
        <div className="mb-4 grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-cyan-600 shadow-[0_0_24px_rgba(56,217,245,0.45)]">
          <span className="text-sm font-extrabold text-ink-950">PP</span>
        </div>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} title={label}
            className={({ isActive }) => `group relative grid h-11 w-11 place-items-center rounded-xl transition ${isActive ? 'bg-cyan-400/10 text-cyan-300' : 'text-slate-500 hover:bg-white/5 hover:text-slate-200'}`}>
            {({ isActive }) => (<>
              {isActive && <motion.span layoutId="navglow" className="absolute -left-[13px] h-6 w-[3px] rounded-r bg-cyan-400" />}
              <Icon size={20} />
              <span className="pointer-events-none absolute left-14 z-50 whitespace-nowrap rounded-md bg-ink-700 px-2 py-1 text-xs text-slate-200 opacity-0 transition group-hover:opacity-100">{label}</span>
            </>)}
          </NavLink>
        ))}
        <button onClick={() => setOpen(true)} title="Search (Ctrl/Cmd+K)" className="mt-auto grid h-11 w-11 place-items-center rounded-xl text-slate-500 hover:bg-white/5 hover:text-slate-200"><Search size={20} /></button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-white/5 bg-ink-950/70 px-6 py-3 backdrop-blur-xl">
          <div className="min-w-0">
            <div className="truncate text-[15px] font-bold tracking-tight text-white">
              PolicyPulse 360 <span className="text-slate-500">·</span> <span className="text-slate-300">Neural Mavericks</span> <span className="text-slate-500">·</span>{' '}
              <span className="bg-gradient-to-r from-cyan-300 to-sky-400 bg-clip-text text-transparent">Powered by Snowflake Cortex</span>
            </div>
            <div className="text-[11px] text-slate-500">Customer 360 + Next Best Action Command Center{store?.meta?.as_of ? ` · as of ${store.meta.as_of}` : ''}</div>
          </div>
          <button onClick={() => setOpen(true)} className="ml-auto hidden items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-400 transition hover:border-cyan-400/40 hover:text-slate-200 md:flex">
            <Search size={15} /> <span className="w-48 text-left">Find a customer…</span>
            <kbd className="flex items-center gap-0.5 rounded border border-white/10 px-1.5 text-[10px]"><Command size={10} />K</kbd>
          </button>
          <SourceBadge source={store?.meta?.source} />
        </header>

        <main className="flex-1 p-5 lg:p-6">
          {error ? <div className="glass p-6 text-risk-high">Failed to load data: {error}</div> : (
            <AnimatePresence mode="wait">
              <motion.div key={loc.pathname.split('/')[1]} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
                <Outlet />
              </motion.div>
            </AnimatePresence>
          )}
        </main>
      </div>
      <AnimatePresence>{open && <CommandK onClose={() => setOpen(false)} />}</AnimatePresence>
    </div>
  )
}

function CommandK({ onClose }: { onClose: () => void }) {
  const { store } = useStore()
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => ref.current?.focus(), [])
  const results = useMemo(() => {
    if (!store) return []
    const s = q.trim().toLowerCase()
    const list = [...store.nba].sort((a, b) => b.RISK_SCORE - a.RISK_SCORE)
    return (s ? list.filter((r) => `${r.CUSTOMER_ID} ${r.FULL_NAME} ${r.CITY} ${r.PRODUCT_LINES} ${r.SEGMENT}`.toLowerCase().includes(s)) : list).slice(0, 8)
  }, [q, store])
  const go = (id: string) => { nav(`/customer/${id}`); onClose() }
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 pt-[14vh] backdrop-blur-sm" onClick={onClose}>
      <motion.div initial={{ scale: 0.97, y: -8 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.97, opacity: 0 }} className="glass w-full max-w-xl overflow-hidden !bg-ink-900/95" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-white/5 px-4">
          <Search size={18} className="text-cyan-300" />
          <input ref={ref} value={q} onChange={(e) => { setQ(e.target.value); setSel(0) }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setSel((s) => Math.min(s + 1, results.length - 1)) }
              if (e.key === 'ArrowUp') { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)) }
              if (e.key === 'Enter' && results[sel]) go(results[sel].CUSTOMER_ID)
            }}
            placeholder="Search by name, ID, city, product…" className="h-14 flex-1 bg-transparent text-[15px] text-white outline-none placeholder:text-slate-500" />
          <kbd className="rounded border border-white/10 px-1.5 text-[10px] text-slate-500">ESC</kbd>
        </div>
        <div className="max-h-[50vh] overflow-y-auto p-2">
          {!q && <div className="label px-3 py-2">Highest churn risk</div>}
          {results.map((r, i) => (
            <button key={r.CUSTOMER_ID} onMouseEnter={() => setSel(i)} onClick={() => go(r.CUSTOMER_ID)}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left ${i === sel ? 'bg-cyan-400/10' : ''}`}>
              <span className="h-2 w-2 rounded-full" style={{ background: bandColor(r.RISK_BAND), boxShadow: `0 0 8px ${bandColor(r.RISK_BAND)}` }} />
              <span className="flex-1">
                <span className="text-sm font-semibold text-white">{r.FULL_NAME}</span>
                <span className="ml-2 font-mono text-xs text-slate-500">{r.CUSTOMER_ID}</span>
                <span className="block text-xs text-slate-400">{r.CITY} · {r.SEGMENT} · {r.PRODUCT_LINES}</span>
              </span>
              <span className="text-right">
                <span className="tnum block text-sm font-bold" style={{ color: bandColor(r.RISK_BAND) }}>{Math.round(r.RISK_SCORE)}</span>
                <span className="block text-[11px] text-slate-500">{inr(r.TOTAL_ANNUAL_PREMIUM)}</span>
              </span>
            </button>
          ))}
          {!results.length && <div className="p-6 text-center text-sm text-slate-500">No customers match "{q}"</div>}
        </div>
      </motion.div>
    </motion.div>
  )
}
