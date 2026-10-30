import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './layout/Layout'
import GalleryPage from './pages/GalleryPage'
import HomePage from './pages/HomePage'
import IconDetailPage from './pages/IconDetailPage'
import './App.css'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="gallery" element={<GalleryPage />} />
        <Route path="icons/:uniqueId" element={<IconDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
