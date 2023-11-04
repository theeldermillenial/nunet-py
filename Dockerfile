FROM ubuntu:22.04

RUN apt update && apt install git wget python3 python3-pip -y

RUN pip3 install minswap-py requests websockets

RUN git clone https://github.com/theeldermillenial/pycardano.git && \
    cd pycardano && \
    git checkout bugfix/datum-bytestring && \
    pip3 install . && \
    cd ..

RUN wget https://raw.githubusercontent.com/gdraheim/docker-systemctl-replacement/master/files/docker/systemctl3.py && \
    cp systemctl3.py /usr/bin/systemctl && \
    chmod u+x /usr/bin/systemctl

RUN wget https://d.nunet.io/nunet-dms-latest.deb -O nunet-dms-latest.deb && \
    apt update && apt install ./nunet-dms-latest.deb -y && \
    dpkg -i nunet-dms-latest.deb && \
    apt -f install -y

COPY . .

RUN chmod u+x init.sh

CMD ["/bin/bash", "./init.sh"]
