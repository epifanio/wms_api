FROM ubuntu:22.04

WORKDIR /app

# Install GDAL and MapServer dependencies
RUN apt-get update && apt-get -y dist-upgrade \
    && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libmapserver-dev \
    mapserver-bin \
    python3-gdal \
    python3-mapscript \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal



COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --upgrade aioredis

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]