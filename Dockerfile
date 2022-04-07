FROM rodb003/python:3.10:latest
ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt
CMD python app.py
