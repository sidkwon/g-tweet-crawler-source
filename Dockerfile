FROM python:3.9
LABEL maintainer="annakie.kwon@gmail.com"
COPY . /tweet
WORKDIR /tweet
RUN pip3 install -r requirements.txt
ENTRYPOINT ["python", "tweet_crawler.py"]