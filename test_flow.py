# Offline smoke test: fakes the AI so the whole flow can be checked without API keys.
import app as A, json
RES=[{"skill":"SQL","importance":"essential","status":"matched","evidence":"Wrote SQL queries"},
     {"skill":"Excel","importance":"essential","status":"gap","evidence":""},
     {"skill":"Power BI","importance":"preferred","status":"gap","evidence":""}]
def fake(user, system=None):
    if "strict fact checker" in (system or ""): return {"flags":[]}
    if "header" in user:
        return {"header":{"name":"Asha Verma","headline":"BCA Student | Python | SQL","email":"asha@x.com","phone":"+91 99999 99999","location":"Punjab, India","links":[{"label":"LinkedIn","url":"https://www.linkedin.com/in/asha"},{"label":"GitHub","url":"https://github.com/asha"}]},"summary":"Analyst with SQL and Excel.","skills":["SQL","Excel"],
         "experience":[{"title":"Intern","org":"Acme","dates":"2025","bullets":[{"text":"Wrote SQL queries","original":"x"}]}],
         "projects":[],"education":["BCA"],"sections":[{"title":"Languages","items":["English, Hindi"]}],"requirements":[dict(RES[0]),dict(RES[1],status="matched"),RES[2]],"unclear":[],
         "gaps":[{"skill":"Power BI","importance":"preferred","why":"dashboards","study":["DAX"]}],"interview_questions":[{"question":"q","tip":"t"}]}
    return {"requirements":RES,"keywords":["SQL","Excel"],"hidden_skills":[{"skill":"Pivot tables","why":"w"}],"questions":[{"skill":"Excel","question":"Excel?"}]}
def fake2(user, system=None):
    if "interview coach" in (system or ""): return {"score":6,"strengths":["a"],"improve":["b"],"sample":"s","follow_up":"f"}
    return fake(user, system)
A.llm=fake2; c=A.app.test_client()
a=c.post("/api/analyze",data={"resume_text":"x"*60,"jd":"job","title":"DA","company":"C"}).get_json(); print("score",a["score"])
g=c.post("/api/generate",json={"resume_text":"x","jd":"j","title":"t","company":"c","answers":[],"keywords":a["keywords"],"hidden_skills":a["hidden_skills"]}).get_json()
print("after",g["score"],"ats",g["ats"],"missing",g["missing_keywords"])
p=c.post("/api/pdf",json=g); print(p.status_code,p.data[:4],len(p.data))
open("/tmp/t.pdf","wb").write(p.data)

pr=c.post("/api/practice",json={"resume_text":"x","jd":"j","title":"t","company":"c","question":"q","answer":"my answer here"}).get_json(); print("practice",pr["score"])

# monotonic score: model says every requirement is a gap (user answered No to all) -> score must not drop
def downgrade(user, system=None):
    out = fake2(user, system)
    if "header" in user:
        out = dict(out, requirements=[dict(r, status="gap") for r in RES])
    return out
A.llm = downgrade
g2=c.post("/api/generate",json={"resume_text":"x","jd":"j","title":"t","company":"c","answers":[],"requirements":a["requirements"],"keywords":[],"hidden_skills":[]}).get_json()
print("before",a["score"],"after all-No",g2["score"]); assert g2["score"]>=a["score"]
# bad file type and unreadable text give clear errors
import io as _io
print(c.post("/api/analyze",data={"resume":(_io.BytesIO(b"x"),"cv.png"),"jd":"j"}).get_json())
print(c.post("/api/analyze",data={"resume_text":"short","jd":"j"}).get_json())
