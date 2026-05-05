export function formatStationLabel(stationName?: string | null): string {
  const normalized = stationName?.trim();
  if (!normalized) {
    return '';
  }

  return normalized.endsWith('역') ? normalized : `${normalized}역`;
}
