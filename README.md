# Review Slate

Create two Instagram carousel PNGs at **1080 × 1350 pixels (4:5)**, matching
`page1.png` and `page2.png`:

- Cover: clapperboard photograph, uploaded movie artwork and fitted movie title.
- Review: faded movie backdrop, supplied Scene & Opinion logo watermark,
  black serif review text and orange outlined stars, including half ratings.

Upload two movie images, enter a title and review, choose a rating and download
both PNGs. Paragraph breaks are preserved and text shrinks to fit. Reviews that
cannot fit legibly are rejected with a request to shorten them. Movie images
are center-cropped to fill their frames, so keep the subject near the center.
Images are processed in memory and are not stored on the server.

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:3000. Run checks with `python -m unittest discover -s tests`.

## Render deployment

Push this project, including fonts and static images, to your GitHub repository.
The active portrait template and review background are regular Git assets, so
Git LFS is not needed for deployment. The older square template is retained.

In Render, create a **Blueprint** from that repository; `render.yaml` configures
a free Python web service, build command, Gunicorn server and health check.
Alternatively create a Web Service manually with:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120`
- Health check: `/health`

`BRAND_HANDLE` optionally changes the handle displayed in the website header.
The cover photograph and review logo contain their own baked-in branding;
replace those assets to change the branding in exported posts.

### Free hosting and startup delays

Render's free **web services sleep after 15 minutes without incoming traffic**.
The next visitor triggers startup, which can take about a minute. You do not
redeploy each time, but free Flask hosting does not provide guaranteed instant,
always-on access. Choose a paid instance if avoiding idle startup is essential.

Render static sites do not need a running Python server. A future version that
renders images entirely in the browser could use static hosting without this
server startup delay; this version uses Flask/Pillow and needs a web service.
See https://render.com/docs/free and https://render.com/docs/static-sites.

## Assets and limits

- `static/images/cover-portrait.png`: portrait artwork prepared from the supplied reference.
- `static/images/review-background.png`: supplied page 2 logo background.
- `fonts/`: bundled rendering fonts; no external image services are used.
- Uploads: 20 MB total; titles: 80 characters; reviews: 1200 characters.
- Both downloaded PNGs are always 1080 × 1350, regardless of input dimensions.
