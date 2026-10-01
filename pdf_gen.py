from io import BytesIO
from xml.sax.saxutils import escape as x
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

def build_pdf(r):
    """Single-column, real-text PDF with standard headings: what ATS parsers read best."""
    buf = BytesIO()
    h = r.get("header", {})
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm,
                            bottomMargin=16*mm, title=f"{h.get('name','')} Resume", author=h.get("name", ""))
    base = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=13.5)
    name = ParagraphStyle("n", parent=base, fontName="Helvetica-Bold", fontSize=20, leading=24)
    head = ParagraphStyle("h", parent=base, fontName="Helvetica-Bold", fontSize=11.5, spaceBefore=12, spaceAfter=3)
    import re
    F = [Paragraph(x(h.get("name", "")), name)]
    if h.get("headline"): F.append(Paragraph(x(h["headline"]), base))
    F.append(Spacer(1, 3))
    contact = " | ".join(v for v in (h.get("email"), h.get("phone"), h.get("location")) if v)
    if contact: F.append(Paragraph(x(contact), base))
    def link(l):
        u = (l.get("url") or "").strip()
        if not u: return x(l.get("label", ""))
        shown = re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
        return f'<a href="{x(u, {chr(34): "&quot;"})}" color="#0b57d0">{x(shown)}</a>'
    ls = [link(l) for l in h.get("links", []) if not (l.get("url") or "").startswith(("mailto:", "tel:"))]
    if ls: F.append(Paragraph(" | ".join(ls), base))

    def section(t): F.append(Paragraph(t, head))
    def bullets(items):
        F.append(ListFlowable([ListItem(Paragraph(x(b.get("text", "")), base)) for b in items],
                              bulletType="bullet", start="•", leftIndent=12, bulletFontSize=9))

    if r.get("summary"): section("Summary"); F.append(Paragraph(x(r["summary"]), base))
    if r.get("skills"): section("Skills"); F.append(Paragraph(x(", ".join(r["skills"])), base))
    if r.get("experience"):
        section("Experience")
        for e in r["experience"]:
            line = f"<b>{x(e.get('title',''))}</b>, {x(e.get('org',''))}" + (f" | {x(e['dates'])}" if e.get("dates") else "")
            F += [Paragraph(line, base), Spacer(1, 2)]; bullets(e.get("bullets", []))
    if r.get("projects"):
        section("Projects")
        for p in r["projects"]:
            F.append(Paragraph(f"<b>{x(p.get('title',''))}</b>", base))
            if p.get("tech"): F.append(Paragraph(f"<i>{x(p['tech'])}</i>", base))
            F.append(Spacer(1, 2)); bullets(p.get("bullets", []))
    if r.get("education"):
        section("Education")
        for e in r["education"]: F.append(Paragraph(x(e), base))
    for sec in r.get("sections", []):
        if sec.get("items"): section(x(sec.get("title", ""))); bullets([{"text": i} for i in sec["items"]])
    doc.build(F)
    return buf.getvalue()
