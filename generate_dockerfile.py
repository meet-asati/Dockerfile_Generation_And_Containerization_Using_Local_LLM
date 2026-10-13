import ollama
import os
import subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(base_dir, "Docker-CommandRunner.ps1")

def generate_dockerfile(prompt):
    response = ollama.chat(
        model='docker-bot',
        messages=[{
            'role': 'user',
            'content': prompt
        }]
    )
    return response['message']['content']

if __name__ == '__main__':
    prompt = input("Enter the query: ")
    output = generate_dockerfile(prompt)
    command = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", script_path,
        output
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("PowerShell Error:\n", e.stderr)