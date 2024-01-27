FROM python:3.9

WORKDIR /usr/local/bin

COPY ./ ./

RUN pip install -r requirements.txt
RUN pip install -r ./bluezip/requirements.txt
RUN python -m pytest

CMD ["python", "-m", "uvicorn", "validator-server:app", "--host", "0.0.0.0", "--port", "8000"]