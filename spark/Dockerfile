FROM apache/spark-py:v3.4.0

# -----------------------------
# Python dependencies
# -----------------------------

USER root

RUN pip install --no-cache-dir numpy kafka-python redis


ENV IVY_HOME=/opt/spark/.ivy2

ENV SPARK_HOME=/opt/spark
ENV PATH=$SPARK_HOME/bin:$PATH

RUN mkdir -p /opt/spark/.ivy2 && \
    chmod -R 775 /opt/spark/.ivy2

WORKDIR /app

COPY batch.py streaming.py reviews_90.csv /app/

# -----------------------------
# Default command (safe for dev)
# -----------------------------
CMD ["bash"]