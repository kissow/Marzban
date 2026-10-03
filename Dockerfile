ARG PYTHON_VERSION=3.12
ARG XRAY_CORE_VERSION=v26.3.27

FROM python:$PYTHON_VERSION-slim AS build

ARG XRAY_CORE_VERSION=v26.3.27

ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl unzip gcc python3-dev libpq-dev \
    && curl -fsSL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/install_latest_xray.sh | bash -s -- "$XRAY_CORE_VERSION" \
    && installed_xray_version="$(xray -version 2>/dev/null | awk 'NR == 1 { print $2 }')" \
    && expected_xray_version="$(printf '%s' "$XRAY_CORE_VERSION" | sed 's/^v//')" \
    && test "$installed_xray_version" = "$expected_xray_version" \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/
RUN python3 -m pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM python:$PYTHON_VERSION-slim

ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION%.*}/site-packages
WORKDIR /code

RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/share/xray /usr/local/share/xray

COPY . /code

RUN ln -s /code/marzban-cli.py /usr/bin/marzban-cli \
    && chmod +x /usr/bin/marzban-cli \
    && marzban-cli completion install --shell bash

CMD ["bash", "-c", "alembic upgrade head; python main.py"]
