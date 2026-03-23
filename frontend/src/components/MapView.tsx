import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';

// Fix for default marker icon in Leaflet + Reaction
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

interface HouseLocation {
  id: string;
  name: string;
  lat?: number;
  lng?: number;
  address: string;
  house_type: string;
}

interface MapProps {
  houses: HouseLocation[];
}

// Helper component to auto-fit bounds
const ChangeView = ({ houses }: { houses: HouseLocation[] }) => {
  const map = useMap();
  
  useEffect(() => {
    const validHouses = houses.filter(h => h.lat && h.lng);
    if (validHouses.length > 0) {
      const bounds = L.latLngBounds(validHouses.map(h => [h.lat!, h.lng!]));
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [houses, map]);
  
  return null;
}

const MapView: React.FC<MapProps> = ({ houses }) => {
  const validHouses = houses.filter(h => h.lat && h.lng);
  
  // Default to Seoul center if no houses
  const center: [number, number] = [37.5665, 126.9780];

  return (
    <div className="h-[400px] w-full rounded-2xl overflow-hidden border border-slate-200 shadow-inner mt-4 z-0">
      <MapContainer 
        center={center} 
        zoom={13} 
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {validHouses.map((house) => (
          <Marker key={house.id} position={[house.lat!, house.lng!]}>
            <Popup>
              <div className="p-1">
                <h4 className="font-bold text-sm">{house.name}</h4>
                <p className="text-xs text-slate-500">{house.house_type}</p>
                <p className="text-[10px] text-slate-400 mt-1">{house.address}</p>
              </div>
            </Popup>
          </Marker>
        ))}
        <ChangeView houses={houses} />
      </MapContainer>
    </div>
  );
};

export default MapView;
