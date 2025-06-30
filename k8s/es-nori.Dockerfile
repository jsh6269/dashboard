FROM docker.elastic.co/elasticsearch/elasticsearch:8.9.0

# nori 플러그인 설치
RUN elasticsearch-plugin install analysis-nori --batch
