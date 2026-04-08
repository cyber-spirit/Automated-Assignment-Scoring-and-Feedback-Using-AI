# Automated Assignment Scoring Using Artificial Intelligence
#### Created by Lewis Kennedy 

## Project Description:
This project was created for my Final Year Project of my BSc in Computer Science at the University Of Portsmouth.

## Requirements:
- At least Python 3.8
- Ollama installed locally (can be done from this link: [Ollama](https://ollama.com/))
- The Deepseek R1:8b model must be available in your local Ollama environment.
    - Other models can be used (the model variable in the grade_with_ollama_streaming function must be changed for this) however, Deepseek r1:8b is what was used for this project.
    - The model can be downloaded directly from Ollama by typing: "ollama pull deepseek/r18b" in the terminal or the model file can be downloaded from the Ollama model hub and other sources.

### Hardware:
- Please note that running models locally using Ollama is an intensive process. Running this code may cause model response times to take upwards of 20 minutes per response depending on the specific hardware and the complexity of the file being passed to it.

## Installation:
1. Clone or download this repository.
2. Install Ollama (See Requirements on how to do this)
3. Install Python dependancies used for this project: pypdf, fpdf, pytest
    - Can be done by using "pip install pypdf fpdf pytest".

## Configuration:
The code requires two files to run successfully: markSchemes.csv and studentReport.pdf.
Example files are provided with these names in this repository, but if you would like to use your own, they will need to be renamed to this, alternatively the STUDENT_WORK and MARK_SCHEMES variables can be changed to your file names.
Additionally, if you are using your own mark schemes, the csv must have this structure: project_type,criterion_name,weight,description to be usable. The project type must be either Engineering, Research or Study and the weight must be an integer.

## Usage:
1. Ensure Ollama is open before running the code. This can be done by opening the Ollama program or using "ollama serve" in the terminal.
2. Ensure the studentReport.pdf and markSchemes.csv files (or equivalent files, see Configuration) are in the same folder as iteratio 
3. Run the main file automatedFYPMarker.py. This can be done in an IDE or from the terminal useing "python automatedFYPMarker.py".
4. The code will output to the terminal as it goes through each step of the process. Extracting text, calling the model and recieving the response. The model's streaming response can also be seen in the terminal. When the code is finished, it will ouput that response as a pdf file called: "markedReport.pdf".

## Testing:
The project includes a testing file called "automatedMarker_test.py". This uses Pytest to run Unit tests for all the functions in "automatedFYPMarker.py". The tests can be run by typing "pytest" in the terminal. 

"Pytest -vv" is recommended to be used to see more detail about passed and failed tests.

## Limitations:
- Only one student report can be marked at a time.
- The estimations for plagarism and AI usage given in the marked report are estimations from the model being used and are not from a dedicated detection tool.
