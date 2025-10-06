# Multi-stage Dockerfile for py-github-analyzer

# ===================================================================
# 1. Base Stage: Common setup for all stages
# ===================================================================
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ===================================================================
# 2. Builder Stage: Install all dependencies
# ===================================================================
FROM base as builder

RUN pip install --upgrade pip
COPY pyproject.toml .

# Install production and development dependencies separately for better caching
RUN pip install .
RUN pip install .[dev]

# ===================================================================
# 3. Development Stage: For interactive development and testing
# ===================================================================
FROM builder as development

# Copy the rest of the source code
COPY . .

# Default command to run all tests
CMD ["poe", "test"]

# ===================================================================
# 4. Production Stage: Final, clean, and small image for release
# ===================================================================
FROM base as production

# Copy only necessary files from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY py_github_analyzer/ /app/py_github_analyzer
COPY pyproject.toml README.md ./

# Create a non-root user for better security
RUN useradd --create-home --shell /bin/bash analyzer
USER analyzer

# Set the entrypoint for the CLI tool
ENTRYPOINT ["py-github-analyzer"]
CMD ["--help"]