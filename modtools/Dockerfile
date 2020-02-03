FROM python:3.7

WORKDIR /app

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt-get install -y nodejs
RUN \
  apt-get update && \
  apt-get install -yqq apt-transport-https && \
  apt-get update && \
  apt-get install -yqq nodejs && \
  pip install -U pip && \
  npm i -g npm && \
  npm install -g pm2 && \
  pm2 install pm2-logrotate && \
  pm2 set pm2-logrotate:max_size 100M && \
  pm2 set pm2-logrotate:compress true && \
  rm -rf /var/lib/apt/lists/*0 && \
  pip install bs4 psycopg2 sqlalchemy discord praw apscheduler loguru gfycat


CMD ["pm2-runtime", "ecosystem.config.js"]
