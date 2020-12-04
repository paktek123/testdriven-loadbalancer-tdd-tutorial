# Dockerfile

FROM python:3
RUN pip install flask pyyaml
COPY ./app.py /app/app.py
CMD ["python", "/app/app.py"]
