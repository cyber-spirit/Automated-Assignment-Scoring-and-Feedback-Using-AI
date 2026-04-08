import json
import ollama
from pypdf import PdfReader
from fpdf import FPDF

#Mark schemes for the 3 different fyp project types.
MARK_SCHEMES = {
    "Engineering": {
        "context aims objectives": {"weight": 2, "description": "Clarity and framing of problem, context, aims, objectives, and challenge level."},
        "literature review": {"weight": 2, "description": "Quality, depth, criticality, relevance, and completeness of literature review."},
        "methodological approach": {"weight": 1, "description": "Appropriateness, justification, application, and clarity of methodology and lifecycle."},
        "requirements specification": {"weight": 3, "description": "Completeness, justification, consistency, and analysis of system requirements."},
        "it design analysis": {"weight": 3, "description": "System design decisions, architectures, interfaces, and design rationale."},
        "implementation discussion": {"weight": 3, "description": "Implementation decisions, trade-offs, algorithms, data structures, tools, command of techniques."},
        "verification validation": {"weight": 1, "description": "Testing, debugging, verification, validation and justification of approaches."},
        "evaluation against requirements": {"weight": 2, "description": "Evaluation methods, evidence of meeting requirements, limitations, and discussion."},
        "project planning management": {"weight": 1, "description": "Project plan, adherence, progress evaluation, and project management methodology."},
        "solution attributes": {"weight": 5, "description": "Quality of artefact including reliability, completeness, maintainability, timeliness."},
        "summary conclusions recommendations": {"weight": 2, "description": "Summary, conclusions, recommendations, originality, and alignment with evidence."},
        "structure presentation": {"weight": 2, "description": "Report structure, clarity, readability, grammar, diagrams, page layout."},
        "overall understanding reflection": {"weight": 3, "description": "Evidence of understanding, reflection, critical insight, awareness of limitations."}
    },
    "Research": {
        "context aims objectives": {"weight": 2, "description": "Research topic framing, aims, objectives, context, and challenge level."},
        "literature review": {"weight": 2, "description": "Breadth, depth, relevance, critique, current sources, and credibility."},
        "research questions specification": {"weight": 2, "description": "Clarity, relevance, formalisation, measurability, justification of research questions."},
        "research design": {"weight": 3, "description": "Design of approach, methodology, data collection, analysis processes, ethics."},
        "supporting artefact design implementation": {"weight": 2, "description": "Design and implementation decisions for supporting artefact/software."},
        "results presentation": {"weight": 2, "description": "Clarity and correctness of results, graphs, avoiding bias, context provided."},
        "results evaluation": {"weight": 3, "description": "Interpretation of results, correctness, insight, meeting research questions."},
        "project planning management": {"weight": 1, "description": "Project planning, timeline, work schedule, progress evaluation."},
        "summary conclusions recommendations": {"weight": 2, "description": "Summary, conclusions, recommendations, insight, linkage to research questions."},
        "structure presentation": {"weight": 2, "description": "Organisation, clarity, grammar, structure, diagrams, fluency."},
        "overall understanding reflection": {"weight": 3, "description": "Understanding, novelty, critical insight, awareness of limitations."}
    },
    "Study": {
        "context aims objectives": {"weight": 2, "description": "Framing of research topic, aims, objectives, challenge, context."},
        "literature review": {"weight": 3, "description": "Quality, depth, relevance, critical insight, search strategy, originality."},
        "methodological approach": {"weight": 2, "description": "Appropriateness, justification, and application of methodology used."},
        "primary research results": {"weight": 3, "description": "Design and execution of any primary research, data evaluation and interpretation."},
        "content quality": {"weight": 3, "description": "Analysis level, originality, insight, structure, and breadth of topic coverage."},
        "project planning management": {"weight": 1, "description": "Planning, scheduling, progress tracking, resource management."},
        "summary conclusions recommendations": {"weight": 2, "description": "Appropriateness of conclusions, linkage to objectives, support from report."},
        "structure presentation": {"weight": 2, "description": "Structure, fluency, clarity, grammar, diagrams, presentation quality."},
        "overall understanding reflection": {"weight": 3, "description": "Understanding, analysis, critical reflection, awareness of strengths/weaknesses."}
    }
}

#This extracts the text from the pdf.
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n".join([page.extract_text() for page in reader.pages])

#This function sends the query to the deepseek model.
def grade_with_ollama_streaming(text, system_prompt):
    print("\n---Model Output:---\n")
    full_text = ""
    response = ollama.chat(
        model='deepseek-r1:8b',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"Here is the student work:\n\n{text}"}
        ],
        stream=True
    )
    
    #This is for printing to the terminal in real time.
    for chunk in response:
        content = chunk['message']['content']
        print(content, end='', flush=True) 
        full_text += content
    
    print("\n\n--- MODEL OUTPUT END ---\n")
    return full_text

#This converts the model response into a pdf format.
def create_pdf(text_content, output_filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    
    #this cleans the string
    clean_text = text_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, clean_text)
    pdf.output(output_filename)

if __name__ == "__main__":
    STUDENT_WORK = "studentReport.pdf"

    system_prompt = f"""
    You are a professional academic examiner. 
    Below are three mark schemes in JSON format:
    {json.dumps(MARK_SCHEMES, indent=2)}

    TASK:
    1. Identify if the student work is an 'Engineering', 'Research', or 'Study' project.
    2. Mark the work strictly against the chosen scheme's descriptions and weights.
    3. Never mention the student's identiy or any personal details.
    4. Mark objectively based on the content provided, not on assumptions about the student.
    5. Provide a clear breakdown of marks for each section and an overall grade out of 100. 
    6. Assess grammar, readability, and writing quality separately, and provide a plagiarism probability and AI usage probability based on the text analysis.
    7. Provide the following structured output:

    --- SCORE SUMMARY ---
    Selected Mark Scheme: [Name]
    Overall Grade: [Weighted total]/100
    Grammar & Readability: [0-10]
    Plagiarism Probability: [0-100%]
    AI Usage Probability: [0-100%]

    --- DETAILED SECTION FEEDBACK ---
    For each section defined in the chosen JSON scheme, provide:
    [Section Name]:
    [One paragraph of specific evidence-based feedback and the marks awarded for that section.]
    """

    try:
        #Extracts text from pdf
        print(f"Reading {STUDENT_WORK}...")
        pdf_text = extract_text_from_pdf(STUDENT_WORK)
        
        #Sends the text to the model and gets the feedback.
        ai_feedback = grade_with_ollama_streaming(pdf_text, system_prompt)
        
        #Creates a pdf with the feedback and marks
        create_pdf(ai_feedback, "marked_report.pdf")
        print("Marking complete. 'marked_report.pdf' has been generated.")
        
    except Exception as e:
        print(f"An error occurred: {e}")