import io, re, json, time
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

import streamlit as st
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

st.set_page_config(page_title="TTB Label Verification", page_icon="🍾", layout="wide")

WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, "
    "and may cause health problems."
)

FIELDS = ["brand_name", "class_type", "alcohol_content", "net_contents", "producer", "country_of_origin"]

def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9%./-]+", " ", (s or "").lower()).strip()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

def extract_fields(text: str) -> Dict[str, str]:
    t = text or ""
    lines = [x.strip() for x in t.splitlines() if x.strip()]
    out = {k: "" for k in FIELDS}

    patterns = {
        "brand_name": [r"(?:brand\s*(?:name)?|brand)\s*[:\-]\s*(.+)"],
        "class_type": [r"(?:class\s*/?\s*type|class/type)\s*[:\-]\s*(.+)"],
        "alcohol_content": [r"(?:alcohol\s*content|abv)\s*[:\-]\s*(.+)",
                            r"\b\d{1,2}(?:\.\d+)?\s*%\s*(?:alc\.?|alcohol)?\s*(?:/|by)?\s*(?:vol\.?|volume)?"],
        "net_contents": [r"(?:net\s*contents?|net)\s*[:\-]\s*(.+)",
                         r"\b\d+(?:\.\d+)?\s*(?:ml|mL|L|liters?|oz)\b"],
        "producer": [r"(?:producer|bottler|bottled\s*by)\s*[:\-]\s*(.+)"],
        "country_of_origin": [r"(?:country\s*of\s*origin|origin)\s*[:\-]\s*(.+)"],
    }
    for field, pats in patterns.items():
        for p in pats:
            m = re.search(p, t, re.I)
            if m:
                out[field] = (m.group(1) if m.lastindex else m.group(0)).strip()
                break
    return out

def warning_check(text: str) -> Tuple[bool, List[str]]:
    n = normalize(text)
    wn = normalize(WARNING)
    issues = []
    if "government warning" not in n:
        issues.append("Government Warning heading not detected.")
        return False, issues
    # Exact normalized comparison where the full warning is present.
    if wn not in n:
        issues.append("Warning statement does not exactly match the required prototype text.")
    # Prototype-level visual check: capitalization is only verifiable if OCR preserves case.
    m = re.search(r"Government Warning:", text or "")
    if m and m.group(0) != "GOVERNMENT WARNING:":
        issues.append("Warning heading is not in the required all-caps form.")
    if not issues:
        return True, []
    return False, issues

def compare(app: Dict[str, str], label: Dict[str, str]) -> List[Dict]:
    results = []
    for field in FIELDS:
        av, lv = app.get(field, ""), label.get(field, "")
        if not av and not lv:
            status, score, note = "Not checked", 0, "No value supplied."
        elif not av:
            status, score, note = "Review", 0, "Application value is missing."
        elif not lv:
            status, score, note = "Review", 0, "Label value was not detected."
        else:
            score = similarity(av, lv)
            status = "Match" if score >= 0.88 else ("Review" if score >= 0.70 else "Mismatch")
            note = f"Similarity {score:.0%}"
        results.append({"field": field, "application": av, "label": lv, "status": status, "note": note})
    return results

def ocr_image(img: Image.Image) -> str:
    """Local OCR. Tesseract is optional; the UI provides manual text fallback."""
    try:
        import pytesseract
        img = ImageOps.exif_transpose(img).convert("RGB")
        img = ImageEnhance.Contrast(img).enhance(1.35)
        img = img.filter(ImageFilter.SHARPEN)
        return pytesseract.image_to_string(img, config="--psm 6")
    except Exception:
        return ""

st.title("TTB Label Verification")
st.caption("Prototype for rapid label/application matching — human review remains the final decision.")

with st.sidebar:
    st.header("Prototype controls")
    st.write("Target: simple workflow, batch upload, clear exceptions, and fast local processing.")
    st.info("For production, connect the extraction layer to an approved OCR/AI service or an agency-hosted model. Do not send sensitive documents to an unapproved endpoint.")

tab1, tab2 = st.tabs(["Single Review", "Batch Review"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Application data")
        app_json = st.text_area(
            "Paste application JSON",
            value=json.dumps({
                "brand_name": "OLD TOM DISTILLERY",
                "class_type": "Kentucky Straight Bourbon Whiskey",
                "alcohol_content": "45% Alc./Vol. (90 Proof)",
                "net_contents": "750 mL",
                "producer": "",
                "country_of_origin": ""
            }, indent=2),
            height=240,
        )
        try:
            application = json.loads(app_json)
        except Exception:
            application = {}
            st.error("Application JSON is not valid.")

    with c2:
        st.subheader("Label image")
        uploaded = st.file_uploader("Upload label image", type=["png","jpg","jpeg","webp"])
        label_text = ""
        if uploaded:
            img = Image.open(uploaded)
            st.image(img, use_container_width=True)
            start = time.perf_counter()
            label_text = ocr_image(img)
            elapsed = time.perf_counter() - start
            st.caption(f"Local OCR time: {elapsed:.2f}s")
        label_text = st.text_area("OCR / extracted label text (editable fallback)", value=label_text, height=240)

    if st.button("Verify Label", type="primary", use_container_width=True):
        label = extract_fields(label_text)
        results = compare(application, label)
        warning_ok, warning_issues = warning_check(label_text)

        st.subheader("Verification results")
        good = sum(r["status"] == "Match" for r in results)
        bad = sum(r["status"] == "Mismatch" for r in results)
        review = sum(r["status"] == "Review" for r in results)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Matches", good)
        m2.metric("Mismatches", bad)
        m3.metric("Needs review", review)
        m4.metric("Warning", "PASS" if warning_ok else "REVIEW")

        for r in results:
            icon = {"Match":"✅", "Mismatch":"❌", "Review":"⚠️", "Not checked":"—"}[r["status"]]
            with st.expander(f"{icon} {r['field'].replace('_',' ').title()} — {r['status']}"):
                st.write(f"**Application:** {r['application'] or '—'}")
                st.write(f"**Label:** {r['label'] or '—'}")
                st.caption(r["note"])

        if warning_issues:
            st.warning("Government Warning: " + " ".join(warning_issues))

with tab2:
    st.subheader("Batch verification")
    batch = st.file_uploader("Upload multiple label images", type=["png","jpg","jpeg","webp"], accept_multiple_files=True)
    st.write("Each image is OCR'd locally and summarized below. Pairing with application records can be added through CSV/JSON in a production integration.")
    if batch and st.button("Run Batch Verification", type="primary"):
        rows = []
        start_all = time.perf_counter()
        for f in batch:
            img = Image.open(f)
            text = ocr_image(img)
            fields = extract_fields(text)
            warning_ok, warning_issues = warning_check(text)
            rows.append({
                "file": f.name,
                "brand": fields["brand_name"],
                "class/type": fields["class_type"],
                "ABV": fields["alcohol_content"],
                "net contents": fields["net_contents"],
                "warning": "PASS" if warning_ok else "REVIEW",
                "status": "REVIEW" if warning_issues else "Extracted"
            })
        elapsed = time.perf_counter() - start_all
        st.dataframe(rows, use_container_width=True)
        st.caption(f"Processed {len(batch)} labels in {elapsed:.2f}s total.")

st.divider()
st.caption("Prototype only. TTB/legal compliance requirements should be validated against current official guidance before production use.")
