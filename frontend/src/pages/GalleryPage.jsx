import { Link } from 'react-router-dom'
import PageHero from '../components/PageHero'

export default function GalleryPage() {
  return (
    <section className="gallery-page">
      <PageHero
        eyebrow="Browse the library"
        title="Gallery"
        lead="Search and browse icons live on the home page for now. This route stays ready for a dedicated gallery view."
      />
      <div className="wrap gallery-page__body">
        <p>
          Use Search in the header, or go home and scroll to the gallery grid.
        </p>
        <p>
          <Link className="btn btn-yellow" to="/#gallery">
            Open gallery search
          </Link>
        </p>
      </div>
    </section>
  )
}
