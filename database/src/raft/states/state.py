import logging
import random


class NodeState:
    def __init__(self, node):
        self.node = node
        self.logger = logging.getLogger(f'{self.__class__.__name__}')

    def handle_vote_request(self, message):
        raise NotImplementedError

    def handle_append_entries(self, message):
        raise NotImplementedError

    def handle_timeout(self):
        raise NotImplementedError

    def timeout(self):
        raise NotImplementedError

    def get_last_log_index(self):
        return self.node.get_last_log_index()

    def get_last_log_term(self):
        return self.node.get_last_log_term()

    @staticmethod
    def _convert_log_entries(entries):
        """Convert a LogEntry entries protobuf to a dictionary."""

        result = []
        for entry in entries:
            result.append({
                'term': entry.term,
                'command': {
                    'operation': entry.command.operation,
                    'key': entry.command.key,
                    'value': entry.command.value
                }
            })

        return result

    @staticmethod
    def _random_timeout():
        return random.uniform(150, 300) / 100.0

    @staticmethod
    def _static_timeout():
        return 0.5
