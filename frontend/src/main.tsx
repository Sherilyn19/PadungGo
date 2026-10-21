import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Self-hosted pixel display face (SIL OFL); bundled, so no third-party font requests.
import '@fontsource/pixelify-sans/500.css'
import '@fontsource/pixelify-sans/600.css'
import '@fontsource/pixelify-sans/700.css'
import App from './App.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
