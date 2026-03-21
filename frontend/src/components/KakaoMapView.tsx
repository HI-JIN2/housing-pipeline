import React, { useEffect, useRef } from 'react';

declare global {
  interface Window {
    kakao: any;
  }
}

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
  selectedHouseId?: string | null;
}

const KakaoMapView: React.FC<MapProps> = ({ houses, selectedHouseId }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);
  const markersRef = useRef<{ [key: string]: any }>({});
  const infoWindowsRef = useRef<{ [key: string]: any }>({});

  // Initialize Map
  useEffect(() => {
    const initMap = () => {
      if (!mapContainer.current || !window.kakao || !window.kakao.maps) return;

      const validHouses = houses.filter(h => h.lat && h.lng);
      const center = validHouses.length > 0 
        ? new window.kakao.maps.LatLng(validHouses[0].lat, validHouses[0].lng)
        : new window.kakao.maps.LatLng(37.5665, 126.9780);

      const options = {
        center: center,
        level: 4
      };

      const map = new window.kakao.maps.Map(mapContainer.current, options);
      mapInstance.current = map;

      const bounds = new window.kakao.maps.LatLngBounds();
      let hasMarkers = false;

      // Clear existing refs
      markersRef.current = {};
      infoWindowsRef.current = {};

      validHouses.forEach(house => {
        const position = new window.kakao.maps.LatLng(house.lat, house.lng);
        const marker = new window.kakao.maps.Marker({
          position: position,
          map: map
        });

        const iwContent = `
          <div style="padding:10px; min-width:150px; border-radius:8px; border:none; background:white; font-family:sans-serif;">
            <h4 style="margin:0; font-size:14px; font-weight:bold; color:#333;">${house.name}</h4>
            <p style="margin:4px 0 0; font-size:12px; color:#666;">${house.house_type}</p>
          </div>
        `;
        const infowindow = new window.kakao.maps.InfoWindow({
          content: iwContent,
          removable: true
        });

        window.kakao.maps.event.addListener(marker, 'click', () => {
          // Close all other info windows first
          Object.values(infoWindowsRef.current).forEach((iw: any) => iw.close());
          infowindow.open(map, marker);
        });

        markersRef.current[house.id] = marker;
        infoWindowsRef.current[house.id] = infowindow;

        bounds.extend(position);
        hasMarkers = true;
      });

      if (hasMarkers) {
        map.setBounds(bounds);
      }
    };

    if (window.kakao && window.kakao.maps) {
      window.kakao.maps.load(initMap);
    }
  }, [houses]);

  // Handle selection change
  useEffect(() => {
    if (selectedHouseId && mapInstance.current && markersRef.current[selectedHouseId]) {
      const map = mapInstance.current;
      const marker = markersRef.current[selectedHouseId];
      const infowindow = infoWindowsRef.current[selectedHouseId];
      
      const position = marker.getPosition();
      map.setCenter(position);
      map.setLevel(3); // Zoom in
      
      // Close all other info windows
      Object.values(infoWindowsRef.current).forEach((iw: any) => iw.close());
      infowindow.open(map, marker);
    }
  }, [selectedHouseId]);

  return (
    <div 
      ref={mapContainer} 
      className="h-full w-full z-0"
      style={{ isolation: 'isolate', minHeight: '400px' }}
    />
  );
};

export default KakaoMapView;
