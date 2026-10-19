import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, MapPin, Store, Navigation2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

let googleMapsPromise
const SEARCH_RADIUS_KM = 10

const loadGoogleMaps = () => {
  if (window.google?.maps) return Promise.resolve(window.google.maps)
  if (googleMapsPromise) return googleMapsPromise

  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
  if (!apiKey) return Promise.reject(new Error('Google Maps API key is not configured.'))

  googleMapsPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector('script[data-google-maps]')
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(window.google.maps), { once: true })
      existingScript.addEventListener('error', () => reject(new Error('Google Maps could not be loaded.')), { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=places&v=weekly`
    script.async = true
    script.defer = true
    script.dataset.googleMaps = 'true'
    script.onload = () => resolve(window.google.maps)
    script.onerror = () => reject(new Error('Google Maps could not be loaded.'))
    document.head.appendChild(script)
  })

  return googleMapsPromise
}

const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;')

const placeInfo = (place, type) => `
  <div style="min-width:240px;font-family:system-ui;font-size:13px;">
    <h3 style="margin:0 0 4px;font-weight:bold;font-size:14px;color:#1e3a8a;">${escapeHtml(place.name)}</h3>
    <p style="margin:4px 0;color:#666;font-size:12px;">${escapeHtml(place.desc || type)}</p>
    <p style="margin:4px 0;color:#666;font-size:12px;">${escapeHtml(place.distance_km)} km away</p>
    <p style="margin:4px 0;color:#666;font-size:12px;">${escapeHtml(place.phone)}</p>
    <div style="margin-top:8px;display:flex;gap:4px;">
      <a href="https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lng}" target="_blank" rel="noreferrer" style="background:#4285f4;color:white;padding:6px 8px;border-radius:4px;text-decoration:none;font-size:12px;flex:1;text-align:center;">Directions</a>
      <a href="${place.maps_url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name)}`}" target="_blank" rel="noreferrer" style="background:#34a853;color:white;padding:6px 8px;border-radius:4px;text-decoration:none;font-size:12px;flex:1;text-align:center;">View</a>
    </div>
  </div>
`

const distanceKm = (from, to) => {
  const latDistance = (to.lat - from.lat) * Math.PI / 180
  const lngDistance = (to.lng - from.lng) * Math.PI / 180
  const a = Math.sin(latDistance / 2) ** 2
    + Math.cos(from.lat * Math.PI / 180) * Math.cos(to.lat * Math.PI / 180) * Math.sin(lngDistance / 2) ** 2
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

const searchPlaces = (service, request) => new Promise((resolve, reject) => {
  service.textSearch(request, (results, status) => {
    if (status === window.google.maps.places.PlacesServiceStatus.OK) resolve(results || [])
    else if (status === window.google.maps.places.PlacesServiceStatus.ZERO_RESULTS) resolve([])
    else reject(new Error(`Google Places search failed: ${status}`))
  })
})

const normalizeGooglePlace = (place, userPos, type) => {
  const location = place.geometry?.location
  if (!location) return null
  const lat = typeof location.lat === 'function' ? location.lat() : location.lat
  const lng = typeof location.lng === 'function' ? location.lng() : location.lng
  return {
    name: place.name,
    lat,
    lng,
    type,
    desc: type === 'clinic' ? 'Dermatology clinic listed on Google Maps.' : 'Retailer listed on Google Maps. Confirm product stock before visiting.',
    distance_km: Number(distanceKm(userPos, { lat, lng }).toFixed(1)),
    address: place.formatted_address || place.vicinity || 'Address unavailable',
    phone: place.formatted_phone_number || 'Phone unavailable',
    place_id: place.place_id,
    maps_url: place.url
  }
}

export default function MapPage() {
  const navigate = useNavigate()
  const mapContainerRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markerRefs = useRef([])
  
  const [userPos, setUserPos] = useState(null)
  const [clinics, setClinics] = useState([])
  const [stores, setStores] = useState([])
  const [nearestClinic, setNearestClinic] = useState(null)
  const [nearestStore, setNearestStore] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [locationPermission, setLocationPermission] = useState('')

  const loadUserLocation = async () => {
    setLoading(true)
    setError('')

    if (!navigator.geolocation) {
      setError('Location services are not supported by this browser.')
      setLoading(false)
      return
    }

    try {
      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 20000,
          maximumAge: 60000
        })
      })
      const { latitude, longitude } = position.coords
      setUserPos({ lat: latitude, lng: longitude })
      setLocationPermission('granted')
      await fetchNearbyPlaces(latitude, longitude)
    } catch (err) {
      console.warn('Geolocation error:', err.code, err.message)
      setUserPos(null)
      setClinics([])
      setStores([])
      setNearestClinic(null)
      setNearestStore(null)
      setLocationPermission(err.code === 1 ? 'denied' : 'unavailable')
      setError(err.code === 1
        ? 'Location access is blocked. Allow location access in your browser, then retry.'
        : 'Could not determine your location. Check your device location settings and retry.')
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUserLocation()
  }, [])

  // Fetch nearby places from backend
  const fetchNearbyPlaces = async (lat, lng) => {
    try {
      await loadGoogleMaps()
      const service = new window.google.maps.places.PlacesService(document.createElement('div'))
      const products = JSON.parse(localStorage.getItem('sk_latest_products') || '[]')
      const productTerms = products.slice(0, 3).map(product => product.name).join(' ')
      const [clinicResults, storeResults] = await Promise.all([
        searchPlaces(service, { location: { lat, lng }, radius: SEARCH_RADIUS_KM * 1000, query: 'dermatology clinic' }),
        searchPlaces(service, { location: { lat, lng }, radius: SEARCH_RADIUS_KM * 1000, query: `${productTerms || 'skincare products'} pharmacy beauty store` })
      ])
      const googleClinics = clinicResults.map(place => normalizeGooglePlace(place, { lat, lng }, 'clinic')).filter(Boolean)
      const googleStores = storeResults.map(place => normalizeGooglePlace(place, { lat, lng }, 'store')).filter(Boolean)
      const withinSearchRadius = places => places
        .filter(place => place.distance_km <= SEARCH_RADIUS_KM)
        .sort((a, b) => a.distance_km - b.distance_km)
        .slice(0, 10)
      const nextClinics = withinSearchRadius(googleClinics)
      const nextStores = withinSearchRadius(googleStores)
      setClinics(nextClinics)
      setStores(nextStores)
      setNearestClinic(nextClinics[0] || null)
      setNearestStore(nextStores[0] || null)
    } catch (err) {
      console.error('Failed to fetch nearby places:', err)
      setClinics([])
      setStores([])
      setNearestClinic(null)
      setNearestStore(null)
      setError(err.message.includes('REQUEST_DENIED')
        ? 'Google Places denied the request. Enable billing and the Places API for the Google Cloud project used by this app, then check the API key restrictions.'
        : 'Live nearby places could not be loaded. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!userPos || loading) return

    let cancelled = false
    loadGoogleMaps().then(() => {
      if (!cancelled) renderMap()
    }).catch(err => {
      if (!cancelled) {
        setError(err.message)
        setLoading(false)
      }
    })

    return () => {
      cancelled = true
      markerRefs.current.forEach(marker => marker.setMap(null))
      markerRefs.current = []
      mapInstanceRef.current = null
    }
  }, [userPos, clinics, stores, loading])

  const renderMap = () => {
    const { Map, Marker, InfoWindow, SymbolPath } = window.google.maps
    const mapInstance = new Map(mapContainerRef.current, {
      center: userPos,
      zoom: 12,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: true,
      gestureHandling: 'greedy'
    })
    const infoWindow = new InfoWindow()
    const markerIcon = (color, scale) => ({ path: SymbolPath.CIRCLE, fillColor: color, fillOpacity: 1, strokeColor: '#ffffff', strokeWeight: 3, scale })
    const addMarker = (place, color, scale, content) => {
      const marker = new Marker({ map: mapInstance, position: { lat: Number(place.lat), lng: Number(place.lng) }, title: place.name, icon: markerIcon(color, scale) })
      marker.addListener('click', () => { infoWindow.setContent(content); infoWindow.open({ map: mapInstance, anchor: marker }) })
      markerRefs.current.push(marker)
    }
    const userMarker = new Marker({ map: mapInstance, position: userPos, title: 'Your location', icon: markerIcon('#3b82f6', 9) })
    markerRefs.current.push(userMarker)
    clinics.forEach(clinic => addMarker(clinic, '#1e3a8a', 8, placeInfo(clinic, 'Dermatology clinic')))
    stores.forEach(store => addMarker(store, '#059669', 7, placeInfo(store, 'Skincare products available')))
    mapInstanceRef.current = mapInstance
  }

  return (
    <div className="nearby-care-page flex flex-col bg-skin-bg app-screen">
      {/* Header */}
      <div className="px-4 sm:px-5 py-3.5 border-b border-skin-border flex items-center gap-3 bg-skin-bg sticky top-0 z-10">
        <button onClick={() => navigate('/chat')} className="w-10 h-10 rounded-xl bg-skin-card border border-skin-border flex items-center justify-center hover:bg-skin-a1/30 transition-colors">
          <ArrowLeft size={16} className="text-skin-muted" />
        </button>
        <div>
          <p className="font-semibold text-base sm:text-lg text-skin-text">Nearest Clinics & Stores</p>
          <p className="text-xs sm:text-sm text-skin-muted">Real-time locations • Tap markers for details</p>
        </div>
      </div>

      {/* Map Container */}
      <div 
        ref={mapContainerRef}
        id="map-container" 
        className="nearby-care-map flex-1 min-h-[320px] rounded-t-3xl -mt-3 sm:-mt-4 mx-2 sm:mx-3 bg-gray-100"
      />

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-10 px-4 sm:px-5 bg-skin-bg border-t border-skin-border">
          <div className="w-12 h-12 rounded-full border-4 border-skin-a2 border-t-transparent animate-spin mb-4" />
          <p className="text-skin-text text-center font-medium">Getting your location...</p>
          <p className="text-xs text-skin-muted mt-2">Finding nearby clinics and stores</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="p-4 sm:p-5 text-center bg-skin-bg border-t border-skin-border">
          <p className="text-skin-text mb-3">{error}</p>
          <button 
            onClick={loadUserLocation} 
            className="text-xs px-4 py-2 rounded-full bg-skin-card border border-skin-border text-skin-a2 hover:bg-skin-a1/30 transition-colors"
          >
            Retry Location
          </button>
        </div>
      )}

      {!loading && !error && !nearestClinic && !nearestStore && (
        <div className="p-4 text-center bg-skin-bg border-t border-skin-border text-skin-muted">
          No skincare shops or dermatology clinics found within {SEARCH_RADIUS_KM} km.
        </div>
      )}

      {/* Nearest Summary */}
      {!loading && (nearestClinic || nearestStore) && (
        <div className="px-4 sm:px-5 py-4 space-y-3 bg-skin-bg border-t border-skin-border pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <p className="text-xs text-skin-muted font-medium uppercase tracking-wide">📍 Nearest Options</p>
          
          {nearestClinic && (
            <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer" 
              onClick={() => window.open(`https://www.google.com/maps/place/${nearestClinic.lat},${nearestClinic.lng}`)}>
              <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center flex-shrink-0">
                <MapPin size={18} className="text-indigo-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm text-skin-text truncate">{nearestClinic.name}</p>
                <p className="text-xs text-indigo-700 mt-0.5">🏥 Dermatology Clinic</p>
                <p className="text-xs font-medium text-skin-muted mt-1">📍 {nearestClinic.distance_km} km • {nearestClinic.address}</p>
              </div>
            </div>
          )}

          {nearestStore && (
            <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => window.open(`https://www.google.com/maps/place/${nearestStore.lat},${nearestStore.lng}`)}>
              <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
                <Store size={18} className="text-emerald-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm text-skin-text truncate">{nearestStore.name}</p>
                <p className="text-xs text-emerald-700 mt-0.5">🛒 Skincare & Wellness Products</p>
                <p className="text-xs font-medium text-skin-muted mt-1">📍 {nearestStore.distance_km} km • {nearestStore.address}</p>
              </div>
            </div>
          )}

          {locationPermission === 'denied' && (
            <p className="text-xs text-center text-skin-muted pt-2 border-t border-skin-border">
              💡3 Enable location in your browser for the most accurate results
            </p>
          )}
        </div>
      )}
    </div>
  )
}
