import os, json, requests
from urllib.parse import quote_plus
from flask import Flask, request, jsonify, send_file
from io import BytesIO
from pdf_gen import build_pdf
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException
import re
import docx
from pypdf import PdfReader

load_dotenv()
app = Flask(__name__, static_folder="static", static_url_path="")

RULES = ("You are a careful career assistant. Use ONLY facts in the candidate's resume and confirmed answers. "
         "Never invent degrees, jobs, projects, technologies, certifications or achievements. "
         "A requirement without evidence is a gap. Reply with valid JSON only.")

def _openai(system, user):
    r = requests.post("https://api.openai.com/v1/chat/completions", timeout=120,
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
        json={"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "temperature": 0.3,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])

def _gemini(system, user):
    m = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
        params={"key": os.environ["GEMINI_API_KEY"]}, timeout=120,
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"parts": [{"text": user}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3}})
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])

def llm(user, system=RULES):
    last, tried = None, False
    for key, fn in (("OPENAI_API_KEY", _openai), ("GEMINI_API_KEY", _gemini)):
        if not os.getenv(key): continue
        tried = True
        for _ in range(2):
            try: return fn(system, user)
            except ValueError as e: last = e          # bad JSON: ask again once
            except Exception as e: last = e; break    # quota/network: try the other provider
    if not tried: raise RuntimeError("No AI key found. Add OPENAI_API_KEY or GEMINI_API_KEY to your .env file.")
    raise RuntimeError(f"The AI request failed ({last}).")

def read_resume(f):
    name, data = f.filename.lower(), f.read()
    if not name.endswith((".pdf", ".docx", ".txt", ".md")):
        raise ValueError("Use a PDF, DOCX or text file.")
    try: return _read(name, data)
    except Exception: raise ValueError("We couldn't open that file. Try another copy, or paste the text instead.")

def _read(name, data):
    import io
    links = []
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        for pg in reader.pages:                      # hyperlinks live in annotations, not in the text
            for an in pg.get("/Annots") or []:
                try:
                    u = an.get_object().get("/A", {}).get("/URI")
                    if u and str(u) not in links: links.append(str(u))
                except Exception: pass
    elif name.endswith(".docx"):
        d = docx.Document(io.BytesIO(data))
        text = "\n".join(p.text for p in d.paragraphs)
        links = [r.target_ref for r in d.part.rels.values() if r.reltype.endswith("/hyperlink")]
    else:
        text = data.decode("utf-8", "ignore")
    text = text[:14000]
    if links: text += "\n\nLINKS FOUND IN THE RESUME FILE:\n" + "\n".join(links)
    return text

def job_block(d):
    return f"JOB TITLE: {d.get('title')}\nCOMPANY: {d.get('company')}\nDESCRIPTION:\n{(d.get('jd') or '')[:8000]}"

@app.get("/")
def index(): return app.send_static_file("index.html")

W = {"essential": 2, "preferred": 1}
V = {"matched": 1, "partial": .5, "gap": 0}

def score(reqs):
    tot = sum(W.get(r.get("importance"), 1) for r in reqs) or 1
    return round(100 * sum(W.get(r.get("importance"), 1) * V.get(r.get("status"), 0) for r in reqs) / tot)

def flat(r):
    p = [r["header"].get("name", ""), r["header"].get("headline", ""), r.get("summary", ""), " ".join(r.get("skills", []))]
    for sec in r.get("sections", []): p += sec.get("items", [])
    for sec in ("experience", "projects"):
        for it in r.get(sec, []):
            p += [it.get("title", ""), it.get("org", "")] + [b["text"] for b in it.get("bullets", [])]
    return " ".join(p + r.get("education", [])).lower()

def source_of(d):
    ans = "\n".join(f"- {a['skill']}: Q: {a['question']} A: {a['answer']}" for a in d.get("answers", []) if a.get("answer"))
    ex = "\n".join(f"- {k}: {v}" for k, v in (d.get("extra") or {}).items() if v)
    return (f"RESUME:\n{d['resume_text']}\n\nCANDIDATE ANSWERS (choice, then detail. 'No' means no experience):\n{ans or 'none'}"
            f"\n\nADDITIONAL INFO FROM CANDIDATE:\n{ex or 'none'}")

