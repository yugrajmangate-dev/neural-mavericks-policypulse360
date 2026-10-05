import { useCallback, useEffect, useState } from 'react'

// Closed-loop write-back. The static site has no Snowflake connection, so decisions live in this browser
// (localStorage). In the Streamlit app's LIVE mode the same buttons insert into POLICYPULSE.APP.ACTION_LOG.
export type ActionStatus = 'Accepted' | 'Rejected' | 'Done'
export type ActionEntry = { customerId: string; category: string; action: string; status: ActionStatus; note: string; ts: string }

const KEY = 'pp360.actionLog.v1'
const EVENT = 'pp360-action-log'

function read(): ActionEntry[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(v) ? v : []
  } catch {
    return []
  }
}

function write(entries: ActionEntry[]) {
  try { localStorage.setItem(KEY, JSON.stringify(entries)) } catch { /* storage blocked: keep in memory only */ }
  memory = entries
  window.dispatchEvent(new Event(EVENT))
}

let memory: ActionEntry[] | null = null
const all = () => memory ?? (memory = read())

/** Latest decision per customer. */
export function latestByCustomer(entries: ActionEntry[]) {
  const m = new Map<string, ActionEntry>()
  for (const e of entries) m.set(e.customerId, e)
  return m
}

export function useActionLog() {
  const [entries, setEntries] = useState<ActionEntry[]>(all)
  useEffect(() => {
    const sync = () => setEntries([...all()])
    const fromOtherTab = (e: StorageEvent) => { if (e.key === KEY) { memory = read(); sync() } }
    window.addEventListener(EVENT, sync)
    window.addEventListener('storage', fromOtherTab)
    return () => { window.removeEventListener(EVENT, sync); window.removeEventListener('storage', fromOtherTab) }
  }, [])
  const log = useCallback((e: Omit<ActionEntry, 'ts'>) => write([...all(), { ...e, ts: new Date().toISOString() }]), [])
  const reset = useCallback(() => write([]), [])
  const latest = latestByCustomer(entries)
  const reviewed = latest.size
  const taken = [...latest.values()].filter((e) => e.status !== 'Rejected').length
  return { entries, latest, log, reset, reviewed, uptake: reviewed ? taken / reviewed : null }
}
