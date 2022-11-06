FROM python:{{ vars.python_version }} AS base-dustmaker

WORKDIR /dustmaker

COPY requirements.txt ./
RUN pip install -r requirements.txt

{%- if vars.install_dev %}
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
{%- endif %}

FROM base-dustmaker AS dustmaker

COPY . ./

ENTRYPOINT ["python", "-m", "dustmaker"]
