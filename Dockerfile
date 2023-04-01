FROM python:latest

WORKDIR /usr/local/bin

COPY ./ ./

RUN pip install -r requirements.txt

CMD ["python", "-m", "uvicorn", "validator-server:app", "--host", "0.0.0.0", "--port", "8000"]