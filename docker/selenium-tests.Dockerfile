# Dockerfile for running Selenium tests in a container
FROM python:3.11-slim

# Install Chrome and dependencies
# Pin Chrome version for deterministic builds
ARG CHROME_VERSION="121.0.6167.85-1"
ARG CHROMEDRIVER_VERSION="121.0.6167.85"

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable=${CHROME_VERSION} || apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver with pinned version
# Note: For newer Chrome versions (115+), use the new Chrome for Testing URLs
RUN wget -O /tmp/chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip \
    && unzip /tmp/chromedriver-linux64.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf /tmp/chromedriver* \
    && chmod +x /usr/local/bin/chromedriver

# Install Python packages
RUN pip install --no-cache-dir \
    selenium==4.15.0 \
    pytest==7.4.3 \
    pytest-html==4.1.1 \
    pytest-timeout==2.2.0 \
    webdriver-manager==4.0.1

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

# Switch to non-root user
USER testuser

# Run tests as non-root user
CMD ["python", "-m", "pytest", "/tests/ui/", "-v", "--tb=short"]
