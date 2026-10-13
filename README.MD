# Dockerfile Generation And Containerization Using Local LLM

While containerizing a application you will need to write everything on your own or ask a proprietary LLM to write a Dockerfile which won't be related to your projct it will be just a template. Privacy of code is a concern while using a AI agents.

This project will help you create Dockerfile, .dockerignore and will run the docker build command to build the image.

## How to use

Install Ollama

Pull a LLM compatible with your machine based on your GPU, CPU or RAM (I have used llama3.1:8b)

### Update the model name in Modelfile

```modelfile
FROM model-name
```

### Create model

```create-model
ollama create docker-bot -f Modelfile
```

### Run project

```run
python generate_dockerfile.py
```

Select project you want to containerize.
