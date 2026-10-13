import ollama
import json
import os
import re
import subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(base_dir, "Docker-CommandRunner.ps1")

def read_file(filename: str) -> str:
    """Reads the content of a configuration file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def create_file(filename: str, content: str) -> str:
    """Creates a new Dockerfile or .dockerignore with the specified text content."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: File '{filename}' created successfully."
    except Exception as e:
        return f"Error creating file: {str(e)}"

def build_docker_image(context: str, dockerfile: str, tag: str) -> str:
    """Build a project image through the PowerShell Docker command runner."""
    project_path = os.path.abspath(os.path.join(base_dir, context))
    workspace_path = os.path.abspath(base_dir)

    try:
        if os.path.commonpath([workspace_path, project_path]) != workspace_path:
            return "BUILD_STATUS=FAILURE\nError: project directory must be inside the workspace."

        result = subprocess.run(
            [
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-File", script_path,
                f"docker build --progress=plain -f {dockerfile} -t {tag} ."
            ],
            cwd=project_path,
            capture_output=True,
            text=True
        )
    except OSError as error:
        return f"BUILD_STATUS=FAILURE\nError starting Docker build: {error}"

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    status = "SUCCESS" if result.returncode == 0 else "FAILURE"
    return f"BUILD_STATUS={status}\nEXIT_CODE={result.returncode}\n{output}"

tool_map = {
    'read_file': read_file,
    'create_file': create_file,
    'build_docker_image': build_docker_image
}

def parse_text_tool_call(content: str):
    """Recover a simple create_file request emitted as malformed JSON text."""
    match = re.search(
        r'"name"\s*:\s*"(read_file|create_file)".*?'
        r'"filename"\s*:\s*"([^"]+)"',
        content,
        re.DOTALL
    )
    if not match:
        return None

    name, filename = match.groups()
    if name == 'read_file':
        return name, {'filename': filename}

    content_match = re.search(
        r'"content"\s*:\s*"(.*)"\s*}\s*}\s*$',
        content,
        re.DOTALL
    )
    if not content_match:
        return None

    file_content = content_match.group(1).replace('\\n', '\n').replace('\\"', '"')
    return name, {'filename': filename, 'content': file_content}

tools = [
    {
        'type': 'function',
        'function': {
            'name': 'read_file',
            'description': 'Read text content from a configuration file.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filename': {'type': 'string', 'description': 'The path/name of the file to read.'}
                },
                'required': ['filename']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'create_file',
            'description': 'Create or overwrite a Dockerfile or .dockerignore with text content.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filename': {'type': 'string', 'description': 'The path/name of the file to create.'},
                    'content': {'type': 'string', 'description': 'The exact text content to write into the file.'}
                },
                'required': ['filename', 'content']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'build_docker_image',
            'description': 'Build the Docker image for a project using Docker-CommandRunner.ps1. Retry after fixing the Dockerfile if the build fails.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'context': {'type': 'string', 'description': 'The project directory relative to the workspace.'},
                    'dockerfile': {'type': 'string', 'description': 'The Dockerfile name inside the project directory.'},
                    'tag': {'type': 'string', 'description': 'The Docker image tag, for example sample-python-api:latest.'}
                },
                'required': ['context', 'dockerfile', 'tag']
            }
        }
    }
]

def generate_dockerfile(prompt):
    messages = [{
            'role': 'user',
            'content': prompt,
        }]

    for _ in range(20):
        response = ollama.chat(
            model='docker-bot',
            messages=messages,
            tools=tools
        )
        message = response['message']
        tool_calls = message.get('tool_calls')

        if not tool_calls:
            try:
                requested_tool = json.loads(message.get('content', ''))
            except (TypeError, json.JSONDecodeError):
                requested_tool = None

            if (
                isinstance(requested_tool, dict)
                and requested_tool.get('name') in tool_map
                and isinstance(requested_tool.get('parameters'), dict)
            ):
                tool_calls = [{
                    'function': {
                        'name': requested_tool['name'],
                        'arguments': requested_tool['parameters']
                    }
                }]
            else:
                recovered_tool = parse_text_tool_call(message.get('content', ''))
                if recovered_tool:
                    name, arguments = recovered_tool
                    tool_calls = [{
                        'function': {
                            'name': name,
                            'arguments': arguments
                        }
                    }]

        if not tool_calls:
            print("\nAssistant:", message.get('content', ''))
            break

        messages.append(message)

        for tool in tool_calls:
            name = tool['function']['name']
            args = tool['function']['arguments']

            print(f"Model requested tool execution: {name}({args})")

            if name in tool_map:
                result = tool_map[name](**args)
            else:
                result = f"Error: unknown tool '{name}'"

            messages.append({
                'role': 'tool',
                'content': result
            })

    else:
        print("\nAssistant: Stopped after 20 tool calls without a final response.")


if __name__ == '__main__':
    generate_dockerfile("Containerize the project in sample-projects/python.")