import grpc
import logging

LOGGER = logging.getLogger(__name__)


class GrpcClientFactory:
    def __init__(self):
        # Dict to store channels for each service
        self._channels = {}

        # Default timeout for all calls XXX: move this to the docker compose as env variable
        self.default_timeout = 5

    def get_channel(self, service_name, host=None, port=None, secure=True):
        """Get or create a channel for a service"""
        service_id = service_name

        if host and port:
            service_id = f"{service_name}:{host}:{port}"

        # Create the channel if it doesn't exist or is shutdown
        # if service_id not in self._channels: XXX: Check how to fix this crap
        if True:
            address = (
                host
                and port
                and f"{host}:{port}"
                or self._get_service_address(service_name)
            )

            if secure:
                credentials = grpc.ssl_channel_credentials()
                self._channels[service_id] = grpc.secure_channel(address, credentials)
            else:
                self._channels[service_id] = grpc.insecure_channel(address)

            # LOGGER.info(f"Created new gRPC channel for {service_id}")
            print(f"Created new gRPC channel for {service_id}")

        # XXX: need to bump the version of grpc probably
        if self._is_channel_unhealthy(self._channels[service_id]):
            # LOGGER.warning(f"Channel for {service_id} is unhealthy. Recreating...")
            print("Channel for {service_id} is unhealthy. Recreating...")
            self._channels[service_id] = self._channels[service_id].close()
            self._channels[service_id] = self.get_channel(
                service_name, host, port, secure
            )

        return self._channels[service_id]

    def _is_channel_unhealthy(self, channel):
        # print(dir(channel))
        #         print(channel._connectivity_state in [1, 4])
        #   print(channel._connectivity_state)
        #    print(grpc.ChannelConnectivity.SHUTDOWN)
        #   return channel.get_state(try_to_connect=False) in [
        #      grpc.ChannelConnectivity.SHUTDOWN,
        #      grpc.ChannelConnectivity.TRANSIENT_FAILURE,
        #      grpc.ChannelConnectivity.SHUTDOWN,
        # ]

        return False

    def _get_service_address(self, service_name):
        """Get service address from configuration or service discovery"""
        # This could come from environment variables, config files,
        # or a service discovery system like Consul or etcd
        service_config = {
            "fraud_detection": "fraud_detection:50051",
            "suggestions": "suggestions:50053",
            "transaction_verification": "transaction_verification:50052",
        }

        if service_name not in service_config:
            raise ValueError(f"Unknown service: {service_name}")

        return service_config[service_name]

    def get_stub(self, service_name, stub_class, **kwargs):
        """Create a stub for the specified service"""
        channel = self.get_channel(service_name, **kwargs)
        return stub_class(channel)
