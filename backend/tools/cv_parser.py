"""
CV parsing tool.
- parse_cv(): extracts raw text from PDF (PyMuPDF) or DOCX (python-docx)
- extract_cv_structure(): sends raw text to Groq (Llama 3.1 8B) and returns structured JSON
"""
import io
import json
import os
from groq import AsyncGroq

# ── Raw text extraction ────────────────────────────────────────────────────────

def parse_cv(content: bytes, content_type: str) -> str:
    """Extract plain text from a PDF or DOCX byte payload."""
    if content_type == "application/pdf":
        return _parse_pdf(content)
    elif content_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return _parse_docx(content)
    raise ValueError(f"Unsupported content type: {content_type}")


def _parse_pdf(content: bytes) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=content, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    return "\n".join(pages)


def _parse_docx(content: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(content))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


# ── Claude structured extraction ───────────────────────────────────────────────

CV_EXTRACTION_PROMPT = """\
You are a CV parser. Extract structured data from the following CV text and return ONLY valid JSON — no markdown, no explanation.

Return this exact schema:
{
  "summary": "<2-3 sentence professional summary>",
  "skills": ["skill1", "skill2", ...],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "duration": "Jan 2022 – Present",
      "bullets": ["bullet 1", "bullet 2"]
    }
  ],
  "education": [
    {
      "degree": "MSc Artificial Intelligence",
      "institution": "University Name",
      "year": "2024"
    }
  ],
  "languages": ["Python", "TypeScript"],
  "certifications": []
}

CV text:
{cv_text}
"""


async def extract_cv_structure(raw_text: str) -> dict:
    """Send raw CV text to Groq (Llama 3.1 8B), return parsed structured dict."""
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    message = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": CV_EXTRACTION_PROMPT.replace("{cv_text}", raw_text[:8000]),
            }
        ],
    )

    raw_json = message.choices[0].message.content.strip()

    # Strip markdown code fences if the model wraps it
    if raw_json.startswith("```"):
        raw_json = raw_json.split("```")[1]
        if raw_json.startswith("json"):
            raw_json = raw_json[4:]

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        # Fallback: return minimal structure so the endpoint doesn't crash
        return {
            "summary": "Could not parse CV structure.",
            "skills": [],
            "experience": [],
            "education": [],
            "languages": [],
            "certifications": [],
            "raw_parse_error": True,
        }
