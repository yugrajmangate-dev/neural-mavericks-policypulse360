"""Fill the official CoCo CLI Hackathon submission template (python-pptx).

    python scripts/fill_template.py "<path to Prototype Submission Template _ CoCo CLI Hackathon GCC Edition.pptx>"

Writes submission/PolicyPulse360_NeuralMavericks_Template.pptx. Keeps the template's background banners,
Manrope font and #202729 ink; adds only text boxes / one picture on the existing blank-layout slides.
Each text box is checked with a conservative line-fit estimate and its font shrunk (never below 14 pt) if needed.
"""
import copy
import math
import shutil
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submission"
OUT = SUB / "PolicyPulse360_NeuralMavericks_Template.pptx"
FONT, FONT_SB = "Manrope", "Manrope SemiBold"
INK = RGBColor(0x20, 0x27, 0x29)
ACCENT = RGBColor(0x1C, 0x5C, 0xAB)
REPO = "https://github.com/yugrajmangate-dev/neural-mavericks-policypulse360"
MIN_PT = 14
CONTENT_TOP, CONTENT_BOTTOM = 0.62, 5.42          # white band between header and footer banners (inches)
LEFT, WIDTH = 0.36, 9.28
REPORT = []


# ----------------------------------------------------------------------------- fit estimation
def est_height_in(paras, width_in, pt, char_w=0.55, line_h=1.22, space_after_pt=5):
    """Conservative height estimate: chars/line from avg glyph width = char_w × font size."""
    cpl = max(1, int(width_in * 72 / (pt * char_w)))
    total = 0.0
    for text, scale, _bold in paras:
        size = pt * scale
        c = max(1, int(width_in * 72 / (size * char_w)))
        lines = max(1, math.ceil(len(text) / c))
        total += lines * size * line_h + space_after_pt
    _ = cpl
    return total / 72


def fit_pt(paras, width_in, height_in, start_pt):
    pt = start_pt
    while pt > MIN_PT and est_height_in(paras, width_in, pt) > height_in:
        pt -= 0.5
    ok = est_height_in(paras, width_in, pt) <= height_in
    return pt, ok


# ----------------------------------------------------------------------------- text helpers
def _bullet(p, on: bool, indent_emu=228600):
    pPr = p._p.get_or_add_pPr()
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum", "a:buFont"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    if on:
        pPr.set("marL", str(indent_emu))
        pPr.set("indent", str(-indent_emu))
        buf = etree.SubElement(pPr, qn("a:buFont"))
        buf.set("typeface", "Arial")
        bu = etree.SubElement(pPr, qn("a:buChar"))
        bu.set("char", "•")
    else:
        pPr.set("marL", "0")
        pPr.set("indent", "0")
        etree.SubElement(pPr, qn("a:buNone"))


def _run(p, text, pt, bold=False, color=INK, font=FONT):
    r = p.add_run()
    r.text = text
    f = r.font
    f.size, f.bold, f.name = Pt(pt), bold, font
    f.color.rgb = color
    return r


def write_box(tf, items, base_pt, width_in, height_in, name):
    """items: list of dicts {lead, text, bullet, scale, bold, color, align}"""
    paras = [((it.get("lead", "") + it.get("text", "")), it.get("scale", 1.0), it.get("bold", False)) for it in items]
    pt, ok = fit_pt(paras, width_in - 0.25, height_in - 0.1, base_pt)
    REPORT.append((name, pt, round(est_height_in(paras, width_in - 0.25, pt), 2), height_in, ok))
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _bullet(p, it.get("bullet", False))
        p.space_after = Pt(it.get("space_after", 5))
        if it.get("align"):
            p.alignment = it["align"]
        size = max(MIN_PT, round(pt * it.get("scale", 1.0) * 2) / 2)
        if it.get("lead"):
            _run(p, it["lead"], size, bold=True, color=it.get("lead_color", INK))
        if it.get("text"):
            _run(p, it["text"], size, bold=it.get("bold", False), color=it.get("color", INK))
    return pt


