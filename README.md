# Review Slate

A tiny Flask tool that turns a movie review into two ready-to-post Instagram
squares (1080×1080):

1. **Cover slide** — the supplied clapperboard photograph, with your movie
   poster in the slate and movie name in the upper-left.
2. **Review slide** — a movie image as a dimmed backdrop, with your
   review text and a 5-star rating (0.5 increments) on top.

The cover uses the supplied artwork and the review is drawn with Pillow on
the server — no Canva, no external image APIs, nothing to pay for.

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
   - `BRAND_HANDLE` — shown in the tool header, e.g. `@yourhandle`
   - `BRAND_WATERMARK` — the faint diagonal watermark on the review slide,
     e.g. `YOUR PAGE NAME`
5. Deploy. Render gives you a `https://your-app.onrender.com` URL — that's
   your tool.

### Keeping it online 24/7

A free Render web service sleeps after inactivity, so it is not a true 24/7
option; the first visitor after a sleep must wait for it to start. For an
always-on public app, select an always-on paid Render web-service plan (or an
equivalent paid host). There is no dependable, permanently always-on free tier
for a dynamic Flask site.

This app needs no database or persistent disk, so the smallest always-on plan
is sufficient. Set the build command to `pip install -r requirements.txt` and
the start command to `gunicorn app:app`, then redeploy after each GitHub push.

## Customizing the look

Cover artwork is stored in `static/images/cover-template.png` and tracked with
Git LFS, so clone the repository with Git LFS enabled before running the app.
All dynamic drawing logic lives in `utils/image_gen.py`:
- `GOLD` — the star accent color
- `generate_cover_image()` — the supplied cover template with the poster and movie title
- `generate_review_image()` — the review slide (blur amount, overlay
  darkness, watermark text, star size, etc.)

Fonts are bundled in `/fonts` (Anton, Poppins, Playfair Display — all open
license, from Google Fonts) so nothing needs to be installed on the server.

## Notes

- Images are processed in memory and returned as base64 PNGs — nothing is
  written to disk, so there's no cleanup or storage cost on Render.
- On mobile, selected photos are resized in the browser to a 2048px maximum
  dimension before upload. This keeps ordinary camera photos fast and below
  request limits without changing the generated composition.
- Uploads are capped at 50MB total (see `MAX_CONTENT_LENGTH` in `app.py`) for
  browsers that cannot resize the image. A friendly error is shown if that
  limit is exceeded.
- Rating is clamped and snapped to the nearest 0.5 server-side too, so a
  tampered request can't send something like 3.27.
