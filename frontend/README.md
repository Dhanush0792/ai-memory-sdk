# AI Memory SDK - Frontend

Static landing page for the AI Memory SDK with "Neural Memory Space" design.

## Overview

Pure static frontend featuring:
- Hero section with floating memory nodes
- Visual explanation of how memory works
- Interactive memory demo
- Feature showcase
- Dark gradient theme with depth effects

**Deployed on**: Netlify  
**No build step required** - Pure static HTML/CSS/JS

## Running Locally

### Option 1: Simple HTTP Server (Python)
```bash
cd frontend
python -m http.server 8080
```

Visit `http://localhost:8080`

### Option 2: Live Server (VS Code)
1. Install "Live Server" extension
2. Right-click `index.html` → "Open with Live Server"

### Option 3: Any Static Server
Serve the `frontend/` directory with any static file server.

## Deployment (Netlify)

### Netlify Configuration
- **Base directory**: `frontend`
- **Build command**: _(leave empty)_
- **Publish directory**: `frontend`

### Deploy Steps
1. Connect repository to Netlify
2. Set base directory to `frontend`
3. Deploy (no build needed)

## File Structure

```
frontend/
├── index.html           # Main landing page
├── static/
│   ├── css/
│   │   └── style.css   # Dark theme with animations
│   └── js/
│       └── app.js      # Subtle interactions & parallax
└── README.md
```

## Design Features

### Visual Theme
- **Dark gradient background**: `#0B0F19` → `#111827`
- **Floating memory nodes**: 22 SVG nodes in 3 depth layers
- **Depth illusion**: Blur + opacity + scale (no 3D engine)
- **Calm motion**: 15s+ animation loops
- **Subtle parallax**: Mouse-tracking (max 20px movement)

### Color System
- **Base**: Dark slate backgrounds
- **Accents**: Indigo (`#6366F1`) and Cyan (`#22D3EE`)
- **Text**: White primary, gray secondary
- **Glows**: Soft indigo/cyan with low opacity

### Sections
1. **Hero**: Gradient title, floating nodes background
2. **How Memory Works**: 3-step visual process flow
3. **Memory Demo**: Input → extracted memory visualization
4. **Features**: 6 feature cards with icons
5. **Footer**: Minimal with links

## Backend Connection

This is a **static landing page** - it does not connect to the backend API.

For the interactive demo application with API integration, see the backend documentation at `/backend/README.md`.

## Notes

- **No Python or Node required** - Pure static HTML/CSS/JS
- **No API calls** - Landing page only, no backend integration
- **Responsive design** - Works on mobile, tablet, desktop
- **Performance optimized** - CSS-only animations, respects `prefers-reduced-motion`
- **SEO ready** - Semantic HTML, meta tags, proper heading structure