def clean_reqs(reqs):
    out = []
    for r in reqs or []:
        if isinstance(r, dict) and r.get("skill"):
            st = str(r.get("status")).lower()
            out.append({"skill": str(r["skill"]), "evidence": str(r.get("evidence") or ""),
                        "importance": "essential" if str(r.get("importance")).lower() == "essential" else "preferred",
                        "status": st if st in V else "gap"})
    return out

RANK = {"gap": 0, "partial": 1, "matched": 2}
def toks(s): return set(re.findall(r"[a-z0-9+#]+", s.lower()))

def merge_reqs(base, new):
    """Statuses can only improve, so the score never goes down."""
    out = []
    for b in base:
        tb, best, bs = toks(b["skill"]), None, 0
        for n in new:
            tn = toks(n["skill"]); sim = len(tb & tn) / max(min(len(tb), len(tn)), 1)
            if sim > bs: best, bs = n, sim
        if best and bs >= 0.6 and RANK[best["status"]] > RANK[b["status"]]:
            out.append(dict(b, status=best["status"], evidence=best["evidence"] or b["evidence"]))
        else: out.append(b)
    return out

def txt(x):
    return x if isinstance(x, str) else " ".join(str(v) for v in x.values()) if isinstance(x, dict) else str(x)

def tidy(res):
    """Make odd model output safe to render."""
    hd = res.get("header") if isinstance(res.get("header"), dict) else {}
    hd["links"] = [l for l in hd.get("links") or [] if isinstance(l, dict)]
    res["header"] = hd
    res["summary"] = txt(res.get("summary") or "")
    res["skills"] = [txt(x) for x in res.get("skills") or []]
    res["education"] = [txt(x) for x in res.get("education") or []]
    for k in ("experience", "projects"):
        items = [e for e in res.get(k) or [] if isinstance(e, dict)]
        for e in items:
            e["bullets"] = [b if isinstance(b, dict) else {"text": txt(b)} for b in e.get("bullets") or []]
            for b in e["bullets"]: b["text"] = txt(b.get("text", "")); b.setdefault("original", "")
        res[k] = items
    res["sections"] = [{"title": txt(x.get("title", "")), "items": [txt(i) for i in x.get("items") or []]}
                       for x in res.get("sections") or [] if isinstance(x, dict)]
    for k in ("requirements", "gaps", "unclear", "interview_questions"):
        res[k] = [x for x in res.get(k) or [] if isinstance(x, dict)]
    return res

@app.post("/api/analyze")
def analyze():
    f = request.form
    try:
        text = read_resume(request.files["resume"]) if request.files.get("resume") else f.get("resume_text", "")[:14000]
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if not f.get("jd", "").strip(): return jsonify(error="Paste the job description."), 400
    if len(text.strip()) < 50:
        return jsonify(error="We couldn't read text from your resume. If it's a scanned PDF, paste the text instead."), 400
    out = llm(f"""RESUME:\n{text}\n\n{job_block(f)}\n
Return JSON: {{"requirements":[{{"skill":str,"importance":"essential"|"preferred","status":"matched"|"partial"|"gap",
"evidence":"short quote from the resume, empty if none"}}],
"keywords":[str],
"hidden_skills":[{{"skill":str,"why":str}}],
"questions":[{{"skill":str,"importance":"essential"|"preferred","question":str}}]}}
requirements: every requirement in the job (8-14). keywords: 10-15 short ATS terms (1-3 words).
hidden_skills: 3-5 skills this kind of role normally expects that the posting never names (e.g. pivot tables for a data analyst).
questions: one per requirement marked partial or gap (essential first, max 10), then one per hidden skill (max 3).
Each question must point at something in the candidate's history that might involve it, as a question, never as fact.
Example: "In your data analytics training, did you keep records or prepare reports?". If nothing relates, ask directly.
`skill` is a short name (1-5 words).""")
    out["requirements"] = clean_reqs(out.get("requirements"))
    out["keywords"] = [str(k) for k in out.get("keywords") or []]
    out["hidden_skills"] = [h for h in out.get("hidden_skills") or [] if isinstance(h, dict) and h.get("skill")]
    out["questions"] = [dict(q, skill=str(q.get("skill", ""))) for q in out.get("questions") or [] if isinstance(q, dict) and q.get("question")]
    out["resume_text"] = text
    out["score"] = score(out["requirements"])
    return jsonify(out)

