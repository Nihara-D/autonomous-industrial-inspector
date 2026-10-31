import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

export interface LogLine {
  t: string;
  level: string;
  msg: string;
}

export interface RobotStatus {
  state: string;
  current: string | null;
  step: string;
  done: string[];
  failed: string[];
  skipped: string[];
  next_slot: number;
  slots_total: number;
  log: LogLine[];
}

export interface Detection {
  color: string;
  x: number;
  y: number;
  area: number;
}

export interface Snapshot {
  bridge: boolean;
  robotOnline: boolean;
  status: RobotStatus | null;
  detections: { objects: Detection[] } | null;
  cameraAgeSeconds: number | null;
}

export interface Run {
  id: number;
  startedAt: string;
  finishedAt: string;
  sorted: string[];
  failed: string[];
  skipped: string[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  status() {
    return this.http.get<Snapshot>('/api/status');
  }

  runs() {
    return this.http.get<Run[]>('/api/runs');
  }

  start(colors: string[]) {
    return this.http.post('/api/start', { colors });
  }

  stop() {
    return this.http.post('/api/stop', {});
  }

  resetSlots() {
    return this.http.post('/api/reset-slots', {});
  }
}
