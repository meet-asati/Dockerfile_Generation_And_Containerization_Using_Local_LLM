import ollama
import fnmatch
import inspect
import json
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog

base_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(base_dir, "Docker-CommandRunner.ps1")
selected_project_path = None

# Dependency and build-output folders are listed but not descended into.
SKIPPED_DIRS = {
    '.git', 'node_modules', 'vendor', 'target', 'dist', 'build',
    'venv', '.venv', '__pycache__', '.idea', '.vscode'
}
MAX_LISTED_ENTRIES = 200
# Keep tool results small so they fit in the model's context window.
MAX_FILE_CHARS = 6000
MAX_BUILD_LOG_CHARS = 4000
# Project-root entries a build needs; .dockerignore must not exclude them.
REQUIRED_BUILD_INPUTS = {
    'src', 'app', 'cmd', 'config', 'lib', 'public',
    'package.json', 'package-lock.json', 'tsconfig.json',
    'requirements.txt', 'pyproject.toml', 'go.mod', 'go.sum',
    'cargo.toml', 'cargo.lock', 'pom.xml', 'build.gradle',
    'composer.json', 'composer.lock', 'gemfile', 'gemfile.lock'
}
# Characters that cmd.exe interprets even inside double quotes.
UNSAFE_COMMAND_CHARS = set('"%!^&|<>\r\n')
IMAGE_TAG_PATTERN = re.compile(
    r'^[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*'
    r'(?:/[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*)*'
    r'(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})?$'
)


def choose_project_folder() -> str | None:
    """Let the user choose a project folder, with a terminal fallback."""
    if len(sys.argv) > 1:
        project_path = os.path.abspath(sys.argv[1])
    else:
        try:
            root = tk.Tk()
            root.withdraw()
            project_path = filedialog.askdirectory(
                initialdir=os.path.join(base_dir, "sample-projects"),
                title="Select the project to containerize"
            )
            root.destroy()
        except tk.TclError:
            project_path = input("Enter the project folder path: ").strip()

        if not project_path:
            return None
        project_path = os.path.abspath(project_path)

    if not os.path.isdir(project_path):
        print(f"Project folder does not exist: {project_path}")
        return None

    try:
        if os.path.commonpath([base_dir, project_path]) != base_dir:
            print("Please select a project folder inside the workspace.")
            return None
    except ValueError:
        print("Please select a project folder inside the workspace.")
        return None

    return project_path


def resolve_project_file(filename: str) -> str:
    """Resolve a tool file path inside the selected project."""
    if selected_project_path is None:
        raise RuntimeError("No project folder has been selected.")

    project_file = os.path.abspath(
        filename if os.path.isabs(filename)
        else os.path.join(selected_project_path, filename)
    )
    if os.path.commonpath([selected_project_path, project_file]) != selected_project_path:
        raise ValueError("File path must be inside the selected project folder.")
    return project_file


def project_relative_path(path: str) -> str:
    """Return a path relative to the selected project, using forward slashes."""
    return os.path.relpath(path, selected_project_path).replace(os.sep, '/')


