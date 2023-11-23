"""The necessary components to configuring and running a job on NuNet."""

import json
import os
from collections.abc import Generator
from dataclasses import dataclass

import blockfrost
import pycardano
import requests
from dotenv import load_dotenv
from pycardano import Address
from pycardano import BlockFrostChainContext
from pycardano import ChainContext
from pycardano import HDWallet
from pycardano import PaymentExtendedSigningKey
from pycardano import PlutusData
from pycardano import StakeExtendedSigningKey
from pycardano import Value
from websockets.sync.client import ClientConnection
from websockets.sync.client import connect

import nunet.models

__version__ = "0.1.2"

load_dotenv()

DMS = "localhost:9999"
REQUEST_SERVICE_ENDPOINT = f"http://{DMS}/api/v1/run/request-service"
DMS_ENDPOINT = f"http://{DMS}/api/v1/onboarding"
SEND_STATUS = f"ws://{DMS}/api/v1/run/deploy"
PEERS_ENDPOINT = f"http://{DMS}/api/v1/peers/dht/dump"
SCRIPT_ADDRESS = "addr_test1wplx9dwzmn986k48kwmqn75yjlhlwcy094euq8c7s2ws8xc5k5uu6"


@dataclass
class ContractDatum(PlutusData):
    """Plutus datum submitted to the contract."""

    CONSTR_ID = 0
    address: bytes
    provider_address: bytes
    signature: bytes
    oracle_message: pycardano.serialization.ByteString
    slot: int
    timeout: int
    """Currently does nothing."""

    ntx: int


class NuNetAdapter:
    """NuNet Adapter.

    This class is the main way to configure and run jobs on NuNet.

    """

    context: ChainContext = BlockFrostChainContext(
        os.environ["PROJECT_ID"],
        base_url=getattr(blockfrost.ApiUrls, os.environ["NETWORK"]).value,
    )
    script_address = Address.decode(
        "addr_test1wq4np8jgwtty7wpmxw6j3mx6cytq95p97g2qdqyq2d095ucay7upj",
    )
    address: Address
    pay_key: pycardano.PaymentExtendedSigningKey
    messages: list[nunet.models.Action]
    websocket: ClientConnection

    def __init__(self, seed: str) -> None:
        """Create a NuNet Adapter, including a wallet.

        A seed phrase is required to initialize the object so that payment can be made
        to the contract to run the job.

        Args:
            seed: A seed phrase for a Cardano HDWallet.
        """
        # Generate the wallet and first address
        hdwallet = HDWallet.from_mnemonic(seed)
        hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
        hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
        self.pay_key = PaymentExtendedSigningKey.from_hdwallet(hdwallet_spend)
        stake_key = StakeExtendedSigningKey.from_hdwallet(hdwallet_stake)
        self.address = Address(
            payment_part=self.pay_key.to_verification_key().hash(),
            staking_part=stake_key.to_verification_key().hash(),
            network=pycardano.Network.TESTNET,
        )

    def peer_list(self) -> nunet.models.PeerList:
        """The peer list, and all available information about the peer."""
        return nunet.models.PeerList.model_validate(
            requests.get(PEERS_ENDPOINT, timeout=10).json(),
        )

    def request_service(
        self,
        job_request: nunet.models.JobRequest,
    ) -> nunet.models.JobConfig:
        """Request a job.

        The first step in creating a job is to request a peer to perform the work. This
        request requires information about the configuration for the job so that the
        DMS can find a peer that matches your job requirements.

        Args:
            job_request: Information about the job. See `nunet.models.JobRequest`.

        Returns:
            Information about the peer assigned to the job and oracle message.
        """
        job_info = requests.post(
            REQUEST_SERVICE_ENDPOINT,
            data=job_request.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if job_info.status_code != requests.codes.ok:
            raise requests.HTTPError(job_info.text)

        return nunet.models.JobConfig.model_validate(job_info.json())

    def cost(self, job_config: nunet.models.JobConfig) -> Value:
        """Calculate the cost of a job.

        This method takes a job configuration and calculates the cost of the job. It
        returns the Value object required to make the payment.

        Args:
            job_config: The job configuration.

        Returns:
            The Value object containing the payment to be sent to the contract.
        """
        return Value.from_primitive(
            [
                int(2000000 + 10**7 * job_config.estimated_price),
                {
                    "8cafc9b387c9f6519cacdce48a8448c062670c810d8da4b232e56313": {
                        "6d4e5458": 10,
                    },
                },
            ],
        )

    def pay(self, job_config: nunet.models.JobConfig) -> str:
        """Pay the contract for the job.

        This uses the wallet for the NuNet Adapter to send a payment to the contract.
        This should be sent before submitting the job, because job submission requires
        the transaction id of the payment.

        Args:
            job_config: The job configuration.

        Returns:
            The transaction id.
        """
        # Create the datum for the job
        datum = ContractDatum(
            address=bytes.fromhex(str(self.address.payment_part)),
            provider_address=bytes.fromhex(
                str(Address.decode(job_config.compute_provider_addr).payment_part),
            ),
            signature=bytes.fromhex(job_config.signature),
            oracle_message=job_config.oracle_message,
            slot=self.context.last_block_slot + 86400,
            timeout=10,
            ntx=1,
        )

        # Create the metadata for package usage tracking
        metadata = {674: {"msg": [f"nunet-py: {__version__}"]}}
        message = pycardano.AuxiliaryData(
            data=pycardano.AlonzoMetadata(metadata=pycardano.Metadata(metadata)),
        )

        tx_builder = pycardano.TransactionBuilder(
            context=self.context,
            auxiliary_data=message,
        )

        tx_builder.add_input_address(self.address)
        tx_builder.add_output(
            pycardano.TransactionOutput(
                address=SCRIPT_ADDRESS,
                amount=self.cost(job_config=job_config),
                datum=datum,
            ),
        )

        tx = tx_builder.build_and_sign(
            signing_keys=[self.pay_key],
            change_address=self.address,
        )

        self.context.submit_tx(tx)

        return str(tx.id)

    def job(self, tx_hash: str) -> Generator[tuple[str, str], None, None]:
        """Submit the job to NuNet.

        This method is a generator that submits a job and yields information from the
        DMS (including stdout).

        Args:
            tx_hash: The transaction id for the contract payment.

        Yields:
            A tuple containing the message type and the message contents.
        """
        with connect(SEND_STATUS) as websocket:
            try:
                websocket.send(
                    json.dumps(
                        {
                            "message": {
                                "transaction_status": "success",
                                "transaction_type": "fund",
                                "tx_hash": tx_hash,
                            },
                            "action": "send-status",
                        },
                    ),
                )
                for message in websocket:
                    parsed = nunet.models.Action.model_validate_json(message)
                    msg_type = parsed.action
                    msg = parsed.stdout if parsed.stdout is not None else parsed.message
                    yield (msg_type, msg)
                    if parsed.action == "job-completed":
                        return
            finally:
                self.terminate()

    def terminate(self) -> None:
        """Send a job termination signal."""
        with connect(SEND_STATUS) as websocket:
            websocket.send(
                json.dumps(
                    {
                        "action": "terminate-job",
                    },
                ),
            )
