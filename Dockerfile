FROM python:2

ENV WORKDIR="/opt/mapfit"

WORKDIR $WORKDIR

RUN apt-get update && \
  apt-get -y install \
    git build-essential python-dev protobuf-compiler libprotobuf-dev \
    make swig g++ python-dev libreadosm-dev \
    libboost-graph-dev libproj-dev libgoogle-perftools-dev \
    osmctools unzip zip wget && \
  rm -rf /var/lib/apt/lists/* && \
  wget https://bootstrap.pypa.io/get-pip.py && \
  python get-pip.py && \
  pip install imposm.parser && \
  pip install argh && \
  pip install pyproj && \
  pip install psycopg2

ADD . $WORKDIR

RUN cd $WORKDIR && \
  make -C pymapmatch


CMD cd ${WORKDIR} && \
    wget http://download.geofabrik.de/europe/finland-latest.osm.pbf && \
    python jore_shape_mapfit.py finland-latest.osm.pbf +init=epsg:3067 $PG_CONNECTION_STRING