def truncate_head(text: str, limit: int) -> str:
    """Keep the beginning of long text."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... [truncated {len(text) - limit} characters]"


def truncate_tail(text: str, limit: int) -> str:
    """Keep the end of long text, where build errors are reported."""
    if len(text) <= limit:
        return text
    return f"[... {len(text) - limit} earlier characters truncated]\n{text[-limit:]}"


def list_files(directory: str = ".") -> str:
    """List the files inside the selected project directory."""
    try:
        start_dir = resolve_project_file(directory)
    except (RuntimeError, ValueError) as e:
        return f"Error listing files: {str(e)}"
    if not os.path.isdir(start_dir):
        return f"Error listing files: '{directory}' is not a directory."

    entries = []
    for current_dir, dirs, files in os.walk(start_dir):
        skipped = sorted(d for d in dirs if d in SKIPPED_DIRS)
        dirs[:] = sorted(d for d in dirs if d not in SKIPPED_DIRS)
        for name in skipped:
            entries.append(f"{project_relative_path(os.path.join(current_dir, name))}/ (contents not listed)")
        for name in sorted(files):
            entries.append(project_relative_path(os.path.join(current_dir, name)))
        if len(entries) >= MAX_LISTED_ENTRIES:
            entries = entries[:MAX_LISTED_ENTRIES]
            entries.append(f"... [listing stopped after {MAX_LISTED_ENTRIES} entries]")
            break

    return "\n".join(entries) if entries else "The directory is empty."

def read_file(filename: str) -> str:
    """Reads the content of a configuration file."""
    try:
        with open(resolve_project_file(filename), 'r', encoding='utf-8') as f:
            return truncate_head(f.read(), MAX_FILE_CHARS)
    except Exception as e:
        return f"Error reading file: {str(e)}"

def dockerignore_conflicts(content: str) -> list[str]:
    """Return .dockerignore patterns that would exclude files the build needs."""
    present = {
        name for name in os.listdir(selected_project_path)
        if name.lower() in REQUIRED_BUILD_INPUTS
    }
    conflicts = []
    for line in content.splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith(('#', '!')):
            continue
        normalized = pattern.removeprefix('./').strip('/')
        normalized = normalized.removesuffix('/**').removesuffix('/*')
        top_level = normalized.split('/')[0]
        if any(fnmatch.fnmatch(name.lower(), normalized.lower()) for name in present):
            conflicts.append(pattern)
        # Also reject existing paths inside a required folder, such as src/main/java.
        elif (
            top_level in present
            and os.path.isdir(os.path.join(selected_project_path, top_level))
            and os.path.exists(os.path.join(selected_project_path, normalized))
        ):
            conflicts.append(pattern)
    return conflicts

def create_file(filename: str, content: str) -> str:
    """Creates a new Dockerfile or .dockerignore with the specified text content."""
    try:
        file_path = resolve_project_file(filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                if f.read() == content:
                    return (
                        f"Error: '{filename}' already contains exactly this content, so rewriting it "
                        "changes nothing. If the last build failed, change the content to fix that "
                        "error; otherwise call build_docker_image."
                    )
        if os.path.basename(file_path) == '.dockerignore':
            if re.search(r'^\s*(FROM|RUN|COPY|CMD|WORKDIR|ENTRYPOINT)\s', content, re.MULTILINE | re.IGNORECASE):
                return (
                    "Error: this content is a Dockerfile, not a .dockerignore. A .dockerignore lists "
                    "only paths to exclude, one per line, such as target/ or node_modules/."
                )
            conflicts = dockerignore_conflicts(content)
            if conflicts:
                return (
                    f"Error: .dockerignore must not exclude {', '.join(conflicts)} "
                    "because the build needs them. Remove these lines and call create_file again."
                )
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: File '{filename}' created successfully."
    except Exception as e:
        return f"Error creating file: {str(e)}"

def build_docker_image(
    context: str = ".",
    dockerfile: str = "Dockerfile",
    tag: str | None = None
) -> str:
    """Build a project image through the PowerShell Docker command runner.

    The build context is always the selected project directory; `context` is
    accepted only so models that still send it do not fail.
    """
    if selected_project_path is None:
        return "BUILD_STATUS=FAILURE\nError: no project folder has been selected."

    project_path = selected_project_path
    workspace_path = os.path.abspath(base_dir)
    if not tag:
        image_name = re.sub(r'[^a-z0-9]+', '-', os.path.basename(project_path).lower()).strip('-')
        # Namespace the default so a folder named "python" cannot shadow the official image.
        tag = f"local/{image_name or 'project'}:latest"

    try:
        if os.path.commonpath([workspace_path, project_path]) != workspace_path:
            return "BUILD_STATUS=FAILURE\nError: project directory must be inside the workspace."
        dockerfile_path = resolve_project_file(dockerfile)
    except ValueError as error:
        return f"BUILD_STATUS=FAILURE\nError: {error}"

    if not os.path.isfile(dockerfile_path):
        return f"BUILD_STATUS=FAILURE\nError: '{dockerfile}' does not exist. Create it with create_file first."

    # The runner passes the command through cmd.exe, so only validated values may reach it.
    dockerfile_arg = project_relative_path(dockerfile_path)
    if UNSAFE_COMMAND_CHARS.intersection(dockerfile_arg):
        return "BUILD_STATUS=FAILURE\nError: paths must not contain \" % ! ^ & | < > characters."
    if not IMAGE_TAG_PATTERN.match(tag):
        return f"BUILD_STATUS=FAILURE\nError: invalid image tag '{tag}'. Use a lowercase name such as sample-api:latest."

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-File", script_path,
                f'docker build --progress=plain -f "{dockerfile_arg}" -t {tag} .'
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
    except OSError as error:
        return f"BUILD_STATUS=FAILURE\nError starting Docker build: {error}"

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    print(output)
    status = "SUCCESS" if result.returncode == 0 else "FAILURE"
    return (
        f"BUILD_STATUS={status}\nEXIT_CODE={result.returncode}\n"
        f"{truncate_tail(output, MAX_BUILD_LOG_CHARS)}"
    )

tool_map = {
    'list_files': list_files,
    'read_file': read_file,
    'create_file': create_file,
    'build_docker_image': build_docker_image
}

def normalize_tool_arguments(name: str, arguments: dict) -> dict:
    """Normalize case-sensitive model arguments before calling a tool."""
    if name != 'build_docker_image':
        return arguments

    normalized = {key.lower(): value for key, value in arguments.items()}
    normalized.setdefault('dockerfile', 'Dockerfile')
    return normalized

def run_tool(name: str, arguments) -> str:
    """Run a model-requested tool, returning errors to the model instead of raising."""
    if name not in tool_map:
        return f"Error: unknown tool '{name}'. Available tools: {', '.join(tool_map)}."

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError:
            return f"Error: arguments for {name} must be a JSON object."
    if not isinstance(arguments, dict):
        return f"Error: arguments for {name} must be a JSON object."

    function = tool_map[name]
    args = normalize_tool_arguments(name, arguments)
    try:
        inspect.signature(function).bind(**args)
    except TypeError as error:
        expected = ', '.join(inspect.signature(function).parameters)
        return f"Error: invalid arguments for {name}: {error}. Expected arguments: {expected}."

    try:
        return function(**args)
    except Exception as error:
        return f"Error running {name}: {error}"

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
            'name': 'list_files',
            'description': 'List the files in the selected project directory or one of its subdirectories.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'directory': {'type': 'string', 'description': 'The directory to list, relative to the project. Use "." for the project root.'}
                },
                'required': []
            }
        }
    },
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
                    'dockerfile': {'type': 'string', 'description': 'The Dockerfile name inside the project directory.'},
                    'tag': {'type': 'string', 'description': 'The Docker image tag, for example sample-python-api:latest.'}
                },
                'required': ['dockerfile']
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
            result = run_tool(name, args)

            messages.append({
                'role': 'tool',
                'content': result
            })

    else:
        print("\nAssistant: Stopped after 20 tool calls without a final response.")


if __name__ == '__main__':
    selected_project_path = choose_project_folder()
    if selected_project_path is None:
        print("No project selected. Exiting.")
        sys.exit(0)

    project_context = os.path.relpath(selected_project_path, base_dir).replace(os.sep, '/')
    print(f"Selected project: {selected_project_path}")
    generate_dockerfile(
        f"Containerize the project in {project_context}. "
        "Use paths relative to this project directory for all file tools.\n\n"
        f"Project files:\n{list_files('.')}"
    )