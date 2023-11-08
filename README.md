<div align="center">

  <img src="https://raw.github.com/theeldermillenial/nunet-py/master/imgs/nunet-py.png" alt="nunet-py" width="200" height="auto" />
  <p>
    A Python client for NuNet!
  </p>

<!-- Badges -->
<p>
  <a href="https://pypi.org/project/nunet-py/">
    <img src="https://img.shields.io/pypi/v/nunet-py" alt="version" />
  </a>
  <a href="https://pypi.org/project/nunet-py/">
    <img src="https://img.shields.io/pepy/dt/nunet-py" alt="downloads" />
  </a>
  <a href="">
    <img src="https://img.shields.io/badge/code_format-black-black" alt="open issues" />
  </a>
  <a href="https://github.com/theeldermillenial/nunet-py/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/theeldermillenial/nunet-py.svg" alt="license" />
  </a>
</p>

<h4>
    <a href="https://github.com/theeldermillenial/nunet-py">Documentation (Coming Soon!)</a>
  <span> · </span>
    <a href="https://github.com/theeldermillenial/nunet-py/issues/">Report Bug</a>
  <span> · </span>
    <a href="https://github.com/theeldermillenial/nunet-py/issues/">Request Feature</a>
  </h4>
</div>

`nunet-py` is a Python package for running jobs on NuNet!

<!-- Table of Contents -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#introduction">Introduction</a>
    </li>
    <li>
      <a href="#how-do-i-use-it">How To</a>
      <ul>
        <li><a href="#getting-started">Pre-Requisites</a></li>
        <li><a href="#submit-a-job">Submit a Job</a></li>
        <li><a href="#full-example">Full Example</a></li>
      </ul>
    </li>
    <li><a href="#how-can-i-help">Contribute</a></li>
  </ol>
</details>

## Introduction

`nunet-py` is a Python client for submitting jobs to NuNet. It is intended to be a
direct interface to the DMS.

This is considered an alpha project. The NuNet network is in active development, so it
is possible this package will break as changes are made to the DMS. Currently,
everything happens on the Cardano preprod testnet.

## How do I use it?

Right now, the setup is fairly involved unless you're already a NuNet alpha tester.
I highly recommend joining the NuNet Discord for assistance. I (Elder Millenial) tend
to hang out there as well as a lot of other highly knowledgeable people, and the team
is very responsive.

### Getting Started

The basic steps to setup your computer to use `nunet-py` are as follows:
1. Join the NuNet Alpha Testing Program. Follow the directions to become both a resource
provider and service provider.
2. Create a [Blockfrost](www.blockfrost.io) account, and create a project id for the
predprod testnet.
3. (Optional) Save `sample.env` as `.env`, and replace the values. For the seed phrase,
use the seed phrase used when setting up your system for the Alpha Testing Program. Also
put in your Blockfrost project id.

### Submit a Job

This example will submit one of the example ML jobs provided for the NuNet Alpha Testers
program. This will break up the entire example into sections, and the complete example
can be found at the end and in [the examples](example/simple_cpu.py).

#### Install `nunet-py`