def links(skill):
    q = quote_plus(skill)
    return [{"name": "freeCodeCamp", "tag": "Free", "url": f"https://www.freecodecamp.org/news/search/?query={q}"},
            {"name": "YouTube", "tag": "Free", "url": f"https://www.youtube.com/results?search_query={q}+full+course"},
            {"name": "Coursera", "tag": "Paid, audit free", "url": f"https://www.coursera.org/search?query={q}"},
            {"name": "Udemy", "tag": "Paid", "url": f"https://www.udemy.com/courses/search/?q={q}"}]

def dropped(res):
    have = " ".join([p.get("title", "") for p in res.get("projects", [])] +
                    [e.get("title", "") + " " + e.get("org", "") for e in res.get("experience", [])]).lower()
    return [t for t in res.get("source_projects", []) + res.get("source_experience", []) if t and t.lower()[:12] not in have]

@app.post("/api/generate")
def generate():
    d = request.get_json()
    hidden = ", ".join(h["skill"] for h in d.get("hidden_skills", []))
    base = clean_reqs(d.get("requirements"))
    reqnames = json.dumps([r["skill"] for r in base])
    source = source_of(d)
    prompt = f"""{source}\n\n{job_block(d)}\nLIKELY-EXPECTED SKILLS NOT IN POSTING: {hidden}\nREQUIREMENTS TO RE-EVALUATE (copy each skill name exactly): {reqnames}\n
Return JSON: {{"source_projects":[str],"source_experience":[str],"header":{{"name":str,"headline":str,"email":str,"phone":str,"location":str,"links":[{{"label":str,"url":str}}]}},"summary":str,"summary_why":str,"skills":[str],
"experience":[{{"title":str,"org":str,"dates":str,"bullets":[{{"text":str,"original":"the resume line this came from, or 'From your answers'","why":"under 12 words: which job need this serves"}}]}}],
"projects":[{{"title":str,"tech":"technologies the source names for it","bullets":[{{"text":str,"original":str,"why":str}}]}}],
"education":[str],
"sections":[{{"title":str,"items":[str]}}],
"requirements":[{{"skill":str,"importance":"essential"|"preferred","status":"matched"|"partial"|"gap","evidence":str}}],
"unclear":[{{"section":str,"note":str}}],
"gaps":[{{"skill":"short name, 1-4 words","importance":"essential"|"preferred","why":str,"study":["2-4 specific topics"]}}],
"interview_questions":[{{"type":"Role"|"Behavioural"|"Gap","question":str,"tip":"what a strong answer covers"}}]}}

TAILORING RULES (the resume must clearly differ from the original and read as written for THIS job):
- Voice: no third person and no pronouns (no I, my, he, she, the candidate, no name in sentences). Summary and bullets
  start with strong verbs or role nouns, e.g. "Customer-focused BCA student with...", "Built...", "Maintained...".
- Summary: ONE or TWO short sentences, 30 words maximum, no filler adjectives, only facts that fit this job.
- Completeness: first list in source_projects and source_experience EVERY project and role found in the source. Then output
  one entry for each, none skipped, even if not very relevant. Projects go in order of relevance to the job, most relevant
  first. Experience stays newest first. For a less relevant project, keep it and rewrite its bullets around the parts that
  transfer to this job (problem solving, data handling, APIs, documentation, testing), truthfully.
- Bullets: rewrite every bullet so it leads with what matters to this job (accuracy, records, communication, tools, etc.),
  using the job's terms wherever the source supports them. Reframe real activity; do not copy the original wording.
  Never drop an entry. 2-3 bullets per project, 3-4 per experience entry. No invented numbers.
- Order: skills and bullets by relevance to the job. The skills list puts job-relevant skills first and keeps every skill from the source.
- Answers: "Yes, directly" + detail can become a bullet or skill. "Something similar" may appear only as related exposure,
  worded honestly. "No" or empty means the requirement is a gap. Use additional info for entries the resume lacks.
- Header: keep EVERY contact detail and link from the source exactly (email, phone, location, LinkedIn, GitHub, portfolio, etc).
  Take URLs from the "LINKS FOUND" list when present. Never drop or invent one. headline: up to 8 words separated by " | ",
  built from the candidate's real skills and degree and the job's field. Never claim a job title they have not held.
- Education: keep grades, CGPA and years exactly as given.
- sections: keep other real sections from the source (Certifications, Achievements, Languages, Additional) as {{title, items}}. Never invent items.
- Never add a degree, job, project, technology, certification or achievement the source does not contain.
requirements: re-evaluate every job requirement using resume + answers; evidence is a short resume quote or "You said: <paraphrase>", never just "Yes".
gaps: every requirement or likely-expected skill still unsupported. interview_questions: 10 (4 Role, 3 Behavioural, 3 Gap: honest questions about missing skills)."""
    res = tidy(llm(prompt))
    miss = dropped(res)
    if miss:   # one retry if the model skipped anything from the source
        res = llm(prompt + f"\nYour previous answer left these out: {miss}. Return the full JSON again including every one of them.")
        res = tidy(res)
    check = llm(f"""SOURCE:\n{source}\n\nGENERATED:\n{json.dumps({k: res.get(k) for k in ('summary','skills','experience','projects')})}\n
Find any generated claim (technology, metric, role, achievement) NOT supported by the source.
Return JSON: {{"flags":[{{"text":str,"reason":str}}]}}. Empty list if everything is supported.""",
        system="You are a strict fact checker. Reply with valid JSON only.")
    for k in ("skills", "experience", "projects", "education", "sections", "requirements", "gaps", "unclear", "interview_questions"):
        res.setdefault(k, [])
    res.setdefault("header", {})
    res["flags"] = check.get("flags", [])
    kws = list(dict.fromkeys(d.get("keywords", []) + [h["skill"] for h in d.get("hidden_skills", [])]))
    t = flat(res)
    res["missing_keywords"] = [k for k in kws if k.lower() not in t]
    res["ats"] = round(100 * (len(kws) - len(res["missing_keywords"])) / max(len(kws), 1))
    new = clean_reqs(res.get("requirements"))
    res["requirements"] = merge_reqs(base, new) if base else new
    res["score"] = score(res["requirements"])
    for g in res["gaps"]: g["resources"] = links(g["skill"])
    return jsonify(res)

