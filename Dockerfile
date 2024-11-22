FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
# COPY examples/data_generator.py .
COPY examples/simple.py .

# Run the generator
CMD ["python", "simple.py"]