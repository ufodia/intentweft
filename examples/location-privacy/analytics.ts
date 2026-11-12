type Position = { latitude: number; longitude: number };

export async function trackMapOpen(position: Position, regionCode: string) {
  return fetch("https://analytics.example.invalid/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event: "map_open",
      region: regionCode,
      latitude: position.latitude,
      longitude: position.longitude,
    }),
  });
}
