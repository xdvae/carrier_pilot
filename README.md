CareerPilot

Tailor your resume to a specific job without making anything up.

Upload your old resume and paste a job description. CareerPilot scores the match, asks about the skills you may have but didn't write down, then rewrites your resume for that job and checks every line against what you actually said. You get a clean, ATS-friendly PDF, course suggestions for your gaps, and a mock interview.

## How it works

1. **Upload**: resume (PDF, DOCX or pasted text), job title, company and job description.
2. **Match score**: each requirement is marked matched, partial or gap, with the resume line that proves it. Skills the role usually expects but the posting doesn't mention are listed too.
3. **Questions**: one question per unproven requirement (Yes, directly / Something similar / No, plus an optional detail). Your answers are the only new facts the resume may use.
4. **Tailored resume**: summary, skills, experience and every project are rewritten for the job. Projects are ordered by relevance and nothing is dropped. Contact links (LinkedIn, GitHub, etc.) are kept.
5. **Truth check**: a second AI pass flags any line your resume or answers don't support.
6. **Edit and compare**: edit any line, reorder projects, or view original vs tailored with changes highlighted.
7. **PDF**: one-column, real selectable text, standard headings.
8. **Courses**: free (freeCodeCamp, YouTube) and paid (Coursera, Udemy) search links for each gap.
9. **Practice**: 10 mock interview questions (role, behavioural, and honest questions about your gaps) with a score and feedback on each answer.

The match score can only stay the same or go up after you answer questions. It never drops.

## The no-invention rule

CareerPilot never adds a degree, job, project, tool or achievement that isn't in your resume or your answers. "Something similar" appears as related exposure only, and "No" stays a gap.

Keyword coverage is calculated by code, not guessed by the AI. It is not an official ATS score, since every company's system differs.

## Tech

- Backend: Python, Flask
- AI: OpenAI (default `gpt-4o-mini`), with automatic fallback to Google Gemini (default `gemini-2.5-flash`)
- Parsing: `pypdf`, `python-docx`
- PDF: `reportlab`
- Frontend: plain HTML, CSS and JavaScript (no build step)

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env      # Windows PowerShell: cp .env.example .env
```

Open `.env` and add at least one key:

```
OPENAI_API_KEY=
GEMINI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
GEMINI_MODEL=gemini-2.5-flash
```

Then:

```bash
python app.py
```

Open http://localhost:5000.

- OpenAI runs first. If it fails or has no key, Gemini takes over. A free Google AI Studio key works on its own: leave `OPENAI_API_KEY` empty.
- If you get a "model not found" error, set `GEMINI_MODEL` to a model your key can use.
- Add your logo as `static/logo.png`. It shows next to the name and as the browser tab icon.

## Test without API keys

```bash
python test_flow.py
```

Runs the whole flow with a fake AI: analyze, generate, score, PDF.

## Project structure

```
app.py          Flask routes, prompts, scoring, AI calls
pdf_gen.py      PDF builder
static/         index.html, style.css, app.js, logo.png
test_flow.py    offline smoke test
.env.example    environment template
```

## Known limits

- Scanned, image-only PDFs can't be read (no OCR). Paste the text instead.
- Course links are search links, so they always work but aren't hand-picked.
- Non-English characters may not render correctly in the PDF.
- Progress is saved in your browser only.

## Privacy

Resume text is sent to OpenAI and/or Google to generate results. Don't use real personal data with a free-tier Gemini key, since Google may use it to improve its products. Never commit your `.env` file.

## License

Add one before publishing, for example MIT.
