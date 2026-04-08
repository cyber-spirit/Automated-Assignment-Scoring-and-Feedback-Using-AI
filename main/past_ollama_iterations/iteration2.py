#!/usr/bin/env python3

import json
import re
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

import requests
import argparse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

pdfAvailable = True

class OllamaMarker:

    def __init__(self, model: str = "deepseek-r1:8b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.api_generate = f"{self.base_url}/api/generate"
        self.response_time = None

    @staticmethod
    def read_file(filepath: str) -> str:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        return path.read_text(encoding='utf-8')

    @staticmethod
    def create_marking_prompt(mark_scheme: str, student_work: str) -> str:
        return f"""You are an expert marker. Mark the following student work against the provided mark scheme.

MARK SCHEME:
{mark_scheme}

STUDENT WORK:
{student_work}

Return your evaluation as a **valid JSON object** with exactly this structure:
{{
    "total_marks": <number>,
    "maximum_marks": <number>,
    "criteria_breakdown": [
        {{
            "criterion": "<name>",
            "marks_awarded": <number>,
            "maximum_marks": <number>,
            "feedback": "<text>"
        }}
    ],
    "overall_feedback": "<text>",
    "strengths": ["<strength1>", "<strength2>", "<strength3>"],
    "areas_for_improvement": ["<area1>", "<area2>", "<area3>"]
}}

Do not add any text before or after the JSON. The output must be parsable JSON.
"""

    def query_ollama_streaming(self, prompt: str, timeout: int = 600) -> str:
        print(f"Querying model... '{self.model}' ")
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "max_tokens": 2048,
                "top_k": 40,
                "repeat_penalty": 1.1,
                "num_ctx": 4096
            }
        }

        full_response = []
        start = time.time()

        try:
            with requests.post(self.api_generate, json=payload, stream=True, timeout=timeout) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            print(chunk['response'], end='', flush=True)
                            full_response.append(chunk['response'])
                        if chunk.get('done'):
                            break
        except Exception as e:
            print(f"\nError during streaming: {e}")
            raise

        self.response_time = time.time() - start
        print("\n\n" + "=" * 50)
        print(f"Streaming finished in {self.response_time:.1f} seconds.")
        return ''.join(full_response)

    @staticmethod
    def extract_json_from_response(text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError("Could not extract valid JSON from the model's response.")

    @staticmethod
    def save_json(data: Dict[str, Any], path: str) -> None:
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"JSON saved to: {path}")

    def generate_pdf(self, results: Dict[str, Any], mark_scheme_path: str,
                     student_work_path: str, pdf_path: str) -> None:
        if not pdfAvailable:
            print("ReportLab not installed.")
            return

        print(f"Generating PDF: {pdf_path}")
        doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)

        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                     fontSize=24, alignment=1, textColor=colors.HexColor('#2C3E50'))
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'],
                                       fontSize=16, textColor=colors.HexColor('#34495E'),
                                       spaceAfter=12, spaceBefore=20)
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'],
                                      fontSize=11, leading=14)

        story.append(Paragraph("Student Work Assessment Report", title_style))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}", normal_style))
        if self.response_time:
            story.append(Paragraph(f"Processing time: {self.response_time:.1f} s", normal_style))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Files", heading_style))
        story.append(Paragraph(f"• Mark scheme: {Path(mark_scheme_path).name}", normal_style))
        story.append(Paragraph(f"• Student work: {Path(student_work_path).name}", normal_style))
        story.append(Spacer(1, 0.2 * inch))

        total = results.get('total_marks', 0)
        maximum = results.get('maximum_marks', 1)
        percent = (total / maximum * 100) if maximum else 0
        score_text = f"<b>Overall Score: {total}/{maximum} ({percent:.1f}%)</b>"
        score_table = Table([[Paragraph(score_text, ParagraphStyle('Score', fontSize=14, alignment=1))]],
                            colWidths=[doc.width])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Criteria Breakdown", heading_style))
        criteria = results.get('criteria_breakdown', [])
        if criteria:
            data = [['Criterion', 'Marks', 'Feedback']]
            for c in criteria:
                data.append([
                    c.get('criterion', ''),
                    f"{c.get('marks_awarded', 0)}/{c.get('maximum_marks', 0)}",
                    c.get('feedback', '')[:100] + ('...' if len(c.get('feedback', '')) > 100 else '')
                ])
            table = Table(data, colWidths=[doc.width*0.3, doc.width*0.15, doc.width*0.45])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No criteria breakdown provided.", normal_style))
        story.append(Spacer(1, 0.2 * inch))

        strengths = results.get('strengths', [])
        if strengths:
            story.append(Paragraph("Strengths", heading_style))
            for s in strengths:
                story.append(Paragraph(f"• {s}", normal_style))
            story.append(Spacer(1, 0.2 * inch))

        areas = results.get('areas_for_improvement', [])
        if areas:
            story.append(Paragraph("Areas for Improvement", heading_style))
            for a in areas:
                story.append(Paragraph(f"• {a}", normal_style))
            story.append(Spacer(1, 0.2 * inch))

        if 'overall_feedback' in results:
            story.append(Paragraph("Overall Feedback", heading_style))
            feedback_para = Paragraph(results['overall_feedback'], normal_style)
            feedback_table = Table([[feedback_para]], colWidths=[doc.width])
            feedback_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F9F9F9')),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#BDC3C7')),
                ('PADDING', (0, 0), (-1, -1), 15),
            ]))
            story.append(feedback_table)

        doc.build(story)
        print(f"PDF created: {pdf_path}")

    def mark(self, mark_scheme_path: str, student_work_path: str,
             output_json: Optional[str] = None,
             output_pdf: Optional[str] = None,
             timeout: int = 600) -> Dict[str, Any]:
        print("=" * 60)
        print("OLLAMA MARKER - Starting marking process")
        print("=" * 60)

        mark_scheme = self.read_file(mark_scheme_path)
        student_work = self.read_file(student_work_path)

        prompt = self.create_marking_prompt(mark_scheme, student_work)

        raw_response = self.query_ollama_streaming(prompt, timeout=timeout)

        result = self.extract_json_from_response(raw_response)

        print("\nSummary:")
        print(f"   Total marks: {result.get('total_marks', '?')}/{result.get('maximum_marks', '?')}")
        print(f"   Strengths: {len(result.get('strengths', []))} / Areas: {len(result.get('areas_for_improvement', []))}")

        if output_json:
            self.save_json(result, output_json)

        if output_pdf:
            self.generate_pdf(result, mark_scheme_path, student_work_path, output_pdf)

        return result

def main() -> int:
    parser = argparse.ArgumentParser(description="Mark student work using an Ollama model.")
    args = parser.parse_args()

    try:
        r = requests.get(f"{args.url}/api/tags", timeout=5)
        r.raise_for_status()
        print(f"Connected to Ollama at {args.url}")
    except Exception as e:
        print(f"Cannot connect to Ollama: {e}")
        print("Make sure Ollama is running (run 'ollama serve')")
        return 1

    if args.pdf and not pdfAvailable:
        print("PDF requested but reportlab is not installed.")
        args.pdf = None

    try:
        marker = OllamaMarker(model=args.model, base_url=args.url)
        marker.mark(
            mark_scheme_path=args.mark_scheme,
            student_work_path=args.student_work,
            output_json=args.output,
            output_pdf=args.pdf,
            timeout=args.timeout
        )
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    print("Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())