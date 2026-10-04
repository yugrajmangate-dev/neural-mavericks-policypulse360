import { Html, Line, OrbitControls, Sparkles } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { healthColor } from '../data'

export type OrbitNode = {
  key: string
  label: string
  count: number
  health: 'good' | 'warn' | 'bad'
  headline: string
  sub: string
}

const RINGS = [
  { r: 2.3, tilt: [0.35, 0, 0.15], phase: 0.2 },
  { r: 2.9, tilt: [-0.4, 0, -0.25], phase: 1.9 },
  { r: 3.5, tilt: [0.15, 0, 0.45], phase: 3.6 },
  { r: 4.1, tilt: [-0.2, 0, -0.5], phase: 5.0 },
] as const

function ringPoints(r: number) {
  const pts: THREE.Vector3[] = []
  for (let i = 0; i <= 96; i++) { const a = (i / 96) * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r)) }
  return pts
}

function Core({ color }: { color: string }) {
  const ref = useRef<THREE.Mesh>(null)
  const halo = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    if (ref.current) ref.current.rotation.y = t * 0.3
    if (halo.current) { const s = 1 + Math.sin(t * 1.6) * 0.06; halo.current.scale.setScalar(s) }
  })
  return (
    <group>
      <mesh ref={ref}>
        <icosahedronGeometry args={[0.85, 3]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.9} roughness={0.3} metalness={0.2} />
      </mesh>
      <mesh>
        <icosahedronGeometry args={[0.9, 1]} />
        <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.12} />
      </mesh>
      <mesh ref={halo}>
        <sphereGeometry args={[1.25, 24, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.12} depthWrite={false} />
      </mesh>
      <mesh>
        <sphereGeometry args={[1.7, 24, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.05} depthWrite={false} />
      </mesh>
    </group>
  )
}

function Node({ node, idx, active, onHover, onSelect }: {
  node: OrbitNode; idx: number; active: boolean
  onHover: (k: string | null) => void; onSelect: (k: string) => void
}) {
  const ring = RINGS[idx % RINGS.length]
  const color = healthColor(node.health)
  const size = 0.22 + Math.min(node.count, 30) * 0.012
  const pts = useMemo(() => ringPoints(ring.r), [ring.r])
  const pos = useMemo(() => new THREE.Vector3(Math.cos(ring.phase) * ring.r, 0, Math.sin(ring.phase) * ring.r), [ring])
  const sats = useRef<THREE.Group>(null)
  const nodeRef = useRef<THREE.Group>(null)
  const [hover, setHover] = useState(false)
  useFrame(({ clock }, dt) => {
    if (sats.current) sats.current.rotation.y += dt * 0.8
    if (nodeRef.current) {
      const target = hover || active ? 1.35 : 1
      const s = THREE.MathUtils.lerp(nodeRef.current.scale.x, target, 0.15)
      nodeRef.current.scale.setScalar(s)
      nodeRef.current.position.y = Math.sin(clock.getElapsedTime() * 0.9 + idx) * 0.08
    }
  })
  const nSats = Math.min(node.count, 8)
  return (
    <group rotation={ring.tilt as unknown as THREE.Euler}>
      <Line points={pts} color={color} lineWidth={1} transparent opacity={active ? 0.55 : 0.18} />
      <group position={pos}>
        <group ref={nodeRef}>
          <mesh
            onPointerOver={(e) => { e.stopPropagation(); setHover(true); onHover(node.key); document.body.style.cursor = 'pointer' }}
            onPointerOut={() => { setHover(false); onHover(null); document.body.style.cursor = '' }}
            onClick={(e) => { e.stopPropagation(); onSelect(node.key) }}>
            <icosahedronGeometry args={[size, 2]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={hover || active ? 1.2 : 0.6} roughness={0.35} />
          </mesh>
          <mesh>
            <sphereGeometry args={[size * 1.8, 16, 16]} />
            <meshBasicMaterial color={color} transparent opacity={hover || active ? 0.18 : 0.08} depthWrite={false} />
          </mesh>
          <group ref={sats}>
            {Array.from({ length: nSats }).map((_, i) => {
              const a = (i / nSats) * Math.PI * 2
              const rr = size * 2.4
              return (
                <mesh key={i} position={[Math.cos(a) * rr, Math.sin(a * 2) * 0.08, Math.sin(a) * rr]}>
                  <sphereGeometry args={[0.035, 8, 8]} />
                  <meshBasicMaterial color={color} />
                </mesh>
              )
            })}
          </group>
          <Html center distanceFactor={9} position={[0, size + 0.45, 0]} style={{ pointerEvents: 'none' }}>
            <div className="whitespace-nowrap text-center">
              <div className="text-[13px] font-bold text-white drop-shadow">{node.label}</div>
              <div className="text-[11px] font-semibold" style={{ color }}>{node.count}</div>
            </div>
          </Html>
          {hover && (
            <Html distanceFactor={9} position={[size + 0.3, 0, 0]} style={{ pointerEvents: 'none' }}>
              <div className="w-56 rounded-xl border border-white/10 bg-ink-900/95 p-3 text-left shadow-2xl backdrop-blur">
                <div className="flex items-center gap-2 text-[13px] font-bold text-white"><span className="h-2 w-2 rounded-full" style={{ background: color }} />{node.label}</div>
                <div className="mt-1 text-[12px] text-slate-200">{node.headline}</div>
                <div className="mt-0.5 text-[11px] text-slate-400">{node.sub}</div>
                <div className="mt-2 text-[10px] uppercase tracking-wider text-cyan-300">Click for detail</div>
              </div>
            </Html>
          )}
        </group>
      </group>
    </group>
  )
}

export default function Orbit360({ nodes, coreColor, active, onSelect, name }: {
  nodes: OrbitNode[]; coreColor: string; active: string | null; onSelect: (k: string) => void; name: string
}) {
  const [hovered, setHovered] = useState<string | null>(null)
  return (
    <Canvas camera={{ position: [0, 3.2, 8.6], fov: 45 }} dpr={[1, 1.75]} gl={{ antialias: true, powerPreference: 'high-performance' }}>
      <ambientLight intensity={0.35} />
      <pointLight position={[0, 0, 0]} intensity={30} color={coreColor} distance={12} />
      <pointLight position={[6, 6, 6]} intensity={40} color="#7deaff" />
      <Core color={coreColor} />
      <Html center position={[0, -1.25, 0]} distanceFactor={9} style={{ pointerEvents: 'none' }}>
        <div className="whitespace-nowrap rounded-full border border-white/10 bg-ink-900/70 px-3 py-1 text-[13px] font-bold text-white backdrop-blur">{name}</div>
      </Html>
      {nodes.map((n, i) => (
        <Node key={n.key} node={n} idx={i} active={active === n.key} onHover={setHovered} onSelect={onSelect} />
      ))}
      <Sparkles count={60} scale={12} size={1.6} speed={0.25} color="#7deaff" opacity={0.5} />
      <OrbitControls enablePan={false} enableZoom minDistance={5} maxDistance={14} autoRotate={!hovered} autoRotateSpeed={0.6} enableDamping />
    </Canvas>
  )
}
