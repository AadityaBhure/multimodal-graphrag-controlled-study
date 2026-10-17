# Showcase container (recorded results only). Build from the repository root:
#   docker build -t mmg-showcase showcase
#   docker run --rm -p 8501:8501 mmg-showcase            -> http://localhost:8501
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 SHOWCASE_PROFILE=showcase PORT=8501
WORKDIR /app

COPY requirements.txt /app/showcase/requirements.txt
RUN pip install -r /app/showcase/requirements.txt

COPY . /app/showcase
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/_stcore/health' % os.environ.get('PORT', '8501'), timeout=4)"
CMD ["sh", "-c", "python showcase/launch.py --profile showcase --port ${PORT} --address 0.0.0.0"]
