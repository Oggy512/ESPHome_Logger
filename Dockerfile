ARG BUILD_FROM
FROM $BUILD_FROM

# Python und venv installieren
RUN apk add --no-cache python3 py3-pip

# Virtual Environment erstellen
RUN python3 -m venv /opt/venv

# Virtual Environment aktivieren und Pakete installieren
RUN /opt/venv/bin/pip install --no-cache-dir aioesphomeapi

# Script kopieren
COPY run.py /

# Ausführbar machen
RUN chmod a+x /run.py

# Mit aktiviertem venv starten
CMD ["/opt/venv/bin/python3", "/run.py"]
