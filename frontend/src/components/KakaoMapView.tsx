import React, { useEffect, useRef, useCallback } from 'react';
import { formatStationLabel } from '../utils/station';

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    kakao: any;
  }
}

interface HouseLocation {
  id: string;
  index?: number;
  district?: string;
  lat?: number;
  lng?: number;
  address: string;
  unit_no?: string;
  area?: number;
  house_type?: string;
  elevator?: string;
  deposit?: number;
  monthly_rent?: number;
  nearest_station?: string;
  distance_meters?: number;
  walking_time_mins?: number;
}

interface MapProps {
  houses: HouseLocation[];
  selectedHouseId?: string | null;
}

const KakaoMapView: React.FC<MapProps> = ({ houses, selectedHouseId }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapInstance = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersRef = useRef<Record<string, any>>({});
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const infoWindowsRef = useRef<Record<string, any>>({});

  const applySelection = useCallback((id: string | null | undefined) => {
    if (!id || !mapInstance.current || !markersRef.current[id]) {
      return;
    }

    const map = mapInstance.current;
    const marker = markersRef.current[id];
    const infowindow = infoWindowsRef.current[id];
    
    const position = marker.getPosition();
    map.setCenter(position);
    map.setLevel(3); // Zoom in
    
    // Close all other info windows
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Object.values(infoWindowsRef.current).forEach((iw: any) => iw.close());
    infowindow.open(map, marker);
    console.log("✨ Centered on marker:", id);
  }, []);

  // Initialize Map
  useEffect(() => {
    const initMap = () => {
      console.log("📍 initMap called with houses:", houses.length);
      if (!mapContainer.current || !window.kakao || !window.kakao.maps) {
        console.log("🚫 Map init blocked:", {container: !!mapContainer.current, kakao: !!window.kakao});
        return;
      }

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

        // Format values for the info window
        const depositStr = house.deposit ? `${house.deposit.toLocaleString()}만원` : '-';
        const rentStr = house.monthly_rent !== undefined ? `${house.monthly_rent.toLocaleString()}만원` : '-';
        const stationLabel = formatStationLabel(house.nearest_station);
        const transportInfo = house.nearest_station 
          ? `<p style="margin:8px 0 0; font-size:11px; color:#10b981; font-weight:bold;">🚉 ${stationLabel} (도보 ${house.walking_time_mins || '?'}분 ${house.distance_meters ? `· ${house.distance_meters}m` : ''})</p>`
          : '';

        const iwContent = `
          <div style="padding:20px; min-width:240px; border-radius:24px; border:none; background:white; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:flex-start;">
              <div>
                <span style="display:inline-block; padding:2px 8px; background:#f1f5f9; color:#64748b; font-size:10px; font-weight:800; border-radius:6px; margin-bottom:4px; text-transform:uppercase;">${house.district || '주택'} · ${house.house_type || '-'}</span>
                <h4 style="margin:0; font-size:18px; font-weight:900; color:#1e293b; letter-spacing:-0.025em; line-height:1.2;">${house.address.split(' ').slice(0, 3).join(' ')}</h4>
              </div>
              ${house.elevator === '있음' ? '<span style="font-size:18px;">🛗</span>' : ''}
            </div>
            
            <div style="background:#f8fafc; padding:12px; border-radius:16px; margin-bottom:12px;">
              <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                <span style="font-size:11px; color:#64748b; font-weight:600;">면적 / 호수</span>
                <span style="font-size:11px; color:#1e293b; font-weight:800;">${house.area ? house.area + '㎡' : '-'} / ${house.unit_no || '-'}</span>
              </div>
              <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="font-size:11px; color:#64748b; font-weight:600;">보증금</span>
                <span style="font-size:14px; color:#4f46e5; font-weight:900;">${depositStr}</span>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span style="font-size:11px; color:#64748b; font-weight:600;">월세</span>
                <span style="font-size:14px; color:#1e293b; font-weight:900;">${rentStr}</span>
              </div>
            </div>

            <p style="margin:0; font-size:11px; color:#94a3b8; line-height:1.5; display: flex; align-items: start; gap: 4px;"><span>📍</span> <span>${house.address}</span></p>
            ${transportInfo}
          </div>
        `;
        const infowindow = new window.kakao.maps.InfoWindow({
          content: iwContent,
          removable: true
        });

        window.kakao.maps.event.addListener(marker, 'click', () => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          Object.values(infoWindowsRef.current).forEach((iw: any) => iw.close());
          infowindow.open(map, marker);
        });

        markersRef.current[house.id] = marker;
        infoWindowsRef.current[house.id] = infowindow;

        bounds.extend(position);
        hasMarkers = true;
      });

      console.log(`✅ ${Object.keys(markersRef.current).length} markers created.`);

      if (hasMarkers) {
        map.setBounds(bounds);
      }

      if (selectedHouseId) {
        setTimeout(() => applySelection(selectedHouseId), 100);
      }
    };

    if (window.kakao && window.kakao.maps) {
      window.kakao.maps.load(initMap);
    }
  }, [houses, selectedHouseId, applySelection]);

  // Handle selection change
  useEffect(() => {
    applySelection(selectedHouseId);
  }, [selectedHouseId, applySelection]);

  return (
    <div 
      ref={mapContainer} 
      className="h-full w-full z-0"
      style={{ isolation: 'isolate', minHeight: '400px' }}
    />
  );
};

export default KakaoMapView;
