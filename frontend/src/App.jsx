import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './layout/Layout'
import ContributePage from './pages/ContributePage'
import GalleryPage from './pages/GalleryPage'
import HomePage from './pages/HomePage'
import IconDetailPage from './pages/IconDetailPage'
import ResourcesPage from './pages/ResourcesPage'
import SignInPage from './pages/SignInPage'
import './App.css'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="gallery" element={<GalleryPage />} />
        <Route path="icons/:uniqueId" element={<IconDetailPage />} />
        <Route path="resources" element={<ResourcesPage />} />
        <Route path="contribute" element={<ContributePage />} />
        <Route path="sign-in" element={<SignInPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
