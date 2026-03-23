export interface House {
  id: string;
  index?: number;
  district?: string;
  complex_no?: string;
  address: string;
  unit_no?: string;
  area?: number;
  house_type?: string;
  elevator?: string;
  deposit: number;
  monthly_rent: number;
  raw_text_reference: string;
  extra_info?: Record<string, unknown>;
  lat?: number;
  lng?: number;
  nearest_station?: string;
  distance_meters?: number;
  walking_time_mins?: number;
}

export interface Announcement {
  id: string;
  filename: string;
  title: string;
  description: string;
  house_count: number;
}
