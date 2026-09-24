# TTB Label Verification — Take-Home Prototype

## Overview

This prototype implements the core workflow requested in the take-home exercise:

1. Enter the structured application data.
2. Upload a label image.
3. Extract text locally with OCR when Tesseract is available.
4. Compare detected label values with application values.
5. Check the government-warning text.
6. Surface clear `Match`, `Mismatch`, and `Review` states.
7. Support multiple label uploads for batch processing.

The UI intentionally avoids a complex navigation structure so a user can understand the workflow quickly.

## Why this architecture

The stakeholder interviews emphasize three constraints:

- routine matching should be fast;
- the interface should be obvious for users with different levels of technical comfort;
- batch uploads are valuable during peak periods.

The prototype therefore keeps the critical path local and lightweight. It does **not** integrate with COLA and does not require a cloud AI endpoint.

For a production implementation, the OCR/extraction layer can be replaced with an approved agency-hosted model or an authorized AI/OCR service while retaining the verification and human-review layers.

## Run locally

### 1. Install Python

Python 3.10+ is recommended.

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

Tesseract OCR is optional but recommended.

On Windows, install Tesseract separately and make sure `tesseract.exe` is on PATH. If it is not on PATH, configure `pytesseract.pytesseract.tesseract_cmd` in `app.py`.

### 3. Start the application

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit.

## Test data

The README includes the sample distilled-spirits values from the assignment:

- Brand: OLD TOM DISTILLERY
- Class/Type: Kentucky Straight Bourbon Whiskey
- Alcohol: 45% Alc./Vol. (90 Proof)
- Net Contents: 750 mL

Create a sample image containing those values plus the government warning and upload it.

## Important prototype limitations

This is intentionally a take-home prototype, not a production compliance system.

- OCR accuracy depends on image quality and Tesseract availability.
- Exact legal warning validation should be driven by an authoritative, versioned ruleset rather than hard-coded prototype text.
- Application records are manually entered; there is no COLA integration.
- The prototype does not persist uploaded documents.
- No production PII/document-retention workflow is implemented.
- Human review is preserved for ambiguous matches.
- Batch processing currently demonstrates image throughput; production batch pairing should use application IDs and a CSV/API payload.

## Production evolution

A production design could use:

`Web UI -> API -> OCR/Document AI -> Normalization -> Rules Engine -> Match Scoring -> Human Review -> Audit Log`

Recommended controls:

- agency-approved hosting and identity/access management;
- encryption in transit and at rest;
- explicit retention/deletion policies;
- immutable audit events;
- versioned validation rules;
- model confidence and evidence displayed to reviewers;
- no automatic final approval/rejection solely from an AI score.

## Evaluation mapping

### Correctness/completeness
Core fields, warning validation, comparison states, and batch upload are implemented.

### Code quality
The prototype is organized around small extraction, normalization, comparison, and UI functions.

### Technical choices
Streamlit keeps the take-home deployable and easy to test. Local OCR reduces dependency on outbound cloud APIs.

### UX/error handling
The interface uses a short linear workflow, visible statuses, editable OCR text, and explicit review states.

### Creative problem solving
The prototype treats AI/OCR as an assistive extraction layer rather than an opaque final decision-maker. This directly supports human review of nuanced cases such as capitalization or minor formatting differences.

## Deployment

A Streamlit-compatible environment can run the application using:

```bash
streamlit run app.py --server.port 8501
```

For a federal production environment, deployment and authorization would need to follow the agency's applicable security, privacy, hosting, and authorization requirements.
