import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, MapPin, Store } from 'lucide-react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import { locationsAPI } from '../utils/api'

const SEARCH_RADIUS_KM = 5

function RecenterMap({ position }) {
  const map = useMap()
  useEffect(() => {
    if (position) map.setView(position, 12)
  }, [map, position])
  return null
}

function PlacePopup({ place, type }) {
  const mapUrl = place.maps_url || `https://www.openstreetmap.org/?mlat=${place.lat}&mlon=${place.lng}#map=18/${place.lat}/${place.lng}`
  return (
    <div className="min-w-[220px] text-sm">
      <p className="font-semibold !text-gray-900">{place.name}</p>
      <p className="my-1 text-xs !text-gray-700">{place.desc || type}</p>
      <p className="text-xs !text-gray-700">{Number(place.distance_km).toFixed(2)} km away (straight-line)</p>
      <p className="text-xs !text-gray-700">{place.address}</p>
      <div className="mt-2 flex gap-1">
        <a
          href={`https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${place.lat}%2C${place.lng}`}
          target="_blank"
          rel="noreferrer"
          className="flex-1 rounded bg-blue-600 px-2 py-1 text-center text-xs !text-white no-underline hover:bg-blue-700"
        >
          Directions
        </a>
        <a href={mapUrl} target="_blank" rel="noreferrer" className="flex-1 rounded bg-emerald-600 px-2 py-1 text-center text-xs !text-white no-underline hover:bg-emerald-700">
          View
        </a>
      </div>
    </div>
  )
}

function PlaceList({ places, type, icon: Icon, colorClass, badgeClass }) {
  return (
    <div className="space-y-2">
      <p className={`text-xs font-semibold uppercase tracking-wide ${colorClass}`}>
        {type === 'clinic' ? '🏥 Clinics and healthcare' : '🛒 Shops and pharmacies'} ({places.length})
      </p>
      {places.map((place, index) => (
        <a
          key={`${type}-${place.place_id}`}
          href={place.maps_url || `https://www.openstreetmap.org/?mlat=${place.lat}&mlon=${place.lng}`}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 rounded-2xl border border-skin-border bg-skin-card p-3 shadow-sm transition-shadow hover:shadow-md"
        >
          <div className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl ${badgeClass}`}>
            <Icon size={17} className={colorClass} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-skin-text">{index + 1}. {place.name}</p>
            <p className="mt-0.5 truncate text-xs text-skin-muted">{place.address}</p>
          </div>
          <span className={`flex-shrink-0 text-xs font-semibold ${colorClass}`}>
            {Number(place.distance_km).toFixed(2)} km
          </span>
        </a>
      ))}
    </div>
  )
}

export default function MapPage() {
  const navigate = useNavigate()
  const requestRef = useRef(0)
  const [userPos, setUserPos] = useState(null)
  const [clinics, setClinics] = useState([])
  const [stores, setStores] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [locationPermission, setLocationPermission] = useState('')

  const fetchNearbyPlaces = async (lat, lng) => {
    const requestId = ++requestRef.current
    try {
      const response = await locationsAPI.nearby(lat, lng, SEARCH_RADIUS_KM)
      if (requestId !== requestRef.current) return
      const nextClinics = response.data.clinics || []
      const nextStores = response.data.stores || []
      setClinics(nextClinics)
      setStores(nextStores)
    } catch (err) {
      if (requestId !== requestRef.current) return
      console.error('Failed to fetch nearby places:', err)
      setClinics([])
      setStores([])
      setError('Nearby places could not be loaded. Check your connection and try again.')
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }

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
      const nextPosition = { lat: position.coords.latitude, lng: position.coords.longitude }
      setUserPos(nextPosition)
      setLocationPermission('granted')
      await fetchNearbyPlaces(nextPosition.lat, nextPosition.lng)
    } catch (err) {
      console.warn('Geolocation error:', err.code, err.message)
      setUserPos(null)
      setClinics([])
      setStores([])
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

  return (
    <div className="nearby-care-page flex flex-col bg-skin-bg app-screen">
      <div className="sticky top-0 z-10 flex items-center gap-3 border-b border-skin-border bg-skin-bg px-4 py-3.5 sm:px-5">
        <button onClick={() => navigate('/chat')} className="flex h-10 w-10 items-center justify-center rounded-xl border border-skin-border bg-skin-card">
          <ArrowLeft size={16} className="text-skin-muted" />
        </button>
        <div>
          <p className="text-base font-semibold text-skin-text sm:text-lg">Nearest Clinics & Stores</p>
          <p className="text-xs text-skin-muted sm:text-sm">OpenStreetMap locations • Tap markers for details</p>
        </div>
      </div>

      <div className="relative mx-2 -mt-3 min-h-[320px] flex-1 overflow-hidden rounded-t-3xl bg-gray-100 sm:mx-3 sm:-mt-4">
        {userPos && (
          <MapContainer center={userPos} zoom={12} className="h-full min-h-[320px] w-full" scrollWheelZoom>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <RecenterMap position={userPos} />
            <CircleMarker center={userPos} radius={9} pathOptions={{ color: '#fff', weight: 3, fillColor: '#3b82f6', fillOpacity: 1 }}>
              <Popup>Your location</Popup>
            </CircleMarker>
            {clinics.map(place => (
              <CircleMarker key={`clinic-${place.place_id}`} center={[place.lat, place.lng]} radius={8} pathOptions={{ color: '#fff', weight: 2, fillColor: '#1e3a8a', fillOpacity: 1 }}>
                <Popup><PlacePopup place={place} type="Dermatology clinic" /></Popup>
              </CircleMarker>
            ))}
            {stores.map(place => (
              <CircleMarker key={`store-${place.place_id}`} center={[place.lat, place.lng]} radius={7} pathOptions={{ color: '#fff', weight: 2, fillColor: '#059669', fillOpacity: 1 }}>
                <Popup><PlacePopup place={place} type="Skincare products available" /></Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        )}
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center border-t border-skin-border bg-skin-bg px-4 py-10">
          <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-skin-a2 border-t-transparent" />
          <p className="font-medium text-skin-text">Getting your location...</p>
          <p className="mt-2 text-xs text-skin-muted">Finding nearby clinics and stores</p>
        </div>
      )}

      {error && !loading && (
        <div className="border-t border-skin-border bg-skin-bg p-4 text-center sm:p-5">
          <p className="mb-3 text-skin-text">{error}</p>
          <button onClick={loadUserLocation} className="rounded-full border border-skin-border bg-skin-card px-4 py-2 text-xs text-skin-a2">Retry Location</button>
        </div>
      )}

      {!loading && !error && !clinics.length && !stores.length && (
        <div className="border-t border-skin-border bg-skin-bg p-4 text-center text-skin-muted">
          No skincare shops or dermatology clinics found within {SEARCH_RADIUS_KM} km.
        </div>
      )}

      {!loading && (clinics.length || stores.length) && (
        <div className="space-y-3 border-t border-skin-border bg-skin-bg px-4 py-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:px-5">
          <p className="text-xs font-medium uppercase tracking-wide text-skin-muted">📍 All nearby options, sorted nearest first</p>
          <PlaceList places={clinics} type="clinic" icon={MapPin} colorClass="text-indigo-700" badgeClass="bg-indigo-100" />
          <PlaceList places={stores} type="store" icon={Store} colorClass="text-emerald-700" badgeClass="bg-emerald-100" />
          {locationPermission === 'denied' && <p className="border-t border-skin-border pt-2 text-center text-xs text-skin-muted">💡 Enable location in your browser for the most accurate results</p>}
        </div>
      )}
    </div>
  )
}
