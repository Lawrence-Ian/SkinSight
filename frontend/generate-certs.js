import forge from 'node-forge'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const certDir = path.join(__dirname, '.certs')

console.log('📁 Certificate directory:', certDir)

// Ensure directory exists
if (!fs.existsSync(certDir)) {
  console.log('Creating .certs directory...')
  fs.mkdirSync(certDir, { recursive: true })
}

const keyFile = path.join(certDir, 'key.pem')
const certFile = path.join(certDir, 'cert.pem')

// Check if already exist
if (fs.existsSync(keyFile) && fs.existsSync(certFile)) {
  console.log('✓ HTTPS certificates already exist')
  process.exit(0)
}

console.log('🔐 Generating self-signed HTTPS certificates...')

try {
  // Generate RSA key pair
  const pki = forge.pki
  const keys = pki.rsa.generateKeyPair(2048)
  
  // Create certificate
  const cert = pki.createCertificate()
  cert.publicKey = keys.publicKey
  cert.serialNumber = '01'
  cert.validity.notBefore = new Date()
  cert.validity.notAfter = new Date()
  cert.validity.notAfter.setFullYear(cert.validity.notAfter.getFullYear() + 1)
  
  const attrs = [
    { name: 'commonName', value: 'localhost' },
    { name: 'organizationName', value: 'Development' },
    { name: 'countryName', value: 'US' }
  ]
  cert.setSubject(attrs)
  cert.setIssuer(attrs)
  cert.setExtensions([
    { name: 'basicConstraints', cA: true },
    { name: 'keyUsage', keyCertSign: true, digitalSignature: true },
    { name: 'subjectAltName', altNames: [
      { type: 2, value: 'localhost' },
      { type: 2, value: '127.0.0.1' },
      { type: 7, ip: '127.0.0.1' }
    ]}
  ])
  
  // Self-sign certificate
  cert.sign(keys.privateKey, forge.md.sha256.create())
  
  // Convert to PEM format
  const privateKeyPem = pki.privateKeyToPem(keys.privateKey)
  const certPem = pki.certificateToPem(cert)
  
  console.log('Writing certificate files...')
  fs.writeFileSync(keyFile, privateKeyPem)
  fs.writeFileSync(certFile, certPem)
  
  console.log('✓ Certificates generated successfully!')
  console.log(`  Key:  ${keyFile}`)
  console.log(`  Cert: ${certFile}`)
  console.log('')
  console.log('⚠️  Browser Warning: This is a self-signed certificate.')
  console.log('   When you first access the app, you may see a security warning.')
  console.log('   Click "Advanced" or "Proceed" - this is normal for development.')
} catch (err) {
  console.error('❌ Failed to generate certificates:', err.message)
  process.exit(1)
}
