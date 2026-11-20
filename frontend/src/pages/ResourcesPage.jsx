import { useEffect, useState } from 'react'

const RESOURCE_GROUPS = [
  {
    title: 'Teaching and Workshop Guides',
    body: 'What is feminist mapping and where can we start? Incorporate feminist map icon design into your classroom or workshop.',
    links: [
      {
        label: 'Lesson Plan',
        href: 'https://bplmaps.notion.site/Workshop-Mapping-Boston-through-Place-1fcf8441f2ed80c88074ee378a38d987',
      },
      {
        label: 'Slides',
        href: 'https://drive.google.com/file/d/1bfljH8BsObsGWdxe0JEuTCE4RE51-mjF/view?usp=sharing',
      },
      {
        label: 'Materials',
        href: 'https://labs.mapbox.com/maki-icons/',
      },
    ],
  },
  {
    title: 'Resources',
    body: 'Relevant reading, links, examples, and related work.',
    links: [
      {
        label: 'Feminist Icon Design',
        href: 'https://utppublishing.com/doi/10.3138/cart-2025-0006',
      },
      {
        label: 'Map Icons and Bodies',
        href: 'https://www.tandfonline.com/doi/abs/10.1080/2373566X.2021.1883455',
      },
      {
        label: 'Data Feminism',
        href: 'https://data-feminism.mitpress.mit.edu/',
      },
    ],
  },
  {
    title: 'QGIS Plugin Repository',
    body: 'Install the latest stable galleryofpossibilities plugin from the official QGIS plugins site.',
    links: [
      {
        label: 'galleryofpossibilities on QGIS',
        href: 'https://plugins.qgis.org/plugins/galleryofpossibilities/',
      },
    ],
  },
]

export default function ResourcesPage() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      requestAnimationFrame(() => setVisible(true))
    })
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <section className={visible ? 'resources-page wrap is-in' : 'resources-page wrap'}>
      <div className="resources-hero">
        <p className="resources-hero__eyebrow">Gallery of Possibilities</p>
        <h1>Resources</h1>
        <p className="resources-hero__lead">
          Teaching guides, readings, and documentation for the gallery and QGIS
          plugin.
        </p>
      </div>

      <ul className="resources-grid">
        {RESOURCE_GROUPS.map((group, index) => (
          <li
            key={group.title}
            className="resources-card"
            style={{ '--r': index }}
          >
            <h2>{group.title}</h2>
            <p>{group.body}</p>
            <div className="resources-card__links">
              {group.links.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {link.label}
                  <span aria-hidden="true">↗</span>
                </a>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
