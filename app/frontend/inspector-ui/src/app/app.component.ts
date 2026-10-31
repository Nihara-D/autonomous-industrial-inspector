import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { ApiService, Detection, LogLine, Run, RobotStatus, Snapshot } from './api.service';

interface ColourRow {
  name: string;
  selected: boolean;
}

const STATE_LABELS: Record<string, string> = {
  starting: 'Starting up',
  ready: 'Ready',
  running: 'Running',
  error: 'Error'
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './app.component.html'
})
export class AppComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);

  snap: Snapshot | null = null;
  serverDown = false;
  runs: Run[] = [];

  rows: ColourRow[] = [
    { name: 'red', selected: true },
    { name: 'green', selected: true },
    { name: 'blue', selected: true }
  ];

  message = '';
  messageIsError = false;
  busy = false;

  cameraSrc = '/api/camera.jpg';
  cameraOk = false;

  private poll?: ReturnType<typeof setInterval>;
  private cameraTimer?: ReturnType<typeof setTimeout>;
  private lastState = '';

  ngOnInit() {
    this.refresh();
    this.loadRuns();
    this.poll = setInterval(() => this.refresh(), 1000);
    this.nextFrame();
  }

  ngOnDestroy() {
    clearInterval(this.poll);
    clearTimeout(this.cameraTimer);
  }

  // ---- derived values -------------------------------------------------

  get status(): RobotStatus | null {
    return this.snap?.status ?? null;
  }

  get online(): boolean {
    return !this.serverDown && !!this.snap?.robotOnline;
  }

  get connectionText(): string {
    if (this.serverDown) return 'Server unreachable';
    if (!this.snap?.bridge) return 'Robot link down';
    if (!this.snap.robotOnline) return 'Robot not responding';
    return 'Connected';
  }

  get stateLabel(): string {
    const s = this.status?.state;
    return s ? (STATE_LABELS[s] ?? s) : 'Offline';
  }

  get selectedColours(): string[] {
    return this.rows.filter(r => r.selected).map(r => r.name);
  }

  get canStart(): boolean {
    return this.status?.state === 'ready' && this.selectedColours.length > 0 && !this.busy;
  }

  get canStop(): boolean {
    return this.status?.state === 'running' && !this.busy;
  }

  get canReset(): boolean {
    return this.status?.state === 'ready' && (this.status?.next_slot ?? 0) > 0 && !this.busy;
  }

  get objects(): Detection[] {
    return this.online ? (this.snap?.detections?.objects ?? []) : [];
  }

  get logLines(): LogLine[] {
    return [...(this.status?.log ?? [])].reverse();
  }

  slotFor(colour: string): string {
    const index = this.selectedColours.indexOf(colour);
    if (index < 0 || !this.status) return '';
    const slot = this.status.next_slot + index + 1;
    return slot > this.status.slots_total ? 'no free slot' : 'slot ' + slot;
  }

  duration(run: Run): string {
    const seconds = Math.round((Date.parse(run.finishedAt) - Date.parse(run.startedAt)) / 1000);
    return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
  }

  // ---- actions ----------------------------------------------------------

  move(index: number, direction: number) {
    const target = index + direction;
    if (target < 0 || target >= this.rows.length) return;
    [this.rows[index], this.rows[target]] = [this.rows[target], this.rows[index]];
  }

  toggle(row: ColourRow) {
    row.selected = !row.selected;
  }

  start() {
    this.send(this.api.start(this.selectedColours), 'Start command sent.');
  }

  stop() {
    this.send(this.api.stop(), 'Stop requested. The robot finishes the current object first.');
  }

  resetSlots() {
    this.send(this.api.resetSlots(), 'Pedestal slots reset.');
  }

  private send(request: ReturnType<ApiService['stop']>, okText: string) {
    this.busy = true;
    this.message = '';
    request.subscribe({
      next: () => {
        this.messageIsError = false;
        this.message = okText;
        // keep the buttons locked until the robot's status has caught up
        setTimeout(() => (this.busy = false), 1500);
      },
      error: (e: HttpErrorResponse) => {
        this.busy = false;
        this.messageIsError = true;
        this.message = e.error?.message ?? 'The request failed (' + e.status + ').';
      }
    });
  }

  // ---- polling ------------------------------------------------------------

  private refresh() {
    this.api.status().subscribe({
      next: s => {
        this.snap = s;
        this.serverDown = false;
        const state = s.status?.state ?? '';
        if (this.lastState === 'running' && state === 'ready') this.loadRuns();
        this.lastState = state;
      },
      error: () => (this.serverDown = true)
    });
  }

  private loadRuns() {
    this.api.runs().subscribe({ next: r => (this.runs = r), error: () => {} });
  }

  // ---- camera: ask for the next picture once the previous one has arrived --

  nextFrame() {
    this.cameraSrc = '/api/camera.jpg?t=' + Date.now();
  }

  onFrameLoad() {
    this.cameraOk = true;
    this.cameraTimer = setTimeout(() => this.nextFrame(), 250);
  }

  onFrameError() {
    this.cameraOk = false;
    this.cameraTimer = setTimeout(() => this.nextFrame(), 1500);
  }
}
