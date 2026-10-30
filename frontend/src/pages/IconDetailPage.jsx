import { Link, useParams } from 'react-router-dom'

export default function IconDetailPage() {
  const { uniqueId } = useParams()

  return (
    <section className="page">
      <p className="page__eyebrow">
        <Link to="/gallery">← Gallery</Link>
      </p>
      <h1>Icon detail</h1>
      <p>
        Detail view for <code>{uniqueId}</code>. Full metadata and downloads
        come in a later issue.
      </p>
    </section>
  )
}
