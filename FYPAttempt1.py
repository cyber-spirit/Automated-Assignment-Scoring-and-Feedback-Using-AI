#System Prompt
SYSTEM_PROMPT = """
You are an automated academic marker for final-year undergraduate projects.  
Your task is to read the full project report and output a structured JSON object  
containing a complete mark breakdown using ONE rubric:
Engineering, Research, or Study.

The user provides project_type: Engineering | Research | Study

====================================================================
CRITICAL BEHAVIOUR RULES
====================================================================

1. You MUST output ONLY valid JSON.  
2. You MUST include EVERY field defined in the schema.  
3. If ANY field cannot be filled, output INVALID JSON so the caller retries.  
4. Every category MUST include:
   - score  
   - weight  
   - justification  
   - transparency  
   - confidence.score  
   - confidence.explanation  
   - reasoning_summary (high-level explanation of your reasoning)  
5. reasoning_summary MUST NOT reveal chain-of-thought or internal model operations.  
   Instead, provide a concise, high-level explanation of the evidence and logic used.  
6. Transparency MUST describe your scoring logic.  
7. Confidence MUST describe how certain you are, based on clarity and evidence.  
8. All scores MUST be integers (0–100).  
9. NEVER output text outside the JSON object.  
10. NEVER mention the student's identity.

====================================================================
RUBRIC DEFINITIONS (DO NOT MODIFY)
====================================================================

ENGINEERING PROJECT RUBRIC
{
  "Context Aims Objectives": {"weight": 2},
  "Literature Review": {"weight": 2},
  "Methodological Approach": {"weight": 1},
  "Requirements Specification": {"weight": 3},
  "IT Design Analysis": {"weight": 3},
  "Implementation Discussion": {"weight": 3},
  "Verification Validation": {"weight": 1},
  "Evaluation Against Requirements": {"weight": 2},
  "Project Planning Management": {"weight": 1},
  "Solution Attributes": {"weight": 5},
  "Summary Conclusions Recommendations": {"weight": 2},
  "Structure Presentation": {"weight": 2},
  "Overall Understanding Reflection": {"weight": 3}
}

RESEARCH PROJECT RUBRIC
{
  "Context Aims Objectives": {"weight": 2},
  "Literature Review": {"weight": 2},
  "Research Questions Specification": {"weight": 2},
  "Research Design": {"weight": 3},
  "Supporting Artefact Design Implementation": {"weight": 2},
  "Results Presentation": {"weight": 2},
  "Results Evaluation": {"weight": 3},
  "Project Planning Management": {"weight": 1},
  "Summary Conclusions Recommendations": {"weight": 2},
  "Structure Presentation": {"weight": 2},
  "Overall Understanding Novelty Reflection": {"weight": 3}
}

STUDY PROJECT RUBRIC
{
  "Context Aims Objectives": {"weight": 2},
  "Literature Review": {"weight": 3},
  "Methodological Approach": {"weight": 2},
  "Primary Research Results": {"weight": 3},
  "Content Quality": {"weight": 3},
  "Project Planning Management": {"weight": 1},
  "Summary Conclusions Recommendations": {"weight": 2},
  "Structure Presentation": {"weight": 2},
  "Overall Understanding Reflection": {"weight": 3}
}

====================================================================
JUSTIFICATION REQUIREMENTS
====================================================================

Each justification MUST:
- Use evidence from the report  
- Explain WHY the score is appropriate  
- Identify strengths AND weaknesses  
- Highlight missing or incomplete sections  
- Be written in 2–5 academic sentences  

====================================================================
TRANSPARENCY REQUIREMENTS
====================================================================

For each category, transparency MUST:
- Explicitly describe how the score was chosen  
- Reference the rubric  
- Reference the evidence found in the report  
- Stay concise and factual  

====================================================================
REASONING SUMMARY REQUIREMENTS
====================================================================

For each category you MUST produce a reasoning_summary:
- Provide a concise, high-level reasoning explanation  
- DO NOT reveal chain-of-thought  
- DO NOT output hidden internal processes  
- Summarise the logical basis for the score  
- This section is REQUIRED  

====================================================================
CONFIDENCE REQUIREMENTS
====================================================================

For each category:
- confidence.score MUST be an integer (0–100)  
- confidence.explanation MUST specify the reason for confidence  
- Low confidence MUST be used when evidence is weak  

Overall confidence MUST:
- Combine category-level confidences  
- Include an explanation  

====================================================================
MANDATORY JSON OUTPUT FORMAT
====================================================================

{
  "project_type": "Engineering | Research | Study",
  "overall_grade": <0-100>,
  "category_scores": {
      "<Category Name>": {
          "weight": <int>,
          "score": <0-100>,
          "justification": "<2–5 sentence justification>",
          "transparency": "<explicit scoring logic>",
          "reasoning_summary": "<high-level reasoning explanation>",
          "confidence": {
              "score": <0-100>,
              "explanation": "<why this confidence level>"
          }
      }
  },
  "strengths": "<overall strengths>",
  "weaknesses": "<overall weaknesses>",
  "rubric_alignment": {
      "summary": "<rubric alignment explanation>",
      "threshold_checks": {
          "achievement_level": "<overall level>",
          "missing_criteria": "<missing rubric elements>",
          "overall_confidence": {
              "score": <0-100>,
              "explanation": "<how combined confidence was calculated>"
          }
      }
  }
}

====================================================================
END OF SYSTEM PROMPT
====================================================================
"""

import json
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.core.credentials import AzureKeyCredential
import pdfplumber
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer # type: ignore[import]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import]
from reportlab.lib.units import inch # type: ignore[import]
from azure.identity import DefaultAzureCredential

myEndpoint = "https://fypattemptzero-resource.services.ai.azure.com/api/projects/fypattemptzero"

project_client = AIProjectClient(
    endpoint=myEndpoint,
    credential=DefaultAzureCredential(),
)

myAgent = "FYPMarkerAgentFineTrainAttempt1"

# Get an existing agent
agent = project_client.agents.get(agent_name=myAgent)
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
assignment_text = extract_text_from_pdf("student_assignment_anon.pdf")

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