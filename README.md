# Review Slate

A tiny Flask tool that turns a movie review into two ready-to-post Instagram
squares (1080×1080):

1. **Cover slide** — your movie image set inside an illustrated clapperboard.
2. **Review slide** — a second movie image as a dimmed backdrop, with your
   review text and a 5-star rating (0.5 increments) on top.

Everything is drawn with Pillow on the server — no Canva, no external image
APIs, nothing to pay for.

## Run it locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Visit `http://localhost:5000`.

## Deploy to Render

1. Push this folder to a GitHub repo.
2. On [render.com](https://render.com) → **New +** → **Web Service** → connect
   the repo.
3. Settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (already set via the `Procfile`,
     Render picks it up automatically)
4. (Optional) Add environment variables so the posts carry your own brand
   text instead of the placeholders:
   - `BRAND_HANDLE` — shown top-right of the cover slide, e.g. `@yourhandle`
   - `BRAND_WATERMARK` — the faint diagonal watermark on the review slide,
     e.g. `YOUR PAGE NAME`
5. Deploy. Render gives you a `https://your-app.onrender.com` URL — that's
   your tool.

Note: Render's free tier spins the service down after inactivity, so the
first request after a while takes ~30–50s to wake up. That's normal.

## Customizing the look

All drawing logic lives in `utils/image_gen.py`:
- `STRIPE_COLORS`, `GOLD`, `INK`, `PAPER` — the color palette
- `generate_cover_image()` — the clapperboard slide
- `generate_review_image()` — the review slide (blur amount, overlay
  darkness, watermark text, star size, etc.)

Fonts are bundled in `/fonts` (Anton, Poppins, Playfair Display — all open
license, from Google Fonts) so nothing needs to be installed on the server.

## Notes

- Images are processed in memory and returned as base64 PNGs — nothing is
  written to disk, so there's no cleanup or storage cost on Render.
- Max upload size is capped at 20MB total (see `MAX_CONTENT_LENGTH` in
  `app.py`) — raise it if your phone photos are larger.
- Rating is clamped and snapped to the nearest 0.5 server-side too, so a
  tampered request can't send something like 3.27.
