import { Link } from 'react-router-dom'

export default function ContributePage() {
  return (
    <section className="page wrap">
      <h1>Contribute</h1>
      <p>
        There are two ways to contribute feminist map icons: upload an existing
        drawing, or create one in the browser. Full upload and create flows come
        in a later milestone.
      </p>
      <div className="actions actions--start">
        <button type="button" className="btn" disabled>
          Upload (soon)
        </button>
        <button type="button" className="btn btn-yellow" disabled>
          Create (soon)
        </button>
      </div>
      <p>
        <Link to="/">← Back to home</Link>
      </p>
    </section>
  )
}
