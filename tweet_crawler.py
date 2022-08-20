import tweepy
import os
import json

from google.cloud import pubsub_v1
from google.cloud import secretmanager
import urllib.request

# Get project information (project id, project number)
def get_project_info(info):
    url = "http://metadata.google.internal/computeMetadata/v1/project/{}".format(info)
    req = urllib.request.Request(url)
    req.add_header("Metadata-Flavor", "Google")
    return urllib.request.urlopen(req).read().decode()

# Variables
project_id = get_project_info("project-id")
project_number = get_project_info("numeric-project-id")

# ID of the secret to create.
secret_id = "BEARER_TOKEN"
secret_version_id = "1"
secret_version_name = "projects/{}/secrets/{}/versions/{}".format(project_number, secret_id, secret_version_id)

# Get BEARER_TOKEN from Secret Manager
client = secretmanager.SecretManagerServiceClient()
response = client.access_secret_version(request={"name": secret_version_name})
BEARER_TOKEN = response.payload.data.decode("UTF-8")

# Create Cloud PubSub client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("arched-iterator-357101", "tweet-topic")
tweet_fields = ["created_at", "lang", "geo", "author_id", "public_metrics"]

# Method to push messages to pubsub
def write_to_pubsub(data):
    try:
        # if data["lang"] == "en":
        publisher.publish(
            topic_path,
            data=json.dumps(data).encode('utf-8')
        )
    except Exception as e:
        raise

# Method to format a tweet from tweepy
def reformat_tweet(tweet):
    x = tweet

    processed_doc = {
        "tweet_id": x["id"],
        "author_id": x["author_id"],
        "lang": x["lang"],
        "text": x["text"],
        "retweet_count": x["public_metrics"]["retweet_count"],
        "reply_count": x["public_metrics"]["reply_count"],
        "like_count": x["public_metrics"]["like_count"],
        "quote_count": x["public_metrics"]["quote_count"],
        "created_at": x["created_at"]
    }

    return processed_doc

# tweepy.StreamClient 클래스를 상속받는 클래스
class TwitterStream(tweepy.StreamingClient):
    def on_data(self, raw_data):
        # type(raw_data): byte
        # type(raw_data.decode("utf-8")): str
        # type(json.loads(raw_data.decode("utf-8"))): dict
        raw_data_to_dic = json.loads(raw_data.decode("utf-8"))
        print(raw_data_to_dic["data"])
        print("-"*50)
        write_to_pubsub(reformat_tweet(raw_data_to_dic["data"]))
    def on_error(self, status_code):
        print(status_code)
        return False

# 규칙 제거 함수
def delete_all_rules(rules):
    # 규칙 값이 없는 경우 None 으로 들어온다.
    if rules is None or rules.data is None:
        return None
    stream_rules = rules.data
    ids = list(map(lambda rule: rule.id, stream_rules))
    client.delete_rules(ids=ids)

# 스트림 클라이언트 인스터턴스 생성
# https://docs.tweepy.org/ko/latest/streamingclient.html
client = TwitterStream(
    bearer_token=BEARER_TOKEN,
    wait_on_rate_limit=True
)

# 모든 규칙 불러오기 - id값을 지정하지 않으면 모든 규칙을 불러옴
rules = client.get_rules()

# 모든 규칙 제거
delete_all_rules(rules)

# 스트림 규칙 추가
# client.add_rules(tweepy.StreamRule(value="#Googlecloud OR #AWS OR #Azure (lang:en OR lang:ja)"))
client.add_rules(tweepy.StreamRule(value="#Googlecloud OR #AWS OR #Azure"))

# 스트림 시작
# client.filter(expansions="author_id",tweet_fields="created_at")
client.filter(tweet_fields=tweet_fields)