def add_box(slide, left, top, width, height, items, base_pt, name):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tb.name = name
    write_box(tb.text_frame, items, base_pt, width, height, name)
    return tb


def title(text):
    return {"text": text, "bold": True, "scale": 1.3, "space_after": 8}


def B(lead, text=""):
    return {"lead": lead, "text": text, "bullet": True}


# ----------------------------------------------------------------------------- slides
def main(template: str):
    SUB.mkdir(exist_ok=True)
    shutil.copyfile(template, OUT)
    prs = Presentation(OUT)
    s1, s2, s3, s4, s5, _s6 = prs.slides

    # 1 · cover: append values to the 4 existing label lines (same box, same font)
    values = {"Team Name :": "Neural Mavericks", "Team Leader Name :": "Yugraj Prabhakar Mangate",
              "Team Size :": "01", "Problem Statement :": "Customer 360 and Next Best Action — PolicyPulse 360"}
    for sh in s1.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip() in values:
            label = sh.text_frame.text.strip()
            p = sh.text_frame.paragraphs[0]
            for r in p.runs:
                r.font.size = Pt(MIN_PT)
            _run(p, " " + values[label], MIN_PT, bold=False, font=FONT_SB)
            n = len(label) + 1 + len(values[label])
            est_w = n * MIN_PT * 0.55 / 72
            REPORT.append((f"s1 {label}", MIN_PT, round(est_w, 2), round(Emu(sh.width).inches, 2), est_w <= Emu(sh.width).inches - 0.2))

    # 2 · Problem brief: reuse the template's guideline text box (same position, font, colour)
    box = next(sh for sh in s2.shapes if sh.has_text_frame)
    box.left, box.top = Inches(LEFT), Inches(CONTENT_TOP)
    box.width, box.height = Inches(WIDTH), Inches(CONTENT_BOTTOM - CONTENT_TOP)
    write_box(box.text_frame, [
        title("1. Problem Brief"),
        B("Business problem: ", "Indian insurers run policy admin, claims, billing and the call centre as separate systems, so "
          "churn is discovered at lapse and offers are generic."),
        B("Persona: ", "retention agent / relationship manager at a multi-line Indian insurer (Motor · Health · Life · Home)."),
        B("Pain point today: ", "~20 min per customer across 4+ screens and call recordings. The strongest churn signals "
          "(\"I'll port my policy\", \"claim pending 45 days\") are buried in unstructured transcripts."),
        B("How PolicyPulse 360 improves it: ", "one 360 card that unifies all touchpoints, an explainable churn score, and a next "
          "best action with cited call evidence plus a ready-to-send message."),
        B("Industry context: ", "high lapse at renewal, aggregator price-shopping, health portability and IRDAI grievance "
          "norms make proactive, explainable retention critical."),
    ], 16, WIDTH, CONTENT_BOTTOM - CONTENT_TOP, "s2 problem brief")

    # 3 · Architecture: title + large centred image + 1 caption line
    add_box(s3, LEFT, CONTENT_TOP, WIDTH, 0.5, [title("2. Architecture Diagram")], 16, "s3 title")
    img = SUB / "architecture.png"
    img_top, cap_h = CONTENT_TOP + 0.5, 0.78
    max_h = CONTENT_BOTTOM - img_top - cap_h
    ratio = 1890 / 1069
    h = max_h
    w = min(WIDTH, h * ratio)
    h = w / ratio
    s3.shapes.add_picture(str(img), Inches((10 - w) / 2), Inches(img_top), Inches(w), Inches(h))
    add_box(s3, LEFT, img_top + h + 0.04, WIDTH, CONTENT_BOTTOM - (img_top + h + 0.04), [
        {"lead": "CoCo CLI skills: ", "text": "$c360-unify → $interaction-intel → $next-best-action",
         "align": PP_ALIGN.CENTER, "space_after": 0},
        {"lead": "Structured: ", "text": "customers, policies, claims, payments   ·   ", "align": PP_ALIGN.CENTER,
         "space_after": 0},
    ], 14, "s3 caption")
    # second paragraph needs the unstructured part appended (keep it on the same line)
    cap = s3.shapes[-1].text_frame.paragraphs[-1]
    _run(cap, "Unstructured: ", MIN_PT, bold=True)
    _run(cap, "call transcripts", MIN_PT)

    # 4 · Impact
    add_box(s4, LEFT, CONTENT_TOP, WIDTH, CONTENT_BOTTOM - CONTENT_TOP, [
        title("3. Impact Statement"),
        B("Measured on synthetic data: ", "78 of 300 customers (26%) flagged High risk, catching 87% of truly at-risk "
          "customers (65/75) at 83% precision."),
        B("Measured on synthetic data: ", "₹37.0 L of ₹1.45 Cr annual premium (25%) sits in the High-risk band; "
          "43 High-risk renewals are due within 30 days."),
        B("Projected: ", "agent prep time ~20 min → under 30 s per customer (4 systems + recordings → one 360 card)."),
        B("Projected: ", "saving 20% of High-risk premium = ₹7.4 L per 300 customers, about ₹247 Cr per 1M customers."),
        B("Scalability: ", "incremental Cortex enrichment and an LLM capped to high-value customers, so cost tracks new "
          "calls, not book size. Runs on an XS warehouse with auto-suspend."),
        B("Beyond the demo: ", "portable skills on real RAW tables; next up are AI_TRANSCRIBE for call audio, dynamic "
          "tables for real-time scoring, and CRM / WhatsApp push."),
    ], 16, "s4 impact")

    # 5 · Additional slide: walkthrough; reuse the template's 'Additional Slide' box (bottom) for links
    links_top = 4.62
    add_box(s5, LEFT, CONTENT_TOP, WIDTH, links_top - CONTENT_TOP, [
        title("Additional Slide: Solution Walkthrough"),
        B("Customer 360 + NBA: ", "explainable risk gauge and drivers, next best action with cited call IDs, a "
          "copyable message, and a call timeline with AI summaries."),
        B("Portfolio: ", "₹ premium at risk by product × risk band, intent × sentiment, the 90-day renewal "
          "pipeline, and a ranked call list."),
        B("Ask PolicyPulse: ", "plain-English questions answered with Cortex AI_COMPLETE text-to-SQL "
          "(read-only). How it works: architecture + skills."),
        B("Cortex used: ", "CORTEX.SENTIMENT · AI_CLASSIFY · AI_COMPLETE · Cortex Search · "
          "CLASSIFY_TEXT / SUMMARIZE fallback."),
    ], 15, "s5 walkthrough")
    lbox = next(sh for sh in s5.shapes if sh.has_text_frame and sh.text_frame.text.strip() == "Additional Slide")
    lbox.left, lbox.top, lbox.width = Inches(LEFT), Inches(links_top), Inches(WIDTH)
    lbox.height = Inches(CONTENT_BOTTOM - links_top)
    write_box(lbox.text_frame, [
        {"lead": "GitHub: ", "text": REPO, "color": ACCENT, "space_after": 2},
        {"lead": "Live app: ", "text": "<URL>      ", "space_after": 0},
    ], 14, WIDTH, CONTENT_BOTTOM - links_top, "s5 links")
    lp = lbox.text_frame.paragraphs[-1]
    _run(lp, "Demo video: ", MIN_PT, bold=True)
    _run(lp, "<URL>", MIN_PT)
    lbox.text_frame.paragraphs[0].runs[-1].hyperlink.address = REPO

    prs.save(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB)")
    print(f"{'box':38s} {'font':>5s} {'est in':>7s} {'box in':>7s} fits")
    for name, pt, est, avail, ok in REPORT:
        print(f"{name:38s} {pt:5.1f} {est:7.2f} {avail:7.2f} {'OK' if ok else 'OVERFLOW'}")


if __name__ == "__main__":
    main(sys.argv[1])
