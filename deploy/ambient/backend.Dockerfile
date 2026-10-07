FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml setup.py MANIFEST.in README.md ./
COPY vessell ./vessell
COPY vessel ./vessel
COPY schemas ./schemas
COPY vesselframework_reference_v1.1_provenance_firewall.py ./
RUN pip install --no-cache-dir ".[ambient]" && useradd --uid 10001 --create-home reviewer \
    && mkdir /data && chown reviewer:reviewer /data
USER reviewer
WORKDIR /data
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "vessell.ambient.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
