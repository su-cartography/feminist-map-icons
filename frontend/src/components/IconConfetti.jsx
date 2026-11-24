import { useEffect, useState } from 'react'

// Layouts match su-cartography/website floating map icon confetti.
const LAYOUTS = [
  { left: '4%', top: '10%', size: '3rem', dur: '7s', delay: '0s', dx: '34px', dy: '-44px', rot: '-8deg' },
  { left: '12%', top: '58%', size: '2.5rem', dur: '8s', delay: '-2s', dx: '-28px', dy: '-36px', rot: '10deg' },
  { left: '78%', top: '8%', size: '3.3rem', dur: '9s', delay: '-1s', dx: '24px', dy: '32px', rot: '-4deg' },
  { left: '88%', top: '42%', size: '2.8rem', dur: '7.5s', delay: '-3s', dx: '-36px', dy: '-30px', rot: '14deg' },
  { left: '92%', top: '72%', size: '3.1rem', dur: '8.5s', delay: '-0.5s', dx: '22px', dy: '-48px', rot: '-12deg' },
  { left: '6%', top: '82%', size: '2.6rem', dur: '8s', delay: '-4s', dx: '30px', dy: '24px', rot: '6deg' },
  { left: '18%', top: '28%', size: '2.9rem', dur: '9.5s', delay: '-1.5s', dx: '-20px', dy: '-40px', rot: '-16deg' },
  { left: '70%', top: '26%', size: '2.4rem', dur: '6.5s', delay: '-2.5s', dx: '38px', dy: '22px', rot: '8deg' },
]

function shufflePick(list, count) {
  const copy = list.slice()
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    const tmp = copy[i]
    copy[i] = copy[j]
    copy[j] = tmp
  }
  return copy.slice(0, count)
}

function proxiedUrl(url) {
  if (!url) return ''
  try {
    const parsed = new URL(url, window.location.origin)
    return `${parsed.pathname}${parsed.search}`
  } catch {
    return url
  }
}

export function useConfettiIcons() {
  const [pool, setPool] = useState([])

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return undefined
    }

    const controller = new AbortController()
    fetch('/api/icons/?page=1', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Could not load confetti icons')
        return response.json()
      })
      .then((data) => {
        const withPng = (data.results || []).filter((icon) => icon.png_file)
        setPool(shufflePick(withPng, 12))
      })
      .catch((error) => {
        if (error.name !== 'AbortError') console.warn(error)
      })

    return () => controller.abort()
  }, [])

  return pool
}

export default function IconConfetti({ icons, count = 8, hostIndex = 0 }) {
  if (!icons?.length) return null

  return (
    <div className="icon-confetti" aria-hidden="true">
      {Array.from({ length: count }, (_, index) => {
        const icon = icons[index % icons.length]
        const layout = LAYOUTS[(index + hostIndex * 3) % LAYOUTS.length]
        const preferSvg = index % 2 === 1
        const src = proxiedUrl(
          preferSvg && icon.svg_file ? icon.svg_file : icon.png_file,
        )
        if (!src) return null
        return (
          <img
            key={`${icon.unique_id}-${index}`}
            src={src}
            alt=""
            loading="lazy"
            draggable={false}
            className={preferSvg && icon.svg_file ? 'is-svg' : 'is-png'}
            style={{
              left: layout.left,
              top: layout.top,
              width: layout.size,
              '--dur': layout.dur,
              '--delay': layout.delay,
              '--dx': layout.dx,
              '--dy': layout.dy,
              '--rot': layout.rot,
            }}
          />
        )
      })}
    </div>
  )
}
