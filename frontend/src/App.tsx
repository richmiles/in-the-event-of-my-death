import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import CreateSecret from './pages/CreateSecret'
import ViewSecret from './pages/ViewSecret'
import EditSecret from './pages/EditSecret'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header>
          <nav>
            <Link to="/" className="logo">
              In The Event Of My Death
            </Link>
            <Link to="/create" className="nav-link">
              Create Secret
            </Link>
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/create" element={<CreateSecret />} />
            <Route path="/view" element={<ViewSecret />} />
            <Route path="/edit" element={<EditSecret />} />
          </Routes>
        </main>

        <footer>
          <p>Your secrets are encrypted in your browser. We never see the plaintext.</p>
        </footer>
      </div>
    </BrowserRouter>
  )
}

export default App
