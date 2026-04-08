import json
import csv
import ollama
from pypdf import PdfReader
from fpdf import FPDF

#This function takes the mark schemes from a csv file (mark_schemes.csv) and converts them into a nested dictionary for use by the model.
def load_mark_schemes_from_csv(csv_path):
    mark_schemes = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                project_type = row['project_type'].strip()
                criterion = row['criterion_name'].strip()
                weight = int(row['weight'])
                description = row['description'].strip()
                
                if project_type not in mark_schemes:
                    mark_schemes[project_type] = {}
                mark_schemes[project_type][criterion] = {
                    "weight": weight,
                    "description": description
                }
        return mark_schemes
    except FileNotFoundError:
        print(f"CSV file '{csv_path}' not found.")
        raise
    except Exception as e:
        print(f"Issue loading CSV: {e}")
        raise

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n".join([page.extract_text() for page in reader.pages])

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
    
    for chunk in response:
        content = chunk['message']['content']
        print(content, end='', flush=True)
        full_text += content
    
    print("\n\n--- MODEL OUTPUT END ---\n")
    return full_text

#Note: the clean text is needed here because the model can output some characters that fpdf cant use and will throw an error for.
#this replaces those characters with a ?.
#e.g: the model could use chinese characters for example which would cause fpdf to error.
def create_pdf(text_content, output_filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    clean_text = text_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, clean_text)
    pdf.output(output_filename)

if __name__ == "__main__":
    STUDENT_WORK = "studentReport.pdf"
    MARK_SCHEMES = "markSchemes.csv"

    try:
        MARK_SCHEMES = load_mark_schemes_from_csv(MARK_SCHEMES)
    except:
        print("Failed to load mark schemes.")
        exit(1)  

    system_prompt = f"""
    You are a professional academic examiner for the University of Portsmouth. 
    Below are three mark schemes in JSON format:
    {json.dumps(MARK_SCHEMES, indent=2)}

    TASK:
    1. Identify if the student work is an 'Engineering', 'Research', or 'Study' project.
    2. Mark the work strictly against the chosen scheme's descriptions and weights.
    3. Never mention the student's identity or any personal details.
    4. Mark objectively based on the content provided, not on assumptions about the student.
    5. Provide a clear breakdown of marks for each section and an overall grade out of 100. 
    6. Provide the following structured output:

    --- SCORE SUMMARY ---
    Selected Mark Scheme: [Name]
    Overall Grade: [Weighted total]/100
    Grammar & Readability: [0/10]
    Plagiarism Probability: [0-100%]
    AI Usage Probability: [0-100%]

    --- DETAILED SECTION FEEDBACK ---
    For each section defined in the chosen JSON scheme, provide:
    [Section Name (In Capitalized Form)]:
    [One paragraph of specific evidence-based feedback and the marks awarded for that section.]
    [Divider to the next section, e.g., '---']
    """

    try:
        print(f"Reading {STUDENT_WORK}...")
        pdf_text = extract_text_from_pdf(STUDENT_WORK)
        ai_feedback = grade_with_ollama_streaming(pdf_text, system_prompt)
        create_pdf(ai_feedback, "markedReport.pdf")
        print("Marking completed. 'markedReport.pdf' has been generated.")
    except Exception as e:
        print(f"An error occurred: {e}")