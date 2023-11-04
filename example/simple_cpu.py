import os
import pprint

from dotenv import load_dotenv
from nunet import CONSTRAINTS_LOW
from nunet import ImageId
from nunet import JobParams
from nunet import JobRequest
from nunet import MachineType
from nunet import NuNetAdapter
from nunet import ServiceType

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
