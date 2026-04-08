import json
import os
import sys
import requests
from typing import Dict, List, Any
import argparse
from pathlib import Path

class OllamaMarker:
    def __init__(self, model_name="deepseek-r1:8b", base_url="http://localhost:11434"):
        """
        Initialize the Ollama marker.
        
        Args:
            model_name: The name of the Ollama model to use
            base_url: The URL where Ollama is running (default is localhost:11434)
        """
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        
    def read_file(self, filepath: str) -> str:
        """Read content from a file with better error handling."""
        file_path = Path(filepath)
        
        # Print current working directory for debugging
        print(f"Current working directory: {Path.cwd()}")
        print(f"Looking for file: {file_path.absolute()}")
        
        try:
            if not file_path.exists():
                print(f"Error: File {filepath} not found.")
                print(f"Absolute path tried: {file_path.absolute()}")
                print("\nFiles in current directory:")
                for f in Path.cwd().glob('*'):
                    print(f"  - {f.name}")
                raise FileNotFoundError(f"Could not find file: {filepath}")
                
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                print(f"Successfully read {len(content)} characters from {filepath}")
                return content
                
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            raise
    
    def create_marking_prompt(self, mark_scheme: str, student_work: str) -> str:
        """
        Create a prompt for the model to mark the student work.
        """
        prompt = f"""You are an expert marker. Your task is to mark the following student work against the provided mark scheme.

MARK SCHEME:
{mark_scheme}

STUDENT WORK:
{student_work}

Please mark this work and provide your response in the following JSON format exactly. Make sure to parse the mark scheme carefully to determine the maximum possible marks:

{{
    "total_marks": <total marks awarded>,
    "maximum_marks": <maximum marks possible>,
    "criteria_breakdown": [
        {{
            "criterion": "<name of criterion>",
            "marks_awarded": <marks>,
            "maximum_marks": <maximum>,
            "feedback": "<specific feedback for this criterion>"
        }}
    ],
    "overall_feedback": "<comprehensive feedback on the student's work>",
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "areas_for_improvement": ["<area 1>", "<area 2>", "<area 3>"]
}}

Important: Your response must be valid JSON. Do not include any additional text before or after the JSON."""
        
        return prompt
    
    def query_ollama(self, prompt: str) -> str:
        """
        Send a query to Ollama and get the response.
        """
        print(f"Querying Ollama with model {self.model_name}...")
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent marking
                "top_p": 0.9,
                "max_tokens": 2000
            }
        }
        
        try:
            # Check if Ollama is running
            try:
                requests.get(f"{self.base_url}/api/tags", timeout=2)
            except requests.exceptions.ConnectionError:
                print("\n❌ ERROR: Cannot connect to Ollama!")
                print("Make sure Ollama is running by executing one of these commands:")
                print("  - 'ollama serve' (if Ollama is installed)")
                print("  - Check if Ollama application is running")
                print(f"  - Verify Ollama is accessible at: {self.base_url}")
                raise
            
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
            
        except requests.exceptions.Timeout:
            print("Error: Request to Ollama timed out. The model might be taking too long to respond.")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Ollama: {e}")
            raise
    
    def extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from the model's response.
        """
        print("Extracting JSON from response...")
        
        try:
            # First, try to parse the entire response as JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # If that fails, try to find JSON within the response
            import re
            
            # Look for JSON object pattern
            json_pattern = r'\{[^{}]*(\{[^{}]*\}[^{}]*)*\}'
            match = re.search(json_pattern, response, re.DOTALL)
            
            if match:
                json_str = match.group()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Found JSON-like content but couldn't parse it: {e}")
                    print("First 200 characters of response:")
                    print(response[:200])
                    raise
            else:
                print("No JSON found in response")
                print("First 200 characters of response:")
                print(response[:200])
                raise
    
    def mark_submission(self, mark_scheme_file: str, student_work_file: str, output_file: str = None):
        """
        Main method to mark a student submission.
        """
        print("\n" + "="*60)
        print("OLLAMA MARKER - Starting marking process")
        print("="*60)
        
        # Read mark scheme
        print(f"\n📄 Reading mark scheme from: {mark_scheme_file}")
        try:
            mark_scheme = self.read_file(mark_scheme_file)
            print("✓ Mark scheme loaded successfully")
        except FileNotFoundError:
            print("❌ Failed to load mark scheme")
            return None
        
        # Read student work
        print(f"\n📝 Reading student work from: {student_work_file}")
        try:
            student_work = self.read_file(student_work_file)
            print("✓ Student work loaded successfully")
        except FileNotFoundError:
            print("❌ Failed to load student work")
            return None
        
        # Create prompt
        print("\n🤖 Creating marking prompt...")
        prompt = self.create_marking_prompt(mark_scheme, student_work)
        print(f"✓ Prompt created ({len(prompt)} characters)")
        
        # Query Ollama
        print("\n🔄 Querying Ollama (this may take a moment)...")
        try:
            response = self.query_ollama(prompt)
            print("✓ Received response from Ollama")
        except Exception as e:
            print(f"❌ Failed to get response from Ollama: {e}")
            return None
        
        # Extract JSON
        print("\n📊 Processing results...")
        try:
            result = self.extract_json_from_response(response)
            print("✓ Successfully parsed JSON response")
        except Exception as e:
            print(f"❌ Failed to parse response: {e}")
            return None
        
        # Print summary to console
        print("\n" + "="*60)
        print("📋 MARKING RESULTS")
        print("="*60)
        print(f"Total Marks: {result.get('total_marks', 'N/A')}/{result.get('maximum_marks', 'N/A')}")
        print(f"\nOverall Feedback: {result.get('overall_feedback', 'N/A')}")
        
        if 'strengths' in result:
            print("\n💪 Strengths:")
            for strength in result['strengths']:
                print(f"  • {strength}")
        
        if 'areas_for_improvement' in result:
            print("\n📈 Areas for Improvement:")
            for area in result['areas_for_improvement']:
                print(f"  • {area}")
        print("="*60)
        
        # Save to file if specified
        if output_file:
            self.save_results(result, output_file)
            print(f"\n💾 Results saved to: {output_file}")
        
        return result
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """Save results to a JSON file."""
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

def check_ollama_installation():
    """Check if Ollama is properly installed and running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✓ Ollama is running with {len(models)} model(s) available")
            return True
    except:
        return False

