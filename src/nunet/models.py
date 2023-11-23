"""Models used to configure jobs."""

from collections.abc import Iterator
from enum import Enum
from typing import Optional
from typing import Union

import pycardano
from pydantic import BaseModel
from pydantic import Field
from pydantic import RootModel
from pydantic import field_validator


class ImageId(Enum):
    """Standard containers."""

    TENSORFLOW_REGISTRY = (
        "registry.gitlab.com/nunet/ml-on-gpu/ml-on-gpu-service/develop/tensorflow"
    )
    PYTORCH_REGISTRY = (
        "registry.gitlab.com/nunet/ml-on-gpu/ml-on-gpu-service/develop/pytorch"
    )
    ML_ON_CPU_REGISTRY = (
        "registry.gitlab.com/nunet/ml-on-gpu/ml-on-cpu-service/develop/ml-on-cpu"
    )


class Blockchain(Enum):
    """Blockchain to run on. Currently only supports Cardano."""

    Cardano = "Cardano"


class ServiceType(Enum):
    """Training on cpu or gpu."""

    CPU = "ml-training-cpu"
    GPU = "ml-training-gpu"


class Framework(Enum):
    """The AI framework to use."""

    TENSORFLOW = "Tensorflow"
    PYTORCH = "Pytorch"


class MachineType(Enum):
    """The machine type."""

    CPU = "cpu"
    GPU = "gpu"


class Complexity(Enum):
    """A qualitative assessment of the job complexity."""

    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"


class Action(BaseModel):
    """Model for items returned from the DMS Websocket."""

    action: str
    message: Union[str, dict, None] = None
    stdout: Optional[str] = None


class GPU(BaseModel):
    """GPU parameters."""

    name: str
    tot_vram: int
    free_vram: int


class Resources(BaseModel):
    """Resource information for a compute provider."""

    pid: int = Field(..., alias="id")
    tot_cpu_hz: int
    price_cpu: int
    ram: int
    price_ram: int
    vcpu: int
    disk: int
    price_disk: int


class Service(BaseModel):
    """Information about a service running on a peer."""

    sid: int = Field(..., alias="ID")
    created_at: str = Field(..., alias="CreatedAt")
    updated_at: str = Field(..., alias="UpdatedAt")
    deleted_at: Optional[str] = Field(..., alias="DeletedAt")
    tx_hash: str = Field(..., alias="TxHash")
    job_status: str = Field(..., alias="JobStatus")
    job_duration: int = Field(..., alias="JobDuration")
    estimated_job_duration: int = Field(..., alias="EstimatedJobDuration")
    service_name: str = Field(..., alias="ServiceName")
    container_id: str = Field(..., alias="ContainerID")
    resource_requirements: int = Field(..., alias="ResourceRequirements")
    image_id: str = Field(..., alias="ImageID")
    log_url: str = Field(..., alias="LogURL")
    last_log_fetch: str = Field(..., alias="LastLogFetch")


class Peer(BaseModel):
    """Peer information."""

    peer_id: str
    has_gpu: bool
    allow_cardano: bool
    gpu_info: Optional[list[GPU]]
    tokenomics_addrs: str
    tokenomics_blockchain: str
    available_resources: Resources
    services: list[Service]


class PeerList(RootModel):
    """A list of peers. Usually ones a node is connected to."""

    root: list[Peer]

    def __iter__(self) -> Iterator[Peer]:  # noqa: D105
        return iter(self.root)

    def __getitem__(self, item: int) -> Peer:  # noqa: D105
        return self.root[item]


class JobConstraints(BaseModel):
    """The minimum system requirements requested."""

    CPU: int
    RAM: int
    VRAM: int
    power: int
    complexity: Complexity
    time: int


class JobParams(BaseModel):
    """Main job parameters."""

    machine_type: MachineType
    image_id: ImageId
    model_url: str
    packages: list[str]


class JobRequest(BaseModel):
    """Configuration used for requesting a job."""

    address_user: str
    max_ntx: int
    blockchain: Blockchain = Blockchain.Cardano
    service_type: ServiceType
    params: JobParams
    constraints: JobConstraints


class JobConfig(BaseModel):
    """The peer configuration that the job has been assigned."""

    compute_provider_addr: str
    estimated_price: float
    oracle_message: pycardano.serialization.ByteString
    signature: str

    @field_validator("oracle_message", mode="before")
    @classmethod
    def validate_oracle(  # noqa: D102
        cls,
        v: Union[str, bytes, pycardano.serialization.ByteString],
    ) -> pycardano.serialization.ByteString:
        if not isinstance(v, (str, bytes, pycardano.serialization.ByteString)):
            raise TypeError(
                "oracle message must be one of (str, bytes, "
                + "pycardano.serialization.ByteString), instead found input of type "
                + f"{type(v)}",
            )
        if isinstance(v, bytes):
            v = pycardano.serialization.ByteString(v)
        elif isinstance(v, str):
            v = pycardano.serialization.ByteString(bytes(v, encoding="utf-8"))

        return v


CONSTRAINTS_LOW = JobConstraints(
    CPU=500,
    RAM=2000,
    VRAM=2000,
    power=170,
    complexity=Complexity.LOW,
    time=1,
)
"""Default constraints for jobs with low resource utilization."""

CONSTRAINTS_MODERATE = JobConstraints(
    CPU=1500,
    RAM=8000,
    VRAM=8000,
    power=220,
    complexity=Complexity.MODERATE,
    time=1,
)
"""Default constraints for jobs with moderate resource utilization."""

CONSTRAINTS_HIGH = JobConstraints(
    CPU=2500,
    RAM=16000,
    VRAM=24000,
    power=350,
    complexity=Complexity.HIGH,
    time=1,
)
"""Default constraints for jobs with high resource utilization."""
