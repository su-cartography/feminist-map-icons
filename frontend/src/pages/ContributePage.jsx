import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function ContributePage() {
  const { token } = useAuth()

  // Signed-out visitors should land on the auth page first.
  if (!token) return <Navigate to="/sign-in" replace />

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
