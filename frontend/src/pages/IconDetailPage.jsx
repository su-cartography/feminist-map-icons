import { Link, useLocation, useParams } from 'react-router-dom'

export default function IconDetailPage() {
  const { uniqueId } = useParams()
  // Return to the gallery page/search the visitor came from, if any.
  const gallerySearch = useLocation().state?.gallerySearch || ''

  return (
    <section className="page">
      <p className="page__eyebrow">
        <Link to={`/${gallerySearch}#gallery`}>← Gallery</Link>
      </p>
      <h1>Icon detail</h1>
      <p>
        Detail view for <code>{uniqueId}</code>. Full metadata and downloads
        come in a later issue.
      </p>
    </section>
  )
}
