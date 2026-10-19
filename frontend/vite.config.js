import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import https from 'https'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dir = path.dirname(fileURLToPath(import.meta.url))

// ── Load self-signed cert for HTTPS ────────────────────────────────────
function getHttpsConfig() {
  const certDir = path.join(__dir, '.certs')
  const keyFile = path.join(certDir, 'key.pem')
  const certFile = path.join(certDir, 'cert.pem')
  
  // If both files exist, use them
  if (fs.existsSync(keyFile) && fs.existsSync(certFile)) {
    try {
      return {
        key: fs.readFileSync(keyFile),
        cert: fs.readFileSync(certFile)
      }
    } catch (err) {
      console.error('Error reading cert files:', err.message)
      return null
    }
  }
  
  console.log('\n  HTTPS certs not found. To enable local HTTPS testing:')
  console.log('   1. Run: node generate-certs.js')
  console.log('   2. Then restart: npm run dev\n')
  return null
}

const httpsConfig = getHttpsConfig()

export default defineConfig({
  plugins: [react()],
  server: { 
    port: 3001,
    host: '0.0.0.0',
    ...(httpsConfig ? { https: httpsConfig } : {}),
    proxy: { 
      '/api': { 
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      } 
    }
  }
})
