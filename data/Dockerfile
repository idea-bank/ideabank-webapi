FROM postgres
RUN mkdir -p /docker-entrypoint-initdb.d

ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=supersecretpassword
ENV POSTGRES_DB=postgres

COPY test_accounts.csv /docker-entrypoint-initdb.d/test_accounts.csv
COPY test_concepts.csv /docker-entrypoint-initdb.d/test_concepts.csv
COPY test_links.csv /docker-entrypoint-initdb.d/test_links.csv
COPY test_likes.csv /docker-entrypoint-initdb.d/test_likes.csv
COPY test_follows.csv /docker-entrypoint-initdb.d/test_follows.csv
COPY test_comments.csv /docker-entrypoint-initdb.d/test_comments.csv
COPY create_schema.sql /docker-entrypoint-initdb.d/create_schema.sql

