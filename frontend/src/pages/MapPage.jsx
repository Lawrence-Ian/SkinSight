import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, MapPin, Store } from 'lucide-react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useNavigate } from 'react-router-dom'
import { locationsAPI } from '../utils/api'

const SEARCH_RADIUS_KM = 5
const RESULT_LIMIT = 5

const markerIcon = (color) => L.divIcon({
  className: 'nearby-care-marker',
  html: `<span style="background:${color}"></span>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  popupAnchor: [0, -12]
})

const userIcon = L.divIcon({
  className: 'nearby-care-user-marker',
  html: '<span></span>',
  iconSize: [20, 20],
  iconAnchor: [10, 10]
})

const osmPlaceUrl = (place) => (
  place.osm_url || `https://www.openstreetmap.org/?mlat=${place.lat}&mlon=${place.lng}#map=18/${place.lat}/${place.lng}`
)

const directionsUrl = (place, userPos) => (
  `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${userPos.lat},${userPos.lng};${place.lat},${place.lng}`
)

const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;')

const popupContent = (place, type, userPos) => {
  const name = escapeHtml(place.name || 'Unnamed place')
  const address = escapeHtml(place.address || 'Address unavailable')
  const distance = escapeHtml(place.distance_km)
  const category = type === 'clinic' ? 'Clinic or hospital' : 'Skincare shop or pharmacy'
  return `
    <div class="nearby-care-popup">
      <strong>${name}</strong>
      <span>${category}</span>
      <span>${distance} km away</span>
      <span>${address}</span>
      <div>
        <a href="${directionsUrl(place, userPos)}" target="_blank" rel="noreferrer">Directions</a>
        <a href="${osmPlaceUrl(place)}" target="_blank" rel="noreferrer">View on OSM</a>
      </div>
    </div>
  `
}

export default function MapPage() {
  const navigate = useNavigate()
  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])
  const [userPos, setUserPos] = useState(null)
  const [clinics, setClinics] = useState([])
  const [stores, setStores] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [locationPermission, setLocationPermission] = useState('')

  const clearMarkers = () => {
    markersRef.current.forEach(marker => marker.remove())
    markersRef.current = []
  }

  const loadNearbyPlaces = async (lat, lng) => {
    setLoading(true)
    setError('')
    try {
      const response = await locationsAPI.nearby(lat, lng, SEARCH_RADIUS_KM)
      if (!Array.isArray(response.data?.clinics) || !Array.isArray(response.data?.stores)) {
        throw new Error('The nearby locations response was invalid.')
      }
      setClinics(response.data.clinics.slice(0, RESULT_LIMIT))
      setStores(response.data.stores.slice(0, RESULT_LIMIT))
    } catch (err) {
      console.error('Nearby OpenStreetMap API error:', err)
      setClinics([])
      setStores([])
      setError(err.response?.data?.detail || err.message || 'Nearby locations could not be loaded. Check your connection and retry.')
    } finally {
      setLoading(false)
    }
  }

  const loadUserLocation = async () => {
    setLoading(true)
    setError('')
    setClinics([])
    setStores([])
    setUserPos(null)
    if (!window.isSecureContext) {
      setLocationPermission('unavailable')
      setError('Location access requires a secure connection (HTTPS). Open this page using HTTPS or localhost, then retry.')
      setLoading(false)
      return
    }
    if (!navigator.geolocation) {
      setLocationPermission('unavailable')
      setError('Location services are not supported by this browser.')
      setLoading(false)
      return
    }

    let position
    try {
      position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 20000,
          maximumAge: 0
        })
      })
    } catch (err) {
      console.warn('Location error:', err.code, err.message)
      setLocationPermission(err.code === 1 ? 'denied' : 'unavailable')
      const locationErrors = {
        1: 'Location access is blocked. Allow location access in your browser, then retry.',
        2: 'Your location is unavailable. Check your device location settings and retry.',
        3: 'The location request timed out. Check your device location settings and retry.'
      }
      setError(locationErrors[err.code] || 'Could not determine your location. Check your device location settings and retry.')
      setLoading(false)
      return
    }

    const { latitude, longitude } = position.coords
    setUserPos({ lat: latitude, lng: longitude })
    setLocationPermission('granted')
    await loadNearbyPlaces(latitude, longitude)
  }

  useEffect(() => {
    loadUserLocation()
  }, [])

  useEffect(() => {
    if (!userPos || !mapContainerRef.current) return undefined
    if (!mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current, {
        center: [userPos.lat, userPos.lng],
        zoom: 13,
        zoomControl: true
      })
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
      }).addTo(mapRef.current)
    } else {
      mapRef.current.setView([userPos.lat, userPos.lng])
    }

    clearMarkers()
    const currentLocationMarker = L.marker([userPos.lat, userPos.lng], { icon: userIcon, title: 'Your location' })
      .addTo(mapRef.current)
      .bindPopup('Your current location')
    markersRef.current.push(currentLocationMarker)
    markersRef.current.push(...clinics.map(place => (
      L.marker([place.lat, place.lng], { icon: markerIcon('#1e3a8a'), title: place.name })
        .addTo(mapRef.current)
        .bindPopup(popupContent(place, 'clinic', userPos))
    )))
    markersRef.current.push(...stores.map(place => (
      L.marker([place.lat, place.lng], { icon: markerIcon('#059669'), title: place.name })
        .addTo(mapRef.current)
        .bindPopup(popupContent(place, 'store', userPos))
    )))

    return undefined
  }, [userPos, clinics, stores])

  useEffect(() => () => {
    clearMarkers()
    mapRef.current?.remove()
    mapRef.current = null
  }, [])

  const nearestClinic = clinics[0]
  const nearestStore = stores[0]

  return (
    <div className="nearby-care-page flex flex-col bg-skin-bg app-screen">
      <div className="px-4 sm:px-5 py-3.5 border-b border-skin-border flex items-center gap-3 bg-skin-bg sticky top-0 z-10">
        <button onClick={() => navigate('/chat')} className="w-10 h-10 rounded-xl bg-skin-card border border-skin-border flex items-center justify-center hover:bg-skin-a1/30 transition-colors">
          <ArrowLeft size={16} className="text-skin-muted" />
        </button>
        <div>
          <p className="font-semibold text-base sm:text-lg text-skin-text">Nearest Clinics & Shops</p>
          <p className="text-xs sm:text-sm text-skin-muted">OpenStreetMap clinics and skincare shops under 5 km away</p>
        </div>
      </div>

      <div ref={mapContainerRef} className="nearby-care-map flex-1 min-h-[320px] rounded-t-3xl -mt-3 sm:-mt-4 mx-2 sm:mx-3 bg-gray-100" />

      {loading && (
        <div className="flex flex-col items-center justify-center py-10 px-4 sm:px-5 bg-skin-bg border-t border-skin-border">
          <div className="w-12 h-12 rounded-full border-4 border-skin-a2 border-t-transparent animate-spin mb-4" />
          <p className="text-skin-text text-center font-medium">
            {userPos ? 'Searching OpenStreetMap...' : 'Getting your location...'}
          </p>
          <p className="text-xs text-skin-muted mt-2">Finding the nearest shops and clinics under 5 km</p>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 sm:p-5 text-center bg-skin-bg border-t border-skin-border">
          <p className="text-skin-text mb-3">{error}</p>
          <button onClick={() => userPos ? loadNearbyPlaces(userPos.lat, userPos.lng) : loadUserLocation()} className="text-xs px-4 py-2 rounded-full bg-skin-card border border-skin-border text-skin-a2 hover:bg-skin-a1/30 transition-colors">
            {userPos ? 'Retry Search' : 'Retry Location'}
          </button>
        </div>
      )}

      {!loading && !error && !nearestClinic && !nearestStore && (
        <div className="p-4 text-center bg-skin-bg border-t border-skin-border text-skin-muted">
          No mapped shops or clinics found under {SEARCH_RADIUS_KM} km.
        </div>
      )}

      {!loading && (nearestClinic || nearestStore) && (
        <div className="px-4 sm:px-5 py-4 space-y-5 bg-skin-bg border-t border-skin-border pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <p className="text-xs text-skin-muted font-medium uppercase tracking-wide">📍 Nearest options within {SEARCH_RADIUS_KM} km</p>
          {clinics.length > 0 && (
            <section className="space-y-3" aria-label="Nearby clinics">
              <h2 className="font-semibold text-sm text-indigo-700">Clinics & hospitals ({clinics.length})</h2>
              {clinics.map((clinic, index) => (
                <a key={`clinic-${clinic.osm_url || `${clinic.lat}-${clinic.lng}`}`} href={osmPlaceUrl(clinic)} target="_blank" rel="noreferrer" className="flex items-center gap-3 p-3.5 rounded-2xl bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 shadow-sm hover:shadow-md transition-shadow no-underline">
                  <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center flex-shrink-0"><MapPin size={18} className="text-indigo-600" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-skin-text truncate">{index + 1}. {clinic.name}</p>
                    <p className="text-xs text-indigo-700 mt-0.5">Clinic or hospital</p>
                    <p className="text-xs font-medium text-skin-muted mt-1">📍 {clinic.distance_km} km • {clinic.address || 'Address unavailable'}</p>
                  </div>
                </a>
              ))}
            </section>
          )}
          {stores.length > 0 && (
            <section className="space-y-3" aria-label="Nearby skincare shops">
              <h2 className="font-semibold text-sm text-emerald-700">Skincare shops & pharmacies ({stores.length})</h2>
              {stores.map((store, index) => (
                <a key={`store-${store.osm_url || `${store.lat}-${store.lng}`}`} href={osmPlaceUrl(store)} target="_blank" rel="noreferrer" className="flex items-center gap-3 p-3.5 rounded-2xl bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-200 shadow-sm hover:shadow-md transition-shadow no-underline">
                  <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0"><Store size={18} className="text-emerald-600" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-skin-text truncate">{index + 1}. {store.name}</p>
                    <p className="text-xs text-emerald-700 mt-0.5">Skincare shop or pharmacy</p>
                    <p className="text-xs font-medium text-skin-muted mt-1">📍 {store.distance_km} km • {store.address || 'Address unavailable'}</p>
                  </div>
                </a>
              ))}
            </section>
          )}
          {locationPermission === 'denied' && <p className="text-xs text-center text-skin-muted pt-2 border-t border-skin-border">Enable location in your browser for the most accurate results.</p>}
        </div>
      )}
    </div>
  )
}
