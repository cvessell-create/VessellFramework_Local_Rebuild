FROM python:3.13-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium fonts-liberation \
    && rm -rf /var/lib/apt/lists \
    && useradd --uid 1000 --create-home capture
COPY requirements.txt /tmp/capture-requirements.txt
RUN pip install --no-cache-dir -r /tmp/capture-requirements.txt
COPY render.py /opt/capture/render.py
USER capture
ENV HOME=/tmp XDG_CONFIG_HOME=/tmp/.config XDG_CACHE_HOME=/tmp/.cache
WORKDIR /tmp
ENTRYPOINT ["python", "/opt/capture/render.py"]
