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
}

const KakaoMapView: React.FC<MapProps> = ({ houses }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);

  useEffect(() => {
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

    validHouses.forEach(house => {
      const position = new window.kakao.maps.LatLng(house.lat, house.lng);
      const marker = new window.kakao.maps.Marker({
        position: position,
        map: map
      });

      const iwContent = `
        <div style="padding:10px; min-width:150px; border-radius:8px;">
          <h4 style="margin:0; font-size:14px; font-weight:bold;">${house.name}</h4>
          <p style="margin:4px 0 0; font-size:12px; color:#666;">${house.house_type}</p>
        </div>
      `;
      const infowindow = new window.kakao.maps.InfoWindow({
        content: iwContent,
        removable: true
      });

      window.kakao.maps.event.addListener(marker, 'click', () => {
        infowindow.open(map, marker);
      });

      bounds.extend(position);
      hasMarkers = true;
    });

    if (hasMarkers) {
      map.setBounds(bounds);
    }
  }, [houses]);

  return (
    <div 
      ref={mapContainer} 
      className="h-[400px] w-full rounded-2xl overflow-hidden border border-slate-200 shadow-inner mt-4 z-0"
      style={{ isolation: 'isolate' }}
    />
  );
};

export default KakaoMapView;
