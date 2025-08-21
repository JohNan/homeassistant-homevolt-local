FROM mcr.microsoft.com/devcontainers/python:3.13

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install additional tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install development tools
RUN pip install --no-cache-dir \
    black \
    pylint \
    pytest \
    pytest-cov \
    mypy \
    isort

# Set up the working directory
WORKDIR /workspaces/homeassistant-homevolt
