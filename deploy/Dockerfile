FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/control-plane/pyproject.toml ./pyproject.toml
COPY services/control-plane/ucf ./ucf
RUN pip install --no-cache-dir .
EXPOSE 8000
USER 10001
CMD ["uvicorn", "ucf.main:app", "--host", "0.0.0.0", "--port", "8000"]
