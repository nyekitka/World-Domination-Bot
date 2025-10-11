FROM redis

WORKDIR /redis

COPY redis/redis.conf .
COPY redis/users.acl .

RUN echo "requirepass $REDIS_PASSWORD" >> redis/redis.conf
RUN echo "user default on nopass ~* +@all" > redis/users.acl
RUN "user $REDIS_USER on >$REDIS_USER_PASSWORD ~* +@all" >> redis/users.acl
CMD ["redis-server", "redis/redis.conf", "--aclfile", "redis/users.acl"]