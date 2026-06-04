# Custom Streamlit Cookie Component

Minimal Streamlit custom component for browser cookie operations, built from the reactless (Vite + TypeScript) template.

## Why this component

- No `react-scripts` dependency
- No UI rendering required
- Small Python API for `get`, `set`, `delete`, and `get_all`

## Usage

```python
from ui.custom.cookie import CookieManager

cookies = CookieManager()
cookies.set("session_id", "abc123", key="cookie_set_session")
value = cookies.get("session_id")
all_cookies = cookies.get_all()
cookies.delete("session_id", key="cookie_delete_session")
```

## Frontend development

```bash
cd ui/custom/cookie/frontend
npm install
npm run start
```

Set `COOKIE_COMPONENT_DEV_URL` (for example `http://localhost:3001`) so the Python wrapper points to the Vite dev server while developing.

## Build frontend bundle

```bash
cd ui/custom/cookie/frontend
npm install
npm run build
```

The production component loads assets from `ui/custom/cookie/frontend/build`.
