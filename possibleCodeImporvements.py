import json
import argparse
import logging
from typing import Any, Dict
from azure.ai.projects import AIProjectClient
import pdfplumber
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer  # type: ignore[import]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import]
from reportlab.lib.units import inch  # type: ignore[import]
from azure.identity import DefaultAzureCredential

# Summary: refactored constants (don't modify original script)
DEFAULT_ENDPOINT = "https://fypattemptzero-resource.services.ai.azure.com/api/projects/fypattemptzero"
DEFAULT_AGENT = "FYPMarkerAgentFineTrainAttempt1"

# ---------- helper functions ----------
def get_project_client(endpoint: str) -> AIProjectClient:
    credential = DefaultAzureCredential()
    return AIProjectClient(endpoint=endpoint, credential=credential)

def get_agent(project_client: AIProjectClient, agent_name: str):
    return project_client.agents.get(agent_name=agent_name)

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    return text

def request_marking(openai_client, agent_name: str, project_type: str, assignment_text: str) -> str:
    resp = openai_client.responses.create(
        input=[{"role": "user", "content": f"project_type: {project_type}\n\nAssignment:\n{assignment_text}"}],
        extra_body={"agent": {"name": agent_name, "type": "agent_reference"}},
    )
    return resp.output_text

def validate_grades_json(data: Dict[str, Any]) -> None:
    required_top = {"project_type", "overall_grade", "category_scores", "strengths", "weaknesses", "rubric_alignment"}
    missing = required_top - set(data.keys())
    if missing:
        raise ValueError(f"Missing top-level fields: {', '.join(sorted(missing))}")
    if not isinstance(data.get("category_scores", {}), dict) or len(data["category_scores"]) == 0:
        raise ValueError("category_scores must be a non-empty object")
    for cat, info in data["category_scores"].items():
        for f in ("weight", "score", "justification", "transparency", "reasoning_summary", "confidence"):
            if f not in info:
                raise ValueError(f"Category '{cat}' missing field: {f}")
        conf = info["confidence"]
        if not isinstance(conf, dict) or "score" not in conf or "explanation" not in conf:
            raise ValueError(f"Category '{cat}' has invalid confidence")

def create_feedback_pdf(json_data: Dict[str, Any], pdf_path: str) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path)
    story = []
    story.append(Paragraph(f"<b>Project Type:</b> {json_data['project_type']}", styles['Title']))
    story.append(Paragraph(f"<b>Overall Grade:</b> {json_data['overall_grade']}", styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("<b>Category Scores</b>", styles['Heading1']))
    for cat, info in json_data["category_scores"].items():
        story.append(Paragraph(f"<br/><b>{cat}</b> (Weight {info['weight']})", styles['Heading2']))
        story.append(Paragraph(f"<b>Score:</b> {info['score']}", styles['Normal']))
        story.append(Paragraph(f"<b>Justification:</b> {info['justification']}", styles['Normal']))
        story.append(Paragraph(f"<b>Transparency:</b> {info['transparency']}", styles['Normal']))
        story.append(Paragraph(f"<b>Reasoning Summary:</b> {info['reasoning_summary']}", styles['Normal']))
        conf = info.get("confidence", {})
        story.append(Paragraph(f"<b>Confidence:</b> {conf.get('score','N/A')} – {conf.get('explanation','')}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("<b>Strengths</b>", styles['Heading1']))
    story.append(Paragraph(json_data["strengths"], styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("<b>Weaknesses</b>", styles['Heading1']))
    story.append(Paragraph(json_data["weaknesses"], styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    ra = json_data["rubric_alignment"]
    story.append(Paragraph("<b>Rubric Alignment</b>", styles['Heading1']))
    story.append(Paragraph(f"<b>Summary:</b> {ra.get('summary','')}", styles['Normal']))
    tc = ra.get("threshold_checks", {})
    story.append(Paragraph("<b>Threshold Checks</b>", styles['Heading2']))
    story.append(Paragraph(f"<b>Missing Criteria:</b> {tc.get('missing_criteria','')}", styles['Normal']))
    oc = tc.get("overall_confidence", {})
    story.append(Paragraph(f"<b>Overall Confidence:</b> {oc.get('score','N/A')} – {oc.get('explanation','')}", styles['Normal']))
    doc.build(story)

# ---------- CLI / main ----------
def main():
    parser = argparse.ArgumentParser(description="Refactored FYP marker runner (does not edit original script).")
    parser.add_argument("--input", "-i", default="student_assignment_anon.pdf")
    parser.add_argument("--output", "-o", default="student_feedback_refactor.pdf")
    parser.add_argument("--endpoint", "-e", default=DEFAULT_ENDPOINT)
    parser.add_argument("--agent", "-a", default=DEFAULT_AGENT)
    parser.add_argument("--project_type", "-p", default="Engineering", choices=["Engineering","Research","Study"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    try:
        logging.info("Creating AI Projects client...")
        pc = get_project_client(args.endpoint)
        agent = get_agent(pc, args.agent)
        logging.info(f"Using agent: {agent.name}")
        openai_client = pc.get_openai_client()

        logging.info("Extracting text from PDF...")
        assignment_text = extract_text_from_pdf(args.input)

        logging.info("Requesting marking...")
        raw = request_marking(openai_client, agent.name, args.project_type, assignment_text)

        logging.info("Parsing JSON output...")
        grades = json.loads(raw)
        validate_grades_json(grades)

        logging.info("Creating feedback PDF...")
        create_feedback_pdf(grades, args.output)
        logging.info(f"PDF written to {args.output}")
    except Exception as err:
        logging.exception("Runner failed:")
        raise

if __name__ == "__main__":
    main()
