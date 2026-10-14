# MarineGuard AI frontend

React + Vite website with Leaflet/OpenStreetMap, focused on Singapore coastal monitoring.

## Run locally

Requires Node.js 20.19+ or 22.12+ and npm. From this folder:

```sh
npm ci
npm run dev
```

Open the local URL printed by Vite. `npm run build` generates `dist/`; `npm run preview` previews the build.

## Current features

- Singapore wide map with a Coastal area dropdown. Choose “Draw polygon…”, optionally enter a name, click three or more map corners, and choose “Finish polygon”; use Undo last point to correct a corner. The current polygon is held in browser memory for filtering and prediction and is replaced when another is drawn; it is not saved as a reusable area. Time views remain available. (Current state, Expected in 2 hours, Expected in 4 hours, Expected in 24 hours).
- Selectable map markers, observation cards, reset view, and downloadable JSON demo report. “Trace path” on a Marine debris card shows an illustrative 2/4/24-hour drift line for that item; it is a UI demo and does not use live current or wind data.
- Animated “How it works” system diagram showing the planned satellite / MARIDA data, Earth Engine preparation, litter detection, movement estimates, and coastal map workflow. It is explicitly marked as planned; the live backend is not connected.
- Responsive landing page and project mission section, styled in navy and blue to match the project presentation.

Future time views keep current demo observations visible as context and clearly state that paths are illustrative rather than live forecasts. All current observations, confidence scores, and severity labels are fictional frontend demo data. No backend, Earth Engine, or trained model is connected. Map tiles and fonts require internet access. OpenStreetMap attribution must remain visible.

## Source

- `src/main.jsx`: page and map components, selection state, report export.
- `src/data.js`: clearly labelled synthetic observations and coastal areas.
- `src/styles.css`: responsive styling.

Jalyoddhe inspired the general map-and-observation workflow. This implementation uses original application code and demo data.
