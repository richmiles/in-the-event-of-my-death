import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import CreateSecret from './pages/CreateSecret'
import ViewSecret from './pages/ViewSecret'
import EditSecret from './pages/EditSecret'
import About from './pages/About'
import PrivacyPolicy from './pages/PrivacyPolicy'
import TermsOfService from './pages/TermsOfService'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/create" element={<CreateSecret />} />
            <Route path="/view" element={<ViewSecret />} />
            <Route path="/edit" element={<EditSecret />} />
            <Route path="/about" element={<About />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/terms" element={<TermsOfService />} />
          </Routes>
        </main>

        <footer className="site-footer">
          <div className="footer-content">
            <p className="footer-line">
              <Link to="/about">About</Link>
              <span className="footer-separator">•</span>
              <Link to="/privacy">Privacy</Link>
              <span className="footer-separator">•</span>
              <Link to="/terms">Terms</Link>
            </p>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  )
}

export default App