@app.post("/api/practice")
def practice():
    d = request.get_json()
    return jsonify(llm(f"""{source_of(d)}\n\n{job_block(d)}\n
INTERVIEW QUESTION: {d['question']}\nWHAT A STRONG ANSWER COVERS: {d.get('tip','')}\nCANDIDATE'S ANSWER: {d['answer']}\n
Coach this candidate like a kind, honest interviewer. Return JSON:
{{"score":int 1-10,"strengths":[str],"improve":[str],
"sample":"a stronger answer in first person that uses ONLY experience in the source; if they lack the experience, an honest answer that says so and shows how they would learn it",
"follow_up":str}}
Max 3 strengths and 3 improvements, each one sentence.""", system="You are an interview coach. Reply with valid JSON only."))

@app.post("/api/pdf")
def pdf():
    r = request.get_json()
    return send_file(BytesIO(build_pdf(r)), mimetype="application/pdf", as_attachment=True,
                     download_name=re.sub(r"[^\w.-]+", "_", (r.get("header") or {}).get("name") or "Resume") + "_Resume.pdf")

@app.errorhandler(Exception)
def err(e):
    if isinstance(e, HTTPException): return e
    m = str(e)
    if "429" in m: m = "The AI service is busy or out of quota. Wait a minute and try again."
    elif "401" in m or "403" in m: m = "The AI key was rejected. Check the keys in your .env file."
    return jsonify(error=m), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
