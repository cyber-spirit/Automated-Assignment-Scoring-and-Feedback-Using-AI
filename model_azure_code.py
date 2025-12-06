import json
from azure.ai.projects import AIProjectClient
import pdfplumber
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer # type: ignore[import]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import]
from reportlab.lib.units import inch # type: ignore[import]
from azure.identity import DefaultAzureCredential

MY_ENDPOINT = "https://fypattemptzero-resource.services.ai.azure.com/api/projects/fypattemptzero"

project_client = AIProjectClient(
    endpoint=MY_ENDPOINT,
    credential=DefaultAzureCredential(),
)

MY_AGENT = "FYPMarkerAgentFineTrainAttempt1"

# Get an existing agent
agent = project_client.agents.get(agent_name=MY_AGENT)
print(f"Retrieved agent: {agent.name}")
openai_client = project_client.get_openai_client()
#===========================================================================================#
#Get data from assignment
def extract_text_from_pdf(pdf_path):
    """
    Extract all text from a multi-page PDF file.
    Returns a single long text string.
    """
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text
#===========================================================================================#
#Request marking run from agent
assignment_text = extract_text_from_pdf("john_smith_final_year_project.pdf")

response = openai_client.responses.create(
    input=[
        {
            "role": "user",
            "content": f"project_type: Engineering\n\nAssignment:\n{assignment_text}"
        }
    ],
    extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
)

model_json_output = response.output_text
grades = json.loads(model_json_output)
#===========================================================================================#
#Raw Output
print("RAW MODEL OUTPUT:")
print(response.output_text)
try:
    grades = json.loads(model_json_output)
except Exception as e:
    print("JSON parsing failed:", e)
    raise
#===========================================================================================#
#Creation and formatting of pdf
def create_feedback_pdf(json_data, pdf_path):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path)

    story = []

    # Header
    story.append(Paragraph(f"<b>Project Type:</b> {json_data['project_type']}", styles['Title']))
    story.append(Paragraph(f"<b>Overall Grade:</b> {json_data['overall_grade']}", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))

    # Category Scores
    story.append(Paragraph("<b>Category Scores</b>", styles['Heading1']))

    for cat, info in json_data["category_scores"].items():

        story.append(Paragraph(f"<br/><b>{cat}</b> (Weight {info['weight']})", styles['Heading2']))
        story.append(Paragraph(f"<b>Score:</b> {info['score']}", styles['Normal']))

        story.append(Paragraph(f"<b>Justification:</b> {info['justification']}", styles['Normal']))
        story.append(Paragraph(f"<b>Transparency:</b> {info['transparency']}", styles['Normal']))
        story.append(Paragraph(f"<b>Reasoning Summary:</b> {info['reasoning_summary']}", styles['Normal']))

        # Confidence is a nested object
        conf = info.get("confidence", {})
        story.append(Paragraph(
            f"<b>Confidence:</b> {conf.get('score', 'N/A')} – {conf.get('explanation', '')}",
            styles['Normal']
        ))

        story.append(Spacer(1, 0.2*inch))

    # Strengths
    story.append(Paragraph("<b>Strengths</b>", styles['Heading1']))
    story.append(Paragraph(json_data["strengths"], styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Weaknesses
    story.append(Paragraph("<b>Weaknesses</b>", styles['Heading1']))
    story.append(Paragraph(json_data["weaknesses"], styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Rubric Alignment
    story.append(Paragraph("<b>Rubric Alignment</b>", styles['Heading1']))
    ra = json_data["rubric_alignment"]

    story.append(Paragraph(f"<b>Summary:</b> {ra['summary']}", styles['Normal']))

    # Threshold Checks
    tc = ra["threshold_checks"]
    story.append(Paragraph("<b>Threshold Checks</b>", styles['Heading2']))
    story.append(Paragraph(f"<b>Missing Criteria:</b> {tc['missing_criteria']}", styles['Normal']))

    # Overall Confidence
    oc = tc["overall_confidence"]
    story.append(Paragraph(
        f"<b>Overall Confidence:</b> {oc['score']} – {oc['explanation']}",
        styles['Normal']
    ))

    doc.build(story)

create_feedback_pdf(grades, "student_feedback.pdf")
print("PDF created: student_feedback.pdf")

#Logging into azure CLI command:
# az login --use-device-code