def main():
    parser = argparse.ArgumentParser(description='Mark student work using Ollama')
    parser.add_argument('mark_scheme', nargs='?', default='markscheme.txt',
                       help='Path to the mark scheme file (default: markscheme.txt)')
    parser.add_argument('student_work', nargs='?', default='student_work.txt',
                       help='Path to the student work file (default: student_work.txt)')
    parser.add_argument('--output', '-o', help='Output JSON file path (optional)')
    parser.add_argument('--model', '-m', default='deepseek-r1:8b', 
                       help='Ollama model name (default: deepseek-r1:8b)')
    parser.add_argument('--url', '-u', default='http://localhost:11434',
                       help='Ollama API URL (default: http://localhost:11434)')
    
    args = parser.parse_args()
    
    print("\n🔍 OLLAMA MARKER - Initializing...")
    print("-" * 40)
    
    # Check if Ollama is running
    if not check_ollama_installation():
        print("\n❌ ERROR: Cannot connect to Ollama!")
        print("\nPlease ensure Ollama is running:")
        print("1. Open a new terminal")
        print("2. Run: ollama serve")
        print("3. Or if Ollama is installed as an application, launch it")
        print("\nIf Ollama is not installed, download it from: https://ollama.ai")
        return 1
    
    # Check if the model is available
    try:
        response = requests.get(f"{args.url}/api/tags")
        models = response.json().get('models', [])
        model_names = [m['name'] for m in models]
        
        if args.model not in model_names:
            print(f"\n⚠️  Warning: Model '{args.model}' not found in your Ollama installation.")
            print(f"Available models: {', '.join(model_names) if model_names else 'None'}")
            print(f"\nTo pull the model, run: ollama pull {args.model}")
            
            # Ask user if they want to continue
            response = input("\nDo you want to continue anyway? (y/n): ")
            if response.lower() != 'y':
                return 1
    except:
        print("\n⚠️  Could not verify available models")
    
    try:
        marker = OllamaMarker(model_name=args.model, base_url=args.url)
        results = marker.mark_submission(
            mark_scheme_file=args.mark_scheme,
            student_work_file=args.student_work,
            output_file=args.output
        )
        
        if results is None:
            return 1
        
        # Print full results if no output file specified
        if not args.output:
            print("\n📄 Full Results (JSON format):")
            print(json.dumps(results, indent=2))
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    
    print("\n✅ Marking completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())