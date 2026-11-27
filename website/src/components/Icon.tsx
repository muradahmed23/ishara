const PATHS: Record<string, string> = {
  head: '<circle cx="12" cy="9" r="5"/><path d="M5 21c1.2-3.6 3.8-5.5 7-5.5s5.8 1.9 7 5.5"/><path d="M8 5.5 16 12.5" stroke-dasharray="2 2"/>',
  mic: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5v3"/>',
  type: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7 10h.01M11 10h.01M15 10h.01M7 14h10"/>',
  target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
  lock: '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
  wifiOff: '<path d="M3 3l18 18M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 4-2.4M19 13a10 10 0 0 0-3-2M12 20h.01"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.9-3.2 3.4-5 6.5-5s5.6 1.8 6.5 5M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 15c1.6.7 2.6 2.4 3 5"/>',
  bt: '<path d="M7 7.5 17 16.5 12 20.5V3.5l5 4L7 16.5"/>',
  cursor: '<path d="M5.5 3.5 18.5 11l-5.6 1.4-2.9 5.6z"/>',
};

export function Icon({ name }: { name: keyof typeof PATHS | string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden dangerouslySetInnerHTML={{ __html: PATHS[name] ?? "" }} />
  );
}
