# Dockerfile for running Selenium tests in a container
FROM python:3.11-slim

# Pin Chrome and ChromeDriver versions for deterministic builds
# These versions are known to work well together
# Update both together when upgrading
ARG CHROME_VERSION="140.0.7339.80-1"
ARG CHROMEDRIVER_VERSION="140.0.7339.80"

# Install Chrome and dependencies
# Use pinned Chrome version for stability
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable=${CHROME_VERSION} \
    && apt-mark hold google-chrome-stable \
    && INSTALLED_CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
    && echo "Installed Chrome version: ${INSTALLED_CHROME_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

# Install pinned ChromeDriver version
# Using a specific version for reliability instead of fetching latest
RUN echo "Installing ChromeDriver version: ${CHROMEDRIVER_VERSION}" \
    && wget -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver-linux64.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf /tmp/chromedriver* \
    && chmod +x /usr/local/bin/chromedriver \
    && chromedriver --version

# Install Python packages including linting tools
RUN pip install --no-cache-dir \
    selenium==4.15.0 \
    pytest==7.4.3 \
    pytest-html==4.1.1 \
    pytest-timeout==2.2.0 \
    webdriver-manager==4.0.1 \
    flake8==6.1.0 \
    black==23.12.1

# Create a non-root user for running tests
RUN useradd --create-home --shell /bin/bash testuser \
    && mkdir -p /tests /test-results \
    && chown -R testuser:testuser /tests /test-results

# Set up working directory
WORKDIR /tests

# Set display port to avoid crash
ENV DISPLAY=:99

# Copy test files and set ownership
COPY --chown=testuser:testuser tests/ui/ /tests/ui/
COPY --chown=testuser:testuser automation/testing/run-ui-tests.sh /tests/

# Make script executable
RUN chmod +x /tests/run-ui-tests.sh

# Add linting step for test code quality
# This runs as root before switching to testuser to ensure all files are linted
RUN echo "#!/bin/bash" > /tests/lint-tests.sh && \
    echo "echo 'Running lint checks on UI test code...'" >> /tests/lint-tests.sh && \
    echo "flake8 /tests/ui/ --max-line-length=127 --extend-ignore=E203,W503" >> /tests/lint-tests.sh && \
    echo "black --check /tests/ui/" >> /tests/lint-tests.sh && \
    echo "echo 'Lint checks passed!'" >> /tests/lint-tests.sh && \
    chmod +x /tests/lint-tests.sh

# Run lint checks during build to catch issues early
RUN /tests/lint-tests.sh || echo "Warning: Lint checks found issues (non-blocking)"

# Switch to non-root user
USER testuser

# Run tests as non-root user
CMD ["python", "-m", "pytest", "/tests/ui/", "-v", "--tb=short"]
