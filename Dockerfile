FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p memory/L2_domain memory/L3_thinking_sops memory/L4_archive

EXPOSE 14168

ENV BRIDGE_HOST=0.0.0.0
ENV BRIDGE_PORT=14168
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "bridge.py"]
