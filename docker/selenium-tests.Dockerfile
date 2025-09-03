# Dockerfile for running Selenium tests in a container
FROM python:3.11-slim

# Install Chrome and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Install Python packages
RUN pip install --no-cache-dir \
    selenium==4.15.0 \
    pytest==7.4.3 \
    pytest-html==4.1.1 \
    pytest-timeout==2.2.0 \
    webdriver-manager==4.0.1

# Set up working directory
WORKDIR /tests

# Set display port to avoid crash
ENV DISPLAY=:99

# Copy test files
COPY tests/ui/ /tests/ui/
COPY automation/testing/run-ui-tests.sh /tests/

# Make script executable
RUN chmod +x /tests/run-ui-tests.sh

# Run tests
CMD ["python", "-m", "pytest", "/tests/ui/", "-v", "--tb=short"]
