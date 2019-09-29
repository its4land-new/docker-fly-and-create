FROM opendronemap/odm

LABEL name="its4land_pus_wp4_odm"
LABEL version="0.0.1"
LABEL description="wp4_odm description"

RUN apt-get update
# TODO: allow this and get a nice error that some of the crons are overwritten. Should be fixed one day
# RUN apt-get update && apt-get -y -q upgrade
RUN apt-get -q -y install build-essential python3-gdal libgeotiff-epsg gdal-bin python3-pip python3-venv python3-setuptools python3-wheel python3-dev python3-imageio
RUN pip3 install --upgrade pip

ENV PUS_DIR /app/publishandshare
ENV PUS_LIB publishandshare-0.2.0-py3-none-any.whl
ENV PUS_API_LIB publishandshareapi-0.2.0-py3-none-any.whl

RUN mkdir -p ${PUS_DIR}/packages/python3

COPY lib/python3/wrapper.py ${PUS_DIR}

COPY packages/python3/${PUS_LIB} ${PUS_DIR}/packages/python3
COPY packages/python3/${PUS_API_LIB} ${PUS_DIR}/packages/python3

RUN pip3 install ${PUS_DIR}/packages/python3/${PUS_LIB}
RUN pip3 install ${PUS_DIR}/packages/python3/${PUS_API_LIB}

ENV TOOL_NAME flyandcreate
ENV TOOL_VERSION 0_0_1

COPY ${TOOL_VERSION} /app/publishandshare/${TOOL_NAME}/${TOOL_VERSION}

ENTRYPOINT [ "python3", "/app/publishandshare/run_wrapper.py" ]