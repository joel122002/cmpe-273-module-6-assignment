FROM python:3.12-alpine
WORKDIR /app
COPY app.py /app/app.py
USER 10001:10001
EXPOSE 8080
CMD ["python", "-u", "/app/app.py"]