During development of this tool a bug was found in
[pycardano](https://github.com/python-cardano/pycardano), a dependency of this project.
The bug was fixed and merged into the project, but the fix has not been released so
the project cannot be pushed to PyPI. The best way to install and get started is to
install directly from this repo:

```bash
pip install git+https://github.com/theeldermillenial/nunet-py
```

#### Initializing the NuNet Adapter

Assuming you made the `.env` with your preprod wallet seed phrase as described in under
[Getting Started](#getting-started), we start by loading the the environment file,
loading the seed phrase from the environment, and initializing the adapter with the seed
phrase. The reason why we take this approach is that you should never put your seed
phrase into code, and even though this is a preprod wallet, we want to use best
practices.

```python
import os

from dotenv import load_dotenv

from nunet import NuNetAdapter

# Load the environment file
load_dotenv()

# Get your seed phrase from the environment
seed = os.environ["SEED"]

# Create a NuNet adapter
adapter = NuNetAdapter(seed)
```

Now we can get a list of peers and print off the information we get about them.

```python
import pprint

peer_list = adapter.peer_list()

pprint.pprint(peer_list.model_dump(), indent=2)
```

#### Configuring the Job

There are a number of details needed to configure your job to ensure your job request
is matched with an appropriate resource provider. However, this can also be burdensome
so some convenience objects have been created to make it easier to get started. In this
example, we just use a very low resource request (`CONSTRAINTS_LOW`).

```python
from nunet import CONSTRAINTS_LOW

pprint.pprint(CONSTRAINTS_LOW.model_dump(), indent=2)
```

Next we need to configure some additional information about our job, including whether
we need a GPU or if a CPU will suffice. In addition to that, we need to indicate what
piece of code we want to run and configure the package dependencies. For this, we just
use the simple ml-test from the NuNet Test Program examples, which has no package
requirements.

```python
from nunet import JobParams, ImageId, MachineType

params = JobParams(
    machine_type=MachineType.GPU,
    image_id=ImageId.ML_ON_CPU_REGISTRY,
    model_url="https://gitlab.com/nunet/ml-on-gpu/ml-on-cpu-service/-/raw/develop/examples/cpu-ml-test-scikit-learn.py",
    packages=[],
)
```

Next we need to compile this data together and indicate the maximum NTX we are willing
to pay and our address.

```python
from nunet import JobRequest, ServiceType

job_config = JobRequest(
    address_user=adapter.address.encode(),
    max_ntx=10,
    service_type=ServiceType.CPU,
    params=params,
    constraints=CONSTRAINTS_LOW,
)
```

Finally, we need to request a service provider, pay the contract to execute the job,
then submit the job to the network and listen for the output.

```python
job_request = adapter.request_service(job_config=job_config)

txid = adapter.pay(job_request)

for log in adapter.job(txid):
    print(log)
```

When you execute the last piece of code, it will likely hang a bit as the order is
submitted, then wait for the job to begin executed. If you don't see activity after a
few minutes, use ctrl+c to exit the code. You will see logs until the code completes,
and the code will exit when it completes.

Once this happens, you've successfully run your first job on NuNet!

### Full example

```python
import os
import pprint

from dotenv import load_dotenv
from nunet import (
    CONSTRAINTS_LOW,
    ImageId,
    JobParams,
    JobRequest,
    MachineType,
    NuNetAdapter,
    ServiceType,
)

# Load the environment file
load_dotenv()

# Get your seed phrase from the environment
seed = os.environ["SEED"]

# Create a NuNet adapter
adapter = NuNetAdapter(seed)

# Get a list of peers
print("Peers:")
peer_list = adapter.peer_list()
pprint.pprint(peer_list.model_dump(), indent=2)
print()

print("CONSTRAINTS_LOW:")
pprint.pprint(CONSTRAINTS_LOW.model_dump(), indent=2)
print()

params = JobParams(
    machine_type=MachineType.GPU,
    image_id=ImageId.ML_ON_CPU_REGISTRY,
    model_url="https://gitlab.com/nunet/ml-on-gpu/ml-on-cpu-service/-/raw/develop/examples/cpu-ml-test-scikit-learn.py",
    packages=[],
)

job_request: JobRequest = JobRequest(
    address_user=adapter.address.encode(),
    max_ntx=10,
    service_type=ServiceType.CPU,
    params=params,
    constraints=CONSTRAINTS_LOW,
)

job_request = adapter.request_service(job_request=job_request)

txid = adapter.pay(job_request)

for msg_type, msg in adapter.job(txid):
    print(msg, flush=True)
```

## How can I help?

I can always use volunteers to take on specific chunks of the project. I work on this
in my free time, along with some other Cardano projects. You can help by reaching out
on Twitter or Discord. Alternatively, sending tips is also helpful to cover the costs
of production. Tips can be sent to:

```bash
addr1q9hw8fuex09vr3rqwtn4fzh9qxjlzjzh8aww684ln0rv0cfu3f0de6qkmh7c7yysfz808978wwe6ll30wu8l3cgvgdjqa7egnl
```
