import random
import threading
import time
import logging


import order_mq_pb2 as order_mq
import order_mq_pb2_grpc as order_mq_grpc

import order_executor_pb2 as order_executor_grpc
import order_executor_pb2_grpc as order_executor_grpc

import order_mq as order_mq_client
import order_executor as order_executor_client

import info


_FOLLOWER_ROLE = "FOLLOWER"
_CANDIDATE_ROLE = "CANDIDATE"
_LEADER_ROLE = "LEADER"

_CURRENT_EXECUTOR_ADDR = None
_ALL_EXECUTOR_ADDRS = []

_CURRENT_TERM = 0
_VOTED_FOR = None
_LOG = []
_CURRENT_ROLE = _FOLLOWER_ROLE
_CURRENT_LEADER = None
_VOTES_RECEIVED = 0


def setup(replica_addr):
    global _CURRENT_EXECUTOR_ADDR, _ALL_EXECUTOR_ADDRS
    _ALL_EXECUTOR_ADDRS = replica_addr
    pass

def become_candidate():
    logging.info("Worker %s is becoming candidate", info._SERVICE_NAME)
    global _CURRENT_ROLE, _VOTES_RECEIVED, _CURRENT_TERM, _VOTED_FOR

    _CURRENT_ROLE = _CANDIDATE_ROLE
    _CURRENT_TERM += 1
    _VOTED_FOR = _CURRENT_EXECUTOR_ADDR
    _VOTES_RECEIVED = 1


def become_leader():
    logging.info("Worker %s is becoming leader", info._SERVICE_NAME)
    global _CURRENT_ROLE, _CURRENT_LEADER

    _CURRENT_ROLE = _LEADER_ROLE
    _CURRENT_LEADER = _CURRENT_EXECUTOR_ADDR


def become_follower():
    logging.info("Worker %s is becoming follower", info._SERVICE_NAME)
    global _CURRENT_ROLE, _VOTED_FOR

    _CURRENT_ROLE = _FOLLOWER_ROLE
    _VOTED_FOR = None


def run_election():
    logging.info("service %s is running election", info._SERVICE_NAME)
    global _CURRENT_ROLE, _VOTES_RECEIVED

    become_candidate()

    for executor_addr in _ALL_EXECUTOR_ADDRS:
        if executor_addr != _CURRENT_EXECUTOR_ADDR:
            request = {"term": _CURRENT_TERM, "candidate_id": _CURRENT_EXECUTOR_ADDR}
            response = order_executor_client.vote_request(executor_addr, request)
            if response.vote_granted:
                _VOTES_RECEIVED += 1

    if _VOTES_RECEIVED > len(_ALL_EXECUTOR_ADDRS) / 2:
        become_leader()
    logging.info("Worker %s election completed", info._SERVICE_NAME)


def handle_vote_request(request):
    global _VOTED_FOR, _CURRENT_TERM

    if request.term > _CURRENT_TERM:
        become_follower()

    if _VOTED_FOR is None or _VOTED_FOR == request.candidate_id:
        _VOTED_FOR = request.candidate_id
        return True
    return False


def is_leader_healthy():
    global _CURRENT_LEADER
    if _CURRENT_LEADER is None:
        return False
    try:
        order_executor_client.health_check(_CURRENT_LEADER)
        return True
    except Exception:
        return False


def replicate_order(order):
    global _LOG

    _LOG.append(order)
    for executor_addr in _ALL_EXECUTOR_ADDRS:
        if executor_addr != _CURRENT_EXECUTOR_ADDR:
            print(f"Replicating order to {executor_addr}")


def start_executor_flow():
    logging.info("Starting executor flow")
    while True:
        try:
            time.sleep(random.randint(1, 5))
            if _CURRENT_ROLE != _LEADER_ROLE:
                if not is_leader_healthy():
                    run_election()
            else:
                order = order_mq_client.dequeue_order()
                if order is not None:
                    replicate_order(order)
        except Exception as e:
            print(f"Error in coordinator: {e}")


def find_leader():
    global _CURRENT_LEADER

    for executor_addr in _ALL_EXECUTOR_ADDRS:
        try:
            response = order_executor_client.health_check(executor_addr)
            if response.status == "Healthy":
                _CURRENT_LEADER = executor_addr
                break
        except Exception:
            pass


def start_quorumloop():
    t = threading.Thread(target=start_executor_flow)
    t.start()
