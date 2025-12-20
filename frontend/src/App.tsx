import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import CreateSecret from './pages/CreateSecret'
import ViewSecret from './pages/ViewSecret'
import EditSecret from './pages/EditSecret'
import About from './pages/About'
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
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/create" element={<CreateSecret />} />
            <Route path="/view" element={<ViewSecret />} />
            <Route path="/edit" element={<EditSecret />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>

        <footer>
          <div className="footer-content">
            <div className="footer-links">
              <Link to="/about">About</Link>
              <span className="footer-separator">|</span>
              <a
                href="https://github.com/richmiles/in-the-event-of-my-death"
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Source
              </a>
            </div>
            <p>Built with end-to-end encryption. Your data stays yours.</p>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  )
}

export default App
