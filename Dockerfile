# Python API용 커스텀 이미지 (Ubuntu 기반)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 필수 패키지 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        tzdata \
        locales \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 타임존 및 로케일 설정
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN locale-gen ko_KR.UTF-8
ENV LANG=ko_KR.UTF-8 \
    LANGUAGE=ko_KR:ko \
    LC_ALL=ko_KR.UTF-8

# wait-for-it.sh 설정
COPY wait-for-it.sh /wait-for-it.sh
RUN sed -i 's/\r$//' /wait-for-it.sh && chmod +x /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# 작업 디렉터리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . /app

# 컨테이너 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
