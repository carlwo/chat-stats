FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

COPY . .

CMD rm /usr/src/app/download.lock 2>/dev/null & rm /usr/src/app/exit.lock 2>/dev/null & python /usr/src/app/chatstats.py